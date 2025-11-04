import requests
import json
from core.config import settings

def initialize_payment(email: str, amount: float, reference: str, metadata: dict = None):
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    
    data = {
        'email': email,
        'amount': int(amount * 100),  
        'reference': reference,
        'currency': 'NGN',
        'callback_url': f"{settings.FRONTEND_URL}/payment/verify",
        'metadata': metadata or {}
    }
    
    try:
        response = requests.post(
            f'{settings.PAYSTACK_BASE_URL}/transaction/initialize',
            headers=headers,
            data=json.dumps(data)
        )
        response.raise_for_status()
        
        result = response.json()
        if result['status']:
            return result['data']
        else:
            return None
    except requests.RequestException as e:
        print(f"Paystack initialization error: {e}")
        return None

def verify_payment(reference: str):
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.get(
            f'{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}',
            headers=headers
        )
        response.raise_for_status()
        
        result = response.json()
        if result['status']:
            return result['data']
        else:
            return None
    except requests.RequestException as e:
        print(f"Paystack verification error: {e}")
        return None

def create_refund(transaction_reference: str, amount: float):
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    
    data = {
        'transaction': transaction_reference,
        'amount': int(amount * 100),  
        'currency': 'NGN',
    }
    
    try:
        response = requests.post(
            f'{settings.PAYSTACK_BASE_URL}/refund',
            headers=headers,
            data=json.dumps(data)
        )
        response.raise_for_status()
        
        result = response.json()
        if result['status']:
            return result['data']
        else:
            return None
    except requests.RequestException as e:
        print(f"Paystack refund error: {e}")
        return None