"""
URL configuration for ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from ecomapp import views as ecomapp_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ecomapp.urls')),
    path('login/', ecomapp_views.custom_login, name='login'),
    path('register/', ecomapp_views.register, name='register'),
    path('logout/', ecomapp_views.custom_logout, name='logout'),
    path('super-admin/dashboard/', ecomapp_views.super_admin_dashboard, name='super_admin_dashboard'),
    path('super-admin/register-store-admin/', ecomapp_views.register_store_admin, name='register_store_admin'),
    path('store-admin/dashboard/', ecomapp_views.store_admin_dashboard, name='store_admin_dashboard'),
    path('store-admin/product/<int:product_id>/edit/', ecomapp_views.edit_product, name='edit_product'),
    path('store-admin/product/add/', ecomapp_views.add_product, name='add_product'),
    path('store-admin/categories/', ecomapp_views.manage_categories, name='manage_categories'),
    path('store-admin/category/<int:category_id>/update/', ecomapp_views.update_category, name='update_category'),
    path('store-admin/category/<int:category_id>/delete/', ecomapp_views.delete_category, name='delete_category'),
    path('store-admin/product-image/<int:image_id>/delete/', ecomapp_views.delete_product_image, name='delete_product_image'),
    path('store-admin/products/bulk-delete/', ecomapp_views.bulk_delete_products, name='bulk_delete_products'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
