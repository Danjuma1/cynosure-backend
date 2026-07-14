"""
Platform commission arithmetic. The requester pays the agreed fee plus the
platform's cut on top; the holding lawyer's payout is always the full
agreed fee (see apps.payments.models.EscrowAccount).
"""
from decimal import Decimal, ROUND_HALF_UP

from .models import PlatformFeeSetting


def calculate_fee(agreed_fee, percentage=None):
    """Return (fee_amount, total_charged) for a given agreed fee."""
    agreed_fee = Decimal(agreed_fee)
    percentage = Decimal(percentage) if percentage is not None else Decimal(PlatformFeeSetting.current())
    fee_amount = (agreed_fee * percentage / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_charged = agreed_fee + fee_amount
    return fee_amount, total_charged
