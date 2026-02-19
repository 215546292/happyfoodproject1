<<<<<<< HEAD
# Auto Spares Ecommerce Store

A comprehensive ecommerce platform for auto spare parts built with Django and PostgreSQL.

## Features

- **Product Management**: Full CRUD operations for products, categories, and inventory
- **Shopping Cart**: Session-based and user-based cart functionality
- **Order Management**: Complete order processing with status tracking
- **Admin Portal**: Comprehensive admin interface for store management
- **User Authentication**: Login/logout functionality
- **Search & Filtering**: Advanced product search and filtering by make, condition, price
- **Responsive Design**: Modern, mobile-friendly UI

## Requirements

- Python 3.8+
- PostgreSQL 12+
- Django 6.0+

## Installation

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd ecommerce
   ```

2. **Create a virtual environment** (if not already created):
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up PostgreSQL database**:
   - Create a database named `autospares_db`:
     ```sql
     CREATE DATABASE autospares_db;
     ```
   - Update database credentials in `ecommerce/settings.py` if needed:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.postgresql',
             'NAME': 'autospares_db',
             'USER': 'postgres',
             'PASSWORD': 'your_password',
             'HOST': 'localhost',
             'PORT': '5432',
         }
     }
     ```

6. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create a superuser** (for admin access):
   ```bash
   python manage.py createsuperuser
   ```

8. **Collect static files**:
   ```bash
   python manage.py collectstatic
   ```

9. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

10. **Access the application**:
    - Store frontend: http://127.0.0.1:8000/
    - Admin portal: http://127.0.0.1:8000/admin/

## Project Structure

```
ecommerce/
├── ecommerce/          # Main project settings
│   ├── settings.py     # Django settings
│   ├── urls.py         # Main URL configuration
│   └── ...
├── ecomapp/            # Main application
│   ├── models.py       # Database models
│   ├── views.py        # View functions
│   ├── admin.py        # Admin configuration
│   ├── urls.py         # App URL configuration
│   └── ...
├── templates/          # HTML templates
│   └── ecomapp/
├── static/             # Static files (CSS, JS, images)
│   ├── css/
│   └── js/
├── media/              # User-uploaded media files
└── requirements.txt    # Python dependencies
```

## Admin Features

The admin portal provides comprehensive store management:

- **Categories**: Create and manage product categories
- **Products**: Add, edit, and manage products with images, pricing, and inventory
- **Orders**: View and manage orders, update order status
- **Carts**: Monitor active shopping carts
- **Customer Profiles**: View customer information

## Store Features

### For Customers:
- Browse products by category
- Search and filter products
- Add products to cart
- View cart and update quantities
- Checkout and place orders
- View order history and details
- Track order status

### For Admins:
- Full product management
- Order management and status updates
- Inventory tracking
- Customer management
- Category management

## Database Models

- **Category**: Product categories
- **Product**: Auto spare parts with vehicle compatibility
- **Cart**: Shopping cart (user or session-based)
- **CartItem**: Individual cart items
- **Order**: Customer orders
- **OrderItem**: Order line items
- **CustomerProfile**: Extended user profile

## Configuration

### Database Settings
Update `ecommerce/settings.py` with your PostgreSQL credentials.

### Media Files
Media files (product images, category images) are stored in the `media/` directory.

### Static Files
Static files are collected to `staticfiles/` directory in production.

## Development Notes

- The application uses session-based carts for anonymous users
- User-based carts for authenticated users
- Stock is automatically updated when orders are placed
- Tax is set to 10% (configurable in views)
- Shipping cost is $10.00 (configurable in Cart model)

## License

This project is open source and available for modification and distribution.

=======
# happyfoodproject1
is the first project
>>>>>>> fba87c3a8e94175d0e09ac1c991f31d971d62a9d
