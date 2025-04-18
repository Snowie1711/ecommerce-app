# E-Commerce Application

A Flask-based e-commerce application with free shipping for all orders.

## Features

- Product catalog with categories
- Shopping cart
- User accounts and order history
- PayOS payment integration
- **Free shipping on all orders**

## Development Setup

### Prerequisites
1. Python 3.8+
2. Flask and dependencies (`pip install -r requirements.txt`)
3. SQLite (included with Python)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ecommerce-app
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Unix
.\venv\Scripts\activate   # Windows
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
flask init-db
```

### Production Setup

For production deployment, you'll need to set up Tailwind CSS properly:

1. Install Node.js and npm from [https://nodejs.org/](https://nodejs.org/)

2. Install project dependencies:
```bash
npm install
```

3. Build Tailwind CSS:
```bash
npm run build:css
```

4. Configure environment variables:
- Copy `.env.example` to `.env`
- Update PayOS credentials in the .env file

### Development vs Production

1. Development Mode:
- Uses Tailwind CDN (with warning suppression)
- Debug logging enabled
- Detailed error messages

2. Production Mode:
- Uses built Tailwind CSS
- Minimized logging
- User-friendly error messages
- Proper error handling and fallbacks

### Troubleshooting

1. CSS/Styling Issues:
- In development: Use CDN (warning suppressed)
- In production: Build CSS with `npm run build:css`
- If npm not installed: Follow Node.js setup instructions

2. Debug Mode:
- Enable debug toggle in UI
- Check browser console
- Review Flask server logs

### Contributing

1. Style Guide:
- Follow PEP 8 for Python code
- Use JSDoc comments for JavaScript
- Follow Tailwind CSS conventions

2. Testing:
- Run Python tests: `python -m pytest`
- Test PayOS integration with sandbox
- Verify responsive design

### License

MIT License - See LICENSE file for details

## Shipping Policy

This application provides free shipping for all orders. No minimum purchase amount is required.

## Development

For development, you can use the development server:

```bash
python dev.py
```

This will install additional development dependencies if needed.