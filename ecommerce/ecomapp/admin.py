from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Product, Cart, CartItem, Order, OrderItem, CustomerProfile, StoreAdmin
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        ('Image', {
            'fields': ('image', 'image_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Image Preview'
    
    def product_count(self, obj):
        count = obj.products.count()
        url = reverse('admin:ecomapp_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} products</a>', url, count)
    product_count.short_description = 'Products'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'get_subtotal']
    
    def get_subtotal(self, obj):
        return f"R{obj.get_subtotal():.2f}"
    get_subtotal.short_description = 'Subtotal'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'item_count', 'get_total', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CartItemInline]
    
    def item_count(self, obj):
        return obj.get_item_count()
    item_count.short_description = 'Items'
    
    def get_total(self, obj):
        return f"R{obj.get_total():.2f}"
    get_total.short_description = 'Total'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity', 'is_active', 'is_featured', 'image_preview', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'condition', 'created_at']
    search_fields = ['name', 'description', 'make', 'model']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'image_preview', 'image_2_preview', 'image_3_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'condition')
        }),
        ('Vehicle Compatibility', {
            'fields': ('make', 'model', 'year_from', 'year_to'),
            'classes': ('collapse',)
        }),
        ('Images', {
            'fields': ('image', 'image_preview', 'image_2', 'image_2_preview', 'image_3', 'image_3_preview')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Primary Image'
    
    def image_2_preview(self, obj):
        if obj.image_2:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image_2.url)
        return "No image"
    image_2_preview.short_description = 'Image 2'
    
    def image_3_preview(self, obj):
        if obj.image_3:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image_3.url)
        return "No image"
    image_3_preview.short_description = 'Image 3'
    
    actions = ['make_featured', 'make_unfeatured', 'activate_products', 'deactivate_products']
    
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'{queryset.count()} products marked as featured.')
    make_featured.short_description = 'Mark selected as featured'
    
    def make_unfeatured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f'{queryset.count()} products unmarked as featured.')
    make_unfeatured.short_description = 'Unmark selected as featured'
    
    def activate_products(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} products activated.')
    activate_products.short_description = 'Activate selected products'
    
    def deactivate_products(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} products deactivated.')
    deactivate_products.short_description = 'Deactivate selected products'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_sku', 'quantity', 'price', 'subtotal']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'customer_email', 'total', 'status', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_email', 'customer_phone']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'get_order_items']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payment_status')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_address_line_1', 'shipping_address_line_2',
                'shipping_city', 'shipping_state', 'shipping_postal_code', 'shipping_country'
            )
        }),
        ('Order Summary', {
            'fields': ('subtotal', 'tax', 'shipping_cost', 'total', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_order_items(self, obj):
        items = obj.items.all()
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f0f0f0;"><th style="padding: 8px; border: 1px solid #ddd;">Product</th><th style="padding: 8px; border: 1px solid #ddd;">Qty</th><th style="padding: 8px; border: 1px solid #ddd;">Price</th><th style="padding: 8px; border: 1px solid #ddd;">Subtotal</th></tr>'
        for item in items:
            html += f'<tr><td style="padding: 8px; border: 1px solid #ddd;">{item.product_name}</td><td style="padding: 8px; border: 1px solid #ddd;">{item.quantity}</td><td style="padding: 8px; border: 1px solid #ddd;">R{item.price:.2f}</td><td style="padding: 8px; border: 1px solid #ddd;">R{item.subtotal:.2f}</td></tr>'
        html += '</table>'
        return mark_safe(html)
    get_order_items.short_description = 'Order Items'
    
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    
    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, f'{queryset.count()} orders marked as processing.')
    mark_as_processing.short_description = 'Mark selected as processing'
    
    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, f'{queryset.count()} orders marked as shipped.')
    mark_as_shipped.short_description = 'Mark selected as shipped'
    
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, f'{queryset.count()} orders marked as delivered.')
    mark_as_delivered.short_description = 'Mark selected as delivered'
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f'{queryset.count()} orders marked as cancelled.')
    mark_as_cancelled.short_description = 'Mark selected as cancelled'


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'country', 'created_at']
    list_filter = ['country', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone', 'city']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone',)
        }),
        ('Address', {
            'fields': (
                'address_line_1', 'address_line_2',
                'city', 'state', 'postal_code', 'country'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StoreAdmin)
class StoreAdminAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'role')
        }),
        ('Contact Information', {
            'fields': ('phone',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
