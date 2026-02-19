from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.models import User
import json
from .models import (
    Product, Category, Cart, CartItem, Order, OrderItem, CustomerProfile, StoreAdmin, ProductImage
)


def get_or_create_cart(request):
    """Get or create cart for user or session with enhanced error handling"""
    try:
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            if not session_key or len(session_key) > 40:
                raise ValueError("Invalid session key")
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        return cart
    except Exception as e:
        # Log error and raise to be handled by calling function
        raise


def home(request):
    """Home page with featured products"""
    featured_products = Product.objects.filter(is_featured=True, is_active=True).prefetch_related('product_images')[:8]
    categories = Category.objects.filter(is_active=True)[:6]
    latest_products = Product.objects.filter(is_active=True).prefetch_related('product_images').order_by('-created_at')[:8]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'latest_products': latest_products,
    }
    return render(request, 'ecomapp/home.html', context)


def product_list(request, category_slug=None):
    """Product listing page with filtering"""
    products = Product.objects.filter(is_active=True).prefetch_related('product_images')
    category = None
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=category)
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(make__icontains=search_query) |
            Q(model__icontains=search_query)
        )
    
    # Filtering
    make_filter = request.GET.get('make', '')
    condition_filter = request.GET.get('condition', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    
    if make_filter:
        products = products.filter(make__icontains=make_filter)
    if condition_filter:
        products = products.filter(condition=condition_filter)
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique makes for filter
    makes = Product.objects.filter(is_active=True).values_list('make', flat=True).distinct()
    makes = [m for m in makes if m]
    
    context = {
        'products': page_obj,
        'category': category,
        'categories': Category.objects.filter(is_active=True),
        'search_query': search_query,
        'makes': sorted(makes),
        'selected_make': make_filter,
        'selected_condition': condition_filter,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
    }
    return render(request, 'ecomapp/product_list.html', context)


def product_detail(request, slug):
    """Product detail page with enhanced error handling and security"""
    try:
        # Validate slug format
        if not slug or len(slug) > 200:
            messages.error(request, 'Invalid product URL.')
            return redirect('ecomapp:product_list')
        
        # Get product with optimized query
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related('product_images'),
            slug=slug,
            is_active=True
        )
        
        # Get related products with error handling - enhanced for better recommendations
        try:
            # Fetch more related products (12) with smart ordering
            # Priority: featured products first, then by creation date (newest first)
            related_products = Product.objects.filter(
                category=product.category,
                is_active=True
            ).exclude(id=product.id).prefetch_related('product_images').order_by(
                '-is_featured',  # Featured products first
                '-created_at'    # Then newest first
            )[:12]
        except Exception as e:
            # Log error but don't break the page
            related_products = []
        
        context = {
            'product': product,
            'related_products': related_products,
        }
        return render(request, 'ecomapp/product_detail.html', context)
    except Exception as e:
        # Log the error (in production, use proper logging)
        messages.error(request, 'An error occurred while loading the product. Please try again.')
        return redirect('ecomapp:product_list')


def cart_view(request):
    """Shopping cart page with enhanced error handling"""
    try:
        cart = get_or_create_cart(request)
        cart_items = cart.items.select_related('product').prefetch_related('product__product_images').all()
        
        # Validate cart items (remove invalid items)
        invalid_items = []
        for item in cart_items:
            if not item.product.is_active or item.product.stock_quantity < item.quantity:
                invalid_items.append(item)
        
        if invalid_items:
            for item in invalid_items:
                item.delete()
            messages.warning(request, 'Some items in your cart are no longer available and have been removed.')
            # Refresh cart items after cleanup
            cart_items = cart.items.select_related('product').prefetch_related('product__product_images').all()
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
        }
        return render(request, 'ecomapp/cart.html', context)
    except Exception as e:
        messages.error(request, 'An error occurred while loading your cart. Please try again.')
        return redirect('ecomapp:home')


@require_POST
def add_to_cart(request, product_id):
    """Add product to cart with enhanced validation and error handling"""
    try:
        # Validate product_id
        try:
            product_id = int(product_id)
            if product_id <= 0:
                raise ValueError("Invalid product ID")
        except (ValueError, TypeError):
            messages.error(request, 'Invalid product selected.')
            return redirect('ecomapp:product_list')
        
        # Get product with validation
        try:
            product = Product.objects.select_related('category').get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            messages.error(request, 'Product not found or no longer available.')
            return redirect('ecomapp:product_list')
        
        # Validate and parse quantity
        try:
            quantity_str = request.POST.get('quantity', '1')
            quantity = int(quantity_str)
            
            # Validate quantity range
            if quantity < 1:
                messages.error(request, 'Quantity must be at least 1.')
                return redirect('ecomapp:product_detail', slug=product.slug)
            
            if quantity > 999:  # Reasonable upper limit
                messages.error(request, 'Maximum quantity per item is 999.')
                return redirect('ecomapp:product_detail', slug=product.slug)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity specified.')
            return redirect('ecomapp:product_detail', slug=product.slug)
        
        # Check stock availability
        if product.stock_quantity < quantity:
            messages.error(request, f'Only {product.stock_quantity} item(s) available in stock.')
            return redirect('ecomapp:product_detail', slug=product.slug)
        
        # Get or create cart
        try:
            cart = get_or_create_cart(request)
        except Exception as e:
            messages.error(request, 'Unable to access your cart. Please try again.')
            return redirect('ecomapp:product_detail', slug=product.slug)
        
        # Add or update cart item
        try:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > product.stock_quantity:
                    messages.error(request, f'Only {product.stock_quantity} item(s) available in stock.')
                    return redirect('ecomapp:product_detail', slug=product.slug)
                cart_item.quantity = new_quantity
                cart_item.save()
        except Exception as e:
            messages.error(request, 'Unable to add item to cart. Please try again.')
            return redirect('ecomapp:product_detail', slug=product.slug)
        
        messages.success(request, f'{product.name} added to cart.')
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': cart.get_item_count(),
                'message': f'{product.name} added to cart.'
            })
        
        return redirect('ecomapp:cart')
    
    except Exception as e:
        # Log error (in production, use proper logging)
        messages.error(request, 'An error occurred. Please try again.')
        return redirect('ecomapp:product_list')


@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        cart_item.delete()
        messages.success(request, 'Item removed from cart.')
    else:
        if quantity > cart_item.product.stock_quantity:
            messages.error(request, f'Only {cart_item.product.stock_quantity} items available in stock.')
            return redirect('ecomapp:cart')
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, 'Cart updated.')
    
    return redirect('ecomapp:cart')


@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('ecomapp:cart')


@login_required
def checkout(request):
    """Checkout page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('ecomapp:cart')
    
    # Check stock availability
    for item in cart_items:
        if item.quantity > item.product.stock_quantity:
            messages.error(request, f'{item.product.name} - Only {item.product.stock_quantity} items available.')
            return redirect('ecomapp:cart')
    
    # Get or create customer profile
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Process order
        subtotal = cart.get_total()
        tax = cart.get_tax()
        shipping_cost = cart.get_shipping_cost()
        total = cart.get_final_total()
        
        order = Order.objects.create(
            user=request.user,
            customer_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            customer_email=request.user.email,
            customer_phone=request.POST.get('phone', profile.phone),
            shipping_address_line_1=request.POST.get('address_line_1', profile.address_line_1),
            shipping_address_line_2=request.POST.get('address_line_2', profile.address_line_2),
            shipping_city=request.POST.get('city', profile.city),
            shipping_state=request.POST.get('state', profile.state),
            shipping_postal_code=request.POST.get('postal_code', profile.postal_code),
            shipping_country=request.POST.get('country', profile.country),
            subtotal=subtotal,
            tax=tax,
            shipping_cost=shipping_cost,
            total=total,
            notes=request.POST.get('notes', ''),
        )
        
        # Create order items and update stock
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_sku='',  # SKU field removed, but kept in OrderItem for historical data
                quantity=cart_item.quantity,
                price=cart_item.product.price,
            )
            # Update stock
            cart_item.product.stock_quantity -= cart_item.quantity
            cart_item.product.save()
        
        # Update customer profile
        profile.phone = request.POST.get('phone', profile.phone)
        profile.address_line_1 = request.POST.get('address_line_1', profile.address_line_1)
        profile.address_line_2 = request.POST.get('address_line_2', profile.address_line_2)
        profile.city = request.POST.get('city', profile.city)
        profile.state = request.POST.get('state', profile.state)
        profile.postal_code = request.POST.get('postal_code', profile.postal_code)
        profile.country = request.POST.get('country', profile.country)
        profile.save()
        
        # Clear cart
        cart.items.all().delete()
        
        messages.success(request, f'Order {order.order_number} placed successfully!')
        return redirect('order_confirmation', order_number=order.order_number)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'profile': profile,
    }
    return render(request, 'ecomapp/checkout.html', context)


@login_required
def order_confirmation(request, order_number):
    """Order confirmation page"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Verify order belongs to user
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this order.')
        return redirect('ecomapp:home')
    
    context = {
        'order': order,
    }
    return render(request, 'ecomapp/order_confirmation.html', context)


@login_required
def order_list(request):
    """User's order list"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'ecomapp/order_list.html', context)


@login_required
def order_detail(request, order_number):
    """Order detail page"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Verify order belongs to user
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this order.')
        return redirect('ecomapp:home')
    
    context = {
        'order': order,
    }
    return render(request, 'ecomapp/order_detail.html', context)


def custom_login(request):
    """Custom login view to handle super admin and store admin"""
    if request.user.is_authenticated:
        # Redirect based on user type
        if hasattr(request.user, 'store_admin_profile'):
            if request.user.store_admin_profile.is_super_admin():
                return redirect('super_admin_dashboard')
            else:
                return redirect('store_admin_dashboard')
        elif request.user.is_superuser:
            return redirect('super_admin_dashboard')
        else:
            return redirect('ecomapp:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', '') or request.GET.get('next', '')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Check if user is super admin or store admin
                if hasattr(user, 'store_admin_profile'):
                    if user.store_admin_profile.is_super_admin():
                        return redirect('super_admin_dashboard')
                    else:
                        return redirect('store_admin_dashboard')
                elif user.is_superuser:
                    return redirect('super_admin_dashboard')
                else:
                    # Redirect to next URL if provided, otherwise home
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)
                    return redirect('ecomapp:home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please provide both username and password.')
    
    # GET request - pass next parameter to template
    next_url = request.GET.get('next', '')
    return render(request, 'ecomapp/login.html', {'next': next_url})


def custom_logout(request):
    """Custom logout view that redirects to home page"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('ecomapp:home')


def register(request):
    """Customer registration view"""
    if request.user.is_authenticated:
        # If user is already logged in, redirect based on user type
        if hasattr(request.user, 'store_admin_profile'):
            if request.user.store_admin_profile.is_super_admin():
                return redirect('super_admin_dashboard')
            else:
                return redirect('store_admin_dashboard')
        elif request.user.is_superuser:
            return redirect('super_admin_dashboard')
        else:
            return redirect('ecomapp:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        next_url = request.POST.get('next', '') or request.GET.get('next', '')
        
        # Validation
        if not all([username, email, phone, password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return render(request, 'ecomapp/register.html', {'next': next_url})
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'ecomapp/register.html', {'next': next_url})
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'ecomapp/register.html', {'next': next_url})
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Please choose a different username.')
            return render(request, 'ecomapp/register.html', {'next': next_url})
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists. Please use a different email.')
            return render(request, 'ecomapp/register.html', {'next': next_url})
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Create customer profile
            CustomerProfile.objects.create(
                user=user,
                phone=phone
            )
            
            # Log the user in
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Auto Spares Store.')
            
            # Redirect to next URL if provided, otherwise home
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('ecomapp:home')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'ecomapp/register.html', {'next': next_url})
    
    # GET request
    next_url = request.GET.get('next', '')
    return render(request, 'ecomapp/register.html', {'next': next_url})


@login_required
def super_admin_dashboard(request):
    """Super admin dashboard - can register store admins"""
    # Check if user is super admin
    if not request.user.is_superuser and not (hasattr(request.user, 'store_admin_profile') and request.user.store_admin_profile.is_super_admin()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('ecomapp:home')
    
    # Get all store admins
    store_admins = StoreAdmin.objects.filter(role='store_admin').select_related('user')
    
    context = {
        'store_admins': store_admins,
    }
    return render(request, 'ecomapp/super_admin_dashboard.html', context)


@login_required
def register_store_admin(request):
    """Register a new store admin (only accessible by super admin)"""
    # Check if user is super admin
    if not request.user.is_superuser and not (hasattr(request.user, 'store_admin_profile') and request.user.store_admin_profile.is_super_admin()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('ecomapp:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone = request.POST.get('phone')
        
        # Validation
        if not username or not password or not confirm_password or not phone:
            messages.error(request, 'All fields are required.')
            return render(request, 'ecomapp/register_store_admin.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'ecomapp/register_store_admin.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'ecomapp/register_store_admin.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'ecomapp/register_store_admin.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                is_staff=True  # Store admins are staff
            )
            
            # Create store admin profile
            StoreAdmin.objects.create(
                user=user,
                phone=phone,
                role='store_admin'
            )
            
            messages.success(request, f'Store admin "{username}" registered successfully!')
            return redirect('super_admin_dashboard')
        except Exception as e:
            messages.error(request, f'Error creating store admin: {str(e)}')
            return render(request, 'ecomapp/register_store_admin.html')
    
    return render(request, 'ecomapp/register_store_admin.html')


@login_required
def store_admin_dashboard(request):
    """Store admin dashboard - manage products/items and prices"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('ecomapp:home')
    
    # Get all products with optimized queries
    products = Product.objects.select_related('category').prefetch_related('product_images').order_by('-created_at')
    categories = Category.objects.filter(is_active=True)
    
    # Search and filter
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
    }
    return render(request, 'ecomapp/store_admin_dashboard.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def edit_product(request, product_id):
    """Edit product - update all fields (store admin only)"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to perform this action.')
            return redirect('ecomapp:home')
    
    product = get_object_or_404(Product.objects.select_related('category'), id=product_id)
    categories = Category.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name', '').strip()
            category_id = request.POST.get('category')
            price = request.POST.get('price')
            stock_quantity = request.POST.get('stock_quantity')
            is_active = request.POST.get('is_active', 'true').lower() == 'true'
            
            # Validation
            if not all([name, category_id, price, stock_quantity is not None]):
                messages.error(request, 'All required fields must be filled.')
                return redirect('store_admin_dashboard')
            
            # Get category
            try:
                category = Category.objects.get(id=category_id, is_active=True)
            except Category.DoesNotExist:
                messages.error(request, 'Invalid category selected.')
                return redirect('store_admin_dashboard')
            
            # Update product fields
            old_name = product.name
            product.name = name
            product.category = category
            product.price = float(price)
            product.stock_quantity = int(stock_quantity)
            product.is_active = is_active
            
            # Update slug if name changed
            if old_name != name:
                slug = slugify(name)
                base_slug = slug
                counter = 1
                while Product.objects.filter(slug=slug).exclude(id=product_id).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                product.slug = slug
            
            # Handle image upload
            if 'image' in request.FILES:
                image_file = request.FILES['image']
                # Delete old image if exists
                if product.image:
                    product.image.delete(save=False)
                product.image = image_file
            
            # Handle item image 1 upload
            if 'item_image_1' in request.FILES:
                item_image_file = request.FILES['item_image_1']
                # Delete old image if exists
                if product.item_image_1:
                    product.item_image_1.delete(save=False)
                product.item_image_1 = item_image_file
            
            # Handle item image 2 upload
            if 'item_image_2' in request.FILES:
                item_image_file = request.FILES['item_image_2']
                # Delete old image if exists
                if product.item_image_2:
                    product.item_image_2.delete(save=False)
                product.item_image_2 = item_image_file
            
            # Handle item image removal (if remove flags are set)
            if request.POST.get('remove_item_image_1') == 'true':
                if product.item_image_1:
                    product.item_image_1.delete(save=False)
                    product.item_image_1 = None
            
            if request.POST.get('remove_item_image_2') == 'true':
                if product.item_image_2:
                    product.item_image_2.delete(save=False)
                    product.item_image_2 = None
            
            product.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            
        except (ValueError, TypeError) as e:
            messages.error(request, f'Invalid input: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
        
        return redirect('store_admin_dashboard')
    
    # GET request - return product data as JSON (for AJAX if needed)
    return JsonResponse({
        'id': product.id,
        'name': product.name,
        'category_id': product.category.id,
        'price': str(product.price),
        'stock_quantity': product.stock_quantity,
        'is_active': product.is_active,
        'image_url': product.get_primary_image() if product.get_primary_image() else '',
        'item_image_1_url': product.item_image_1.url if product.item_image_1 else '',
        'item_image_2_url': product.item_image_2.url if product.item_image_2 else ''
    })


@login_required
def add_product(request):
    """Add new product (store admin only)"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('ecomapp:home')
    
    categories = Category.objects.filter(is_active=True)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock_quantity = request.POST.get('stock_quantity', 0)
        
        if not all([name, category_id, description, price]):
            messages.error(request, 'All required fields must be filled.')
            return render(request, 'ecomapp/add_product.html', {'categories': categories})
        
        try:
            category = Category.objects.get(id=category_id)
            # Generate unique slug
            slug = slugify(name)
            base_slug = slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Handle multiple image uploads
            images = request.FILES.getlist('images')
            
            # Create product first
            product = Product.objects.create(
                name=name,
                slug=slug,
                category=category,
                description=description,
                price=float(price),
                stock_quantity=int(stock_quantity),
                is_active=True,
            )
            
            # Save images
            if images:
                # Save first image as primary to product.image
                # This ensures get_primary_image() returns the correct URL
                product.image = images[0]
                product.save()
                
                # Save additional images (skip first since it's already in product.image)
                # to ProductImage for gallery views
                for idx, image_file in enumerate(images[1:], start=1):
                    ProductImage.objects.create(
                        product=product,
                        image=image_file,
                        is_primary=False
                    )
            
            # Handle optional item images
            needs_save = False
            if 'item_image_1' in request.FILES:
                product.item_image_1 = request.FILES['item_image_1']
                needs_save = True
            
            if 'item_image_2' in request.FILES:
                product.item_image_2 = request.FILES['item_image_2']
                needs_save = True
            
            if needs_save:
                product.save()
            
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('store_admin_dashboard')
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
            return render(request, 'ecomapp/add_product.html', {'categories': categories})
    
    return render(request, 'ecomapp/add_product.html', {'categories': categories})


@login_required
@require_http_methods(["GET", "POST"])
def manage_categories(request):
    """Manage categories - list, create, update, delete"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'GET':
        # Return list of categories
        categories = Category.objects.filter(is_active=True).order_by('name')
        categories_data = [
            {
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'description': cat.description,
                'product_count': cat.products.count()
            }
            for cat in categories
        ]
        return JsonResponse({'success': True, 'categories': categories_data})
    
    elif request.method == 'POST':
        # Create new category
        try:
            content_type = request.content_type or ''
            if 'application/json' in content_type:
                try:
                    data = json.loads(request.body.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    return JsonResponse({'success': False, 'error': f'Invalid JSON data: {str(e)}'}, status=400)
            else:
                data = request.POST
            
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            
            if not name:
                return JsonResponse({'success': False, 'error': 'Category name is required'}, status=400)
            
            # Check if category with same name exists
            if Category.objects.filter(name__iexact=name).exists():
                return JsonResponse({'success': False, 'error': 'Category with this name already exists'}, status=400)
            
            # Generate slug
            slug = slugify(name)
            base_slug = slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            category = Category.objects.create(
                name=name,
                slug=slug,
                description=description,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Category "{category.name}" created successfully!',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'slug': category.slug,
                    'description': category.description,
                    'product_count': 0
                }
            })
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'Invalid JSON format: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error creating category: {str(e)}'}, status=500)


@login_required
@require_http_methods(["PUT", "POST"])
def update_category(request, category_id):
    """Update an existing category"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    category = get_object_or_404(Category, id=category_id)
    
    try:
        # Handle both JSON and form data
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return JsonResponse({'success': False, 'error': f'Invalid JSON data: {str(e)}'}, status=400)
        else:
            data = request.POST
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'}, status=400)
        
        # Check if another category with same name exists
        if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
            return JsonResponse({'success': False, 'error': 'Category with this name already exists'}, status=400)
        
        # Update slug if name changed
        old_name = category.name
        if old_name != name:
            slug = slugify(name)
            base_slug = slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(id=category_id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            category.slug = slug
        
        # Update category
        category.name = name
        category.description = description
        
        category.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Category "{category.name}" updated successfully!',
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'product_count': category.products.count()
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error updating category: {str(e)}'}, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])
def delete_category(request, category_id):
    """Delete a category"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    category = get_object_or_404(Category, id=category_id)
    
    try:
        # Check if category has products
        product_count = category.products.count()
        if product_count > 0:
            return JsonResponse({
                'success': False,
                'error': f'Cannot delete category. It has {product_count} product(s) associated with it.'
            }, status=400)
        
        category_name = category.name
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Category "{category_name}" deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])
def delete_product_image(request, image_id):
    """Delete a product image"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    product_image = get_object_or_404(ProductImage, id=image_id)
    
    try:
        product_name = product_image.product.name
        # Delete the image file from filesystem
        if product_image.image:
            product_image.image.delete(save=False)
        product_image.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Image deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def bulk_delete_products(request):
    """Bulk delete multiple products"""
    # Check if user is store admin
    if not hasattr(request.user, 'store_admin_profile') or not request.user.store_admin_profile.is_store_admin():
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        # Get product IDs from request
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return JsonResponse({'success': False, 'error': 'No products selected'}, status=400)
        
        # Validate product IDs
        try:
            product_ids = [int(pid) for pid in product_ids]
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid product IDs'}, status=400)
        
        # Get products
        products = Product.objects.filter(id__in=product_ids)
        
        if not products.exists():
            return JsonResponse({'success': False, 'error': 'No products found'}, status=404)
        
        # Delete products and their associated images
        deleted_count = 0
        deleted_names = []
        
        for product in products:
            # Delete product images
            if product.image:
                product.image.delete(save=False)
            if product.image_2:
                product.image_2.delete(save=False)
            if product.image_3:
                product.image_3.delete(save=False)
            if product.item_image_1:
                product.item_image_1.delete(save=False)
            if product.item_image_2:
                product.item_image_2.delete(save=False)
            
            # Delete ProductImage instances
            for product_image in product.product_images.all():
                if product_image.image:
                    product_image.image.delete(save=False)
                product_image.delete()
            
            deleted_names.append(product.name)
            product.delete()
            deleted_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} product(s) deleted successfully!',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
