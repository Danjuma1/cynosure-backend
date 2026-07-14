"""
Thin wrapper around the Paystack REST API. Kept dependency-free (uses
`requests`, already in requirements.txt) so it's easy to mock in tests —
every call goes through `_request`, which callers/tests can monkeypatch.
"""
import hashlib
import hmac
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.paystack.co'


class PaystackError(Exception):
    pass


def _request(method, path, **kwargs):
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError('PAYSTACK_SECRET_KEY is not configured.')
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    headers.update(kwargs.pop('headers', {}))
    response = requests.request(method, f'{BASE_URL}{path}', headers=headers, timeout=15, **kwargs)
    data = response.json()
    if not data.get('status'):
        logger.warning('Paystack API error on %s %s: %s', method, path, data.get('message'))
        raise PaystackError(data.get('message', 'Paystack request failed.'))
    return data['data']


def initialize_transaction(email, amount_kobo, reference, callback_url=None, metadata=None):
    payload = {
        'email': email,
        'amount': amount_kobo,
        'reference': reference,
        'metadata': metadata or {},
    }
    if callback_url:
        payload['callback_url'] = callback_url
    return _request('POST', '/transaction/initialize', json=payload)


def verify_transaction(reference):
    return _request('GET', f'/transaction/verify/{reference}')


def resolve_account_number(account_number, bank_code):
    return _request('GET', '/bank/resolve', params={'account_number': account_number, 'bank_code': bank_code})


def list_banks():
    return _request('GET', '/bank', params={'country': 'nigeria'})


def create_transfer_recipient(name, account_number, bank_code):
    payload = {
        'type': 'nuban',
        'name': name,
        'account_number': account_number,
        'bank_code': bank_code,
        'currency': 'NGN',
    }
    return _request('POST', '/transferrecipient', json=payload)


def refund_transaction(reference, amount_kobo=None):
    payload = {'transaction': reference}
    if amount_kobo is not None:
        payload['amount'] = amount_kobo
    return _request('POST', '/refund', json=payload)


def initiate_transfer(recipient_code, amount_kobo, reason=''):
    payload = {
        'source': 'balance',
        'amount': amount_kobo,
        'recipient': recipient_code,
        'reason': reason,
    }
    return _request('POST', '/transfer', json=payload)


def verify_webhook_signature(request_body, signature_header):
    if not settings.PAYSTACK_SECRET_KEY or not signature_header:
        return False
    computed = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'), request_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, signature_header)
