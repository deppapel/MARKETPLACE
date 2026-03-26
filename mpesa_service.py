import requests
from requests.auth import HTTPBasicAuth
import base64
from datetime import datetime
from flask import current_app

class MpesaService:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.consumer_key = app.config['MPESA_CONSUMER_KEY']
        self.consumer_secret = app.config['MPESA_CONSUMER_SECRET']
        self.passkey = app.config['MPESA_PASSKEY']
        self.shortcode = app.config['MPESA_SHORTCODE']
        self.base_url = 'https://sandbox.safaricom.co.ke'

    def get_access_token(self):
        """Get OAuth access token from Daraja"""
        auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        try:
            response = requests.get(
                auth_url,
                auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret)
            )
            response.raise_for_status()
            result = response.json()
            print("Token response:", result)  # Debugging line
            return result['access_token']
        except Exception as e:
            print(f"Token error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print("Response content:", e.response.text)  # More debugging info
            return None

    def generate_password(self, timestamp):
        """Generate the base64 encoded password for STK push"""
        data = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data.encode()).decode('utf-8')

    def stk_push(self, phone_number, amount, account_ref):
        """
        Initiate STK push.
        account_ref: string to identify the transaction (e.g., 'REG-1' or 'ORD-5')
        """
        token = self.get_access_token()
        if not token:
            return {'error': 'Could not get access token'}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = self.generate_password(timestamp)

        # Format phone number (remove 0 or +, ensure 254...)
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": "https://yourdomain.com/mpesa/callback",  # you'll replace with a real URL later
            "AccountReference": account_ref,
            "TransactionDesc": "Marketplace Payment"
        }

        headers = {'Authorization': f'Bearer {token}'}
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"STK push error: {e}")
            return {'error': str(e)}