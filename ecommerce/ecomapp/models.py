from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    """Category model for organizing auto spare parts"""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model for auto spare parts"""
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
        ('refurbished', 'Refurbished'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, 
                                          validators=[MinValueValidator(Decimal('0.01'))])
    stock_quantity = models.PositiveIntegerField(default=0)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    
    # Vehicle compatibility
    make = models.CharField(max_length=100, blank=True, help_text="Car make (e.g., Toyota, Honda)")
    model = models.CharField(max_length=100, blank=True, help_text="Car model")
    year_from = models.PositiveIntegerField(blank=True, null=True, help_text="Year from")
    year_to = models.PositiveIntegerField(blank=True, null=True, help_text="Year to")
    
    # Images
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # Item Images (optional)
    item_image_1 = models.ImageField(upload_to='products/items/', blank=True, null=True, help_text="Optional item image 1")
    item_image_2 = models.ImageField(upload_to='products/items/', blank=True, null=True, help_text="Optional item image 2")
    
    # SEO and metadata
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def discount_percentage(self):
        """Calculate discount percentage if compare_at_price exists"""
        if self.compare_at_price and self.compare_at_price > self.price:
            discount = ((self.compare_at_price - self.price) / self.compare_at_price) * 100
            return round(discount, 0)
        return 0

    @property
    def in_stock(self):
        """Check if product is in stock"""
        return self.stock_quantity > 0

    def get_primary_image(self):
        """Get primary product image"""
        if self.image:
            return self.image.url
        # Check ProductImage instances for primary image
        primary_image = self.product_images.filter(is_primary=True).first()
        if primary_image and primary_image.image:
            return primary_image.image.url
        # Check any ProductImage instance
        first_image = self.product_images.first()
        if first_image and first_image.image:
            return first_image.image.url
        return '/static/img/default.png'
    
    def get_primary_image_obj(self):
        """Get primary product image object"""
        if self.image:
            return self.image
        # Check ProductImage instances for primary image
        primary_image = self.product_images.filter(is_primary=True).first()
        if primary_image and primary_image.image:
            return primary_image.image
        # Check any ProductImage instance
        first_image = self.product_images.first()
        if first_image and first_image.image:
            return first_image.image
        return None

    def get_all_images(self):
        """Get all product images including ProductImage instances"""
        images = []
        if self.image:
            images.append(self.image)
        if self.image_2:
            images.append(self.image_2)
        if self.image_3:
            images.append(self.image_3)
        # Add ProductImage instances
        images.extend([img.image for img in self.product_images.all() if img.image])
        return images
    
    def get_all_image_urls(self):
        """Get all unique product image URLs in proper order for display, including item images"""
        image_urls = []
        seen_urls = set()
        
        # First, add direct image fields (image, image_2, image_3)
        for img_field in [self.image, self.image_2, self.image_3]:
            if img_field and img_field.url not in seen_urls:
                image_urls.append(img_field.url)
                seen_urls.add(img_field.url)
        
        # Then add ProductImage instances (ordered by is_primary first, then created_at)
        for product_image in self.product_images.all().order_by('-is_primary', 'created_at'):
            if product_image.image and product_image.image.url not in seen_urls:
                image_urls.append(product_image.image.url)
                seen_urls.add(product_image.image.url)
        
        # Finally, add item images (item_image_1, item_image_2)
        for img_field in [self.item_image_1, self.item_image_2]:
            if img_field and img_field.url not in seen_urls:
                image_urls.append(img_field.url)
                seen_urls.add(img_field.url)
        
        return image_urls
    
    def get_total_image_count(self):
        """Get total count of all images including item images"""
        count = 0
        # Count main images
        if self.image:
            count += 1
        if self.image_2:
            count += 1
        if self.image_3:
            count += 1
        # Count ProductImage instances
        count += self.product_images.count()
        # Count item images
        if self.item_image_1:
            count += 1
        if self.item_image_2:
            count += 1
        return count


class ProductImage(models.Model):
    """Model for storing multiple images per product"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_images')
    image = models.ImageField(upload_to='products/', help_text="Product image")
    is_primary = models.BooleanField(default=False, help_text="Set as primary image")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        # If this is set as primary, unset other primary images for this product
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)


class Cart(models.Model):
    """Shopping cart model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart (Session: {self.session_key})"

    def get_total(self):
        """Calculate total cart value"""
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    def get_tax(self):
        """Calculate tax (10%)"""
        from decimal import Decimal
        return self.get_total() * Decimal('0.10')

    def get_shipping_cost(self):
        """Get shipping cost"""
        from decimal import Decimal
        return Decimal('10.00')

    def get_final_total(self):
        """Calculate final total with tax and shipping"""
        return self.get_total() + self.get_tax() + self.get_shipping_cost()


class CartItem(models.Model):
    """Cart item model"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def get_subtotal(self):
        """Calculate subtotal for this item"""
        return self.product.price * self.quantity


class CustomerProfile(models.Model):
    """Extended user profile for customers"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

    def get_full_address(self):
        """Get formatted full address"""
        parts = [self.address_line_1, self.address_line_2, self.city, self.state, self.postal_code, self.country]
        return ', '.join(filter(None, parts))


class Order(models.Model):
    """Order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Customer information (stored at time of order)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    
    # Shipping address
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)
    
    # Order details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    def generate_order_number(self):
        """Generate unique order number"""
        import uuid
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Order item model"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)  # Store name in case product is deleted
    product_sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    def save(self, *args, **kwargs):
        if self.product:
            self.product_name = self.product.name
            # product_sku kept for historical order data, but no longer populated from product
            if not self.product_sku:
                self.product_sku = ''  # Set empty string if not already set
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)


class StoreAdmin(models.Model):
    """Store Admin profile model"""
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('store_admin', 'Store Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='store_admin_profile')
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='store_admin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Store Admin'
        verbose_name_plural = 'Store Admins'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
    def is_super_admin(self):
        """Check if user is super admin"""
        return self.role == 'super_admin' or self.user.is_superuser
    
    def is_store_admin(self):
        """Check if user is store admin"""
        return self.role == 'store_admin'