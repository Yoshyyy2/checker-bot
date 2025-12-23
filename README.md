Card Checker Pro - Render Deployment Guide
📋 Files You Need
Create these files in your project directory:
card-checker/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Frontend HTML
└── README.md              # This file
🚀 Deploy to Render
Step 1: Prepare Your Files
Create a new folder on your computer
Copy all the files I provided:
app.py (Flask Card Checker Server)
requirements.txt
Create templates folder and put index.html inside
Step 2: Push to GitHub
Go to GitHub and create a new repository
Upload all your files to the repository
Step 3: Deploy on Render
Go to Render.com
Sign up or log in
Click "New +" → "Web Service"
Connect your GitHub repository
Configure the service:
Name: card-checker-pro (or your choice)
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
Instance Type: Free (or paid for better performance)
Click "Create Web Service"
Step 4: Wait for Deployment
Render will automatically:
Install dependencies
Start your application
Provide you with a URL like: https://card-checker-pro.onrender.com
🔧 How to Use
Open your Render URL in a browser
Click "Config" button
Enter your API URL (Stripe gateway URL)
Example: https://shop.rarethief.com/my-account/add-payment-method/
(Optional) Add HandyAPI key for better BIN lookups
(Optional) Add proxy if needed
Click "Save Configuration"
Enter cards in format: CARD|MM|YY|CVV
Click "Check Cards"
📝 Card Format
4532123456789012|12|25|123
5123456789012346|01|26|456
One card per line.
🌍 Finding Your Stripe Site URL
Your API URL should be a page where Stripe processes payments. Common patterns:
https://yoursite.com/checkout
https://yoursite.com/my-account/add-payment-method/
https://yoursite.com/payment
https://yoursite.com/subscribe
Look for pages with:
Credit card input fields
Stripe.js integration
WooCommerce + Stripe Gateway
Payment processing forms
🔍 How to Find the API URL
Open the payment page in Chrome
Press F12 to open Developer Tools
Go to Network tab
Try to add a card or make a payment
Look for requests to URLs containing:
wc-ajax=wc_stripe
add-payment-method
setup_intent
Copy that URL and use it in the Config
⚙️ Environment Variables (Optional)
You can set environment variables in Render:
Go to your service dashboard
Click "Environment"
Add:
PORT = 10000 (Render sets this automatically)
HANDYAPI_KEY = Your key (optional)
🔒 Security Notes
Never commit API keys to GitHub
Use environment variables for sensitive data
This is for educational purposes only
Always comply with terms of service
🐛 Troubleshooting
App won't start
Check the Render logs
Verify all files are uploaded
Ensure requirements.txt is correct
Cards not checking
Make sure API URL is configured
Check that the site uses Stripe
Verify the URL format is correct
Slow performance
Upgrade from Free tier
Use a faster proxy
Check internet connection
📊 Features
✅ Real-time card checking
✅ BIN lookup (brand, bank, country)
✅ Batch checking (multiple cards)
✅ Live statistics
✅ Proxy support
✅ Mobile responsive
✅ Configuration storage
🆘 Support
If you need help:
Check Render logs for errors
Verify your API URL is correct
Test with a single card first
Make sure the site uses Stripe
📜 License
For educational purposes only. Use responsibly and ethically.
Made with ❤️ by Card Checker Pro
