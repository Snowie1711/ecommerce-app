# E-Commerce Application

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
- Update variables, especially MoMo credentials:
  ```
  MOMO_PARTNER_CODE=your_partner_code
  MOMO_ACCESS_KEY=your_access_key
  MOMO_SECRET_KEY=your_secret_key
  MOMO_PAYMENT_URL=https://test-payment.momo.vn/v2/gateway/api/create
  ```

### MoMo Integration Notes

1. Amount Handling:
- Amounts are stored in USD
- Automatically converted to VND for MoMo (1 USD = 23,000 VND)
- Amount must be at least 1,000 VND

2. Error Handling:
- Check logs for detailed error messages
- Common error codes:
  - `0`: Success
  - `7`: Transaction denied
  - `9`: Partner not found
  - `10`: Invalid signature
  - `11`: Order not found

3. Development Testing:
- Use MoMo Sandbox environment
- Test credentials available at https://developers.momo.vn
- Sandbox supports test transactions with any valid amount

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

1. MoMo Payment Issues:
- Verify amount conversion (must be in VND)
- Check signature generation
- Validate partner credentials
- Review server logs for detailed errors
- Monitor MoMo sandbox dashboard for transaction status

2. CSS/Styling Issues:
- In development: Use CDN (warning suppressed)
- In production: Build CSS with `npm run build:css`
- If npm not installed: Follow Node.js setup instructions

3. Debug Mode:
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
- Test ZaloPay integration with sandbox
- Verify responsive design

### License

MIT License - See LICENSE file for details