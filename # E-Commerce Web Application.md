# E-Commerce Web Application

A fully functional e-commerce web application built with Flask, HTML, Tailwind CSS, Bootstrap, and SQLite.

## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Technical Stack](#technical-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Admin Dashboard](#admin-dashboard)
- [Contributing](#contributing)
- [License](#license)

## Project Overview
This e-commerce platform allows users to browse products, add items to cart, make purchases, and manage user accounts. It includes an admin dashboard for managing products, viewing analytics, and generating reports.

## Features

### Product Management
- Browse products with detailed information
- Filter products by categories, price, and other attributes
- Search functionality for products
- Admin panel for product CRUD operations

### User Authentication & Management
- User registration and login
- Profile management
- Role-based access control (Admin and Customer)
- Password reset functionality

### Shopping Cart & Checkout
- Add/remove products to/from cart
- Adjust product quantities
- Checkout process
- Order summary
- Payment simulation

### Data Analytics Dashboard
- Sales reports
- Product performance metrics
- User activity tracking
- Inventory management

### Additional Functionalities
- Responsive design for all devices
- Product recommendations
- Order history and tracking

## Technical Stack
- **Backend**: Flask (Python)
- **Frontend**: HTML, Tailwind CSS, Bootstrap
- **Database**: SQLite
- **Template Engine**: Jinja2

## Project Structure
```
ecommerce-app/
│
├── app.py                  # Application entry point
├── config.py               # Configuration settings
├── requirements.txt        # Project dependencies
│
├── models/                 # Database models
│   ├── __init__.py
│   ├── product.py
│   ├── user.py
│   ├── order.py
│   └── cart.py
│
├── routes/                 # Application routes (Blueprints)
│   ├── __init__.py
│   ├── auth.py             # Authentication routes
│   ├── products.py         # Product management routes
│   ├── cart.py             # Cart and checkout routes
│   └── admin.py            # Admin dashboard routes
│
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── home.html
│   ├── products/
│   ├── auth/
│   ├── cart/
│   └── admin/
│
└── static/                 # Static files
    ├── css/                # Stylesheets
    ├── js/                 # JavaScript files
    └── img/                # Images
```

## Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ecommerce-app.git
   cd ecommerce-app
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   python init_db.py
   ```

5. Run the application:
   ```
   python app.py
   ```

6. Open your browser and navigate to:
   ```
   http://localhost:5000/
   ```

## Usage

### Customer Flow
1. Register for an account or log in
2. Browse products by category or search for specific items
3. Add products to your cart
4. Proceed to checkout
5. Complete the payment simulation
6. View your order history

### Admin Flow
1. Log in with admin credentials (default admin: admin@example.com, password: admin123)
2. Access the admin dashboard
3. Manage products (add, edit, delete)
4. View sales reports and analytics
5. Manage user accounts

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/logout` - Logout user

### Products
- `GET /api/products` - Get all products
- `GET /api/products/<id>` - Get product by ID
- `POST /api/products` - Create new product (admin only)
- `PUT /api/products/<id>` - Update product (admin only)
- `DELETE /api/products/<id>` - Delete product (admin only)

### Cart
- `GET /api/cart` - Get cart contents
- `POST /api/cart/add/<product_id>` - Add product to cart
- `PUT /api/cart/update/<product_id>` - Update product quantity
- `DELETE /api/cart/remove/<product_id>` - Remove product from cart

### Orders
- `POST /api/orders` - Create new order
- `GET /api/orders` - Get user orders
- `GET /api/orders/<id>` - Get specific order

## Admin Dashboard

The admin dashboard is accessible at `/admin` and provides the following features:
- Product management
- User management
- Order tracking
- Sales analytics and reporting

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
