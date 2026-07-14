"""
Escrow, platform commission, and Paystack payment/payout records for Brief
Connect engagements. Money flow:

  requester --(Paystack charge, agreed_fee + platform fee)--> EscrowAccount
  EscrowAccount --(confirm-completion, Paystack transfer, full agreed_fee)--> holding lawyer
"""
import uuid
from django.db import models
from apps.common.models import TimeStampedModel


class PlatformFeeSetting(TimeStampedModel):
    """
    The commission percentage charged on Brief Connect escrow transactions.
    Admin-editable; `current()` returns the most recently created row so a
    rate change takes effect immediately without a deploy.
    """
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    updated_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.percentage}% (set {self.created_at:%Y-%m-%d})"

    @classmethod
    def current(cls):
        setting = cls.objects.order_by('-created_at').first()
        return setting.percentage if setting else 10  # sane default if none configured yet


class LawyerBankAccount(TimeStampedModel):
    """A verified payout destination for a holding lawyer's escrow releases."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='bank_accounts',
    )
    bank_code = models.CharField(max_length=10)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255, blank=True)
    paystack_recipient_code = models.CharField(max_length=100, blank=True)
    verified = models.BooleanField(default=False)
    is_default = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'bank_code', 'account_number']

    def __str__(self):
        return f"{self.user.full_name} — {self.bank_name} {self.account_number}"


class EscrowAccount(TimeStampedModel):
    """Escrow ledger for a single Brief Connect engagement."""
    STATUS_CHOICES = [
        ('pending', 'Pending Funding'),
        ('funded', 'Funded'),
        ('released', 'Released'),
        ('refunded', 'Refunded'),
        ('disputed', 'Disputed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement = models.OneToOneField(
        'brief_connect.BriefEngagement',
        on_delete=models.CASCADE,
        related_name='escrow',
    )
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_charged = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Escrow for {self.engagement_id} — {self.status}"


class PaystackTransaction(TimeStampedModel):
    """A single Paystack charge attempt to fund an EscrowAccount."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escrow = models.ForeignKey(
        EscrowAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    status = models.CharField(max_length=20, default='pending')
    amount_kobo = models.BigIntegerField()
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PaystackTransaction {self.reference} ({self.status})"


class Payout(TimeStampedModel):
    """A Paystack Transfer releasing escrow funds to the holding lawyer."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escrow = models.ForeignKey(
        EscrowAccount,
        on_delete=models.CASCADE,
        related_name='payouts',
    )
    bank_account = models.ForeignKey(
        LawyerBankAccount,
        on_delete=models.PROTECT,
        related_name='payouts',
    )
    paystack_transfer_code = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='pending')
    amount_kobo = models.BigIntegerField()
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout {self.id} ({self.status})"
