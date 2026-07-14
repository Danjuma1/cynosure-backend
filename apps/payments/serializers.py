from rest_framework import serializers
from .models import LawyerBankAccount, EscrowAccount, PaystackTransaction


class LawyerBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LawyerBankAccount
        fields = [
            'id', 'bank_code', 'bank_name', 'account_number', 'account_name',
            'verified', 'is_default', 'created_at',
        ]
        read_only_fields = ['id', 'account_name', 'verified', 'created_at']


class EscrowAccountSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EscrowAccount
        fields = [
            'id', 'engagement', 'amount_due', 'platform_fee_amount', 'total_charged',
            'status', 'status_display', 'funded_at', 'released_at', 'created_at',
        ]


class PaystackTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaystackTransaction
        fields = ['id', 'reference', 'status', 'amount_kobo', 'paid_at', 'created_at']
