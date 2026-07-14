"""
Shared escrow release/refund logic, used by both the happy-path completion
flow (apps.brief_connect confirm-completion) and dispute resolution
(apps.disputes resolve action).
"""
import logging
from decimal import Decimal

from django.utils import timezone

from . import paystack
from .models import Payout

logger = logging.getLogger(__name__)


def _get_or_create_recipient(bank_account):
    if bank_account.paystack_recipient_code:
        return bank_account.paystack_recipient_code
    recipient = paystack.create_transfer_recipient(
        name=bank_account.account_name or bank_account.user.full_name,
        account_number=bank_account.account_number,
        bank_code=bank_account.bank_code,
    )
    bank_account.paystack_recipient_code = recipient['recipient_code']
    bank_account.save(update_fields=['paystack_recipient_code'])
    return bank_account.paystack_recipient_code


def release_to_lawyer(escrow, amount=None):
    """Transfer `amount` (defaults to the full agreed fee) to the holding lawyer."""
    holding_lawyer = escrow.engagement.holding_lawyer
    bank_account = holding_lawyer.bank_accounts.filter(is_default=True).first()
    if not bank_account:
        raise ValueError('The holding lawyer has not added a payout bank account yet.')

    amount = Decimal(amount) if amount is not None else escrow.amount_due
    amount_kobo = int(amount * 100)
    recipient_code = _get_or_create_recipient(bank_account)

    payout = Payout.objects.create(
        escrow=escrow, bank_account=bank_account, amount_kobo=amount_kobo, status='pending',
    )
    try:
        result = paystack.initiate_transfer(
            recipient_code, amount_kobo, reason=f'Brief Connect escrow release — engagement {escrow.engagement_id}',
        )
        payout.paystack_transfer_code = result.get('transfer_code', '')
        payout.status = result.get('status', 'pending')
        payout.raw_response = result
        payout.save(update_fields=['paystack_transfer_code', 'status', 'raw_response'])
    except paystack.PaystackError as exc:
        payout.status = 'failed'
        payout.raw_response = {'error': str(exc)}
        payout.save(update_fields=['status', 'raw_response'])
        logger.warning('Brief Connect: payout %s failed: %s', payout.id, exc)
        raise
    return payout


def refund_to_requester(escrow, amount=None):
    """Refund `amount` (defaults to the full amount charged) to the requester's original payment."""
    transaction = escrow.transactions.filter(status='success').order_by('-created_at').first()
    if not transaction:
        raise ValueError('No successful escrow payment found to refund.')

    amount_kobo = int(Decimal(amount) * 100) if amount is not None else None
    result = paystack.refund_transaction(transaction.reference, amount_kobo)
    return result


def release_escrow_full(escrow):
    payout = release_to_lawyer(escrow)
    escrow.status = 'released'
    escrow.released_at = timezone.now()
    escrow.save(update_fields=['status', 'released_at', 'updated_at'])
    return payout


def refund_escrow_full(escrow):
    result = refund_to_requester(escrow)
    escrow.status = 'refunded'
    escrow.save(update_fields=['status', 'updated_at'])
    return result


def split_escrow(escrow, lawyer_amount, requester_refund_amount):
    payout = release_to_lawyer(escrow, amount=lawyer_amount)
    refund_result = refund_to_requester(escrow, amount=requester_refund_amount)
    escrow.status = 'released'
    escrow.released_at = timezone.now()
    escrow.save(update_fields=['status', 'released_at', 'updated_at'])
    return payout, refund_result
