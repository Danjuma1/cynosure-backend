from django.contrib import admin
from .models import PlatformFeeSetting, LawyerBankAccount, EscrowAccount, PaystackTransaction, Payout


@admin.register(PlatformFeeSetting)
class PlatformFeeSettingAdmin(admin.ModelAdmin):
    list_display = ['id', 'percentage', 'updated_by', 'created_at']
    readonly_fields = ['created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LawyerBankAccount)
class LawyerBankAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'bank_name', 'account_number', 'verified', 'is_default']
    list_filter = ['verified', 'is_default']
    search_fields = ['user__email', 'account_number']
    raw_id_fields = ['user']


@admin.register(EscrowAccount)
class EscrowAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'engagement', 'amount_due', 'total_charged', 'status', 'funded_at', 'released_at']
    list_filter = ['status']
    raw_id_fields = ['engagement']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PaystackTransaction)
class PaystackTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'reference', 'escrow', 'status', 'amount_kobo', 'paid_at']
    list_filter = ['status']
    search_fields = ['reference']
    raw_id_fields = ['escrow']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['id', 'escrow', 'bank_account', 'status', 'amount_kobo']
    list_filter = ['status']
    raw_id_fields = ['escrow', 'bank_account']
    readonly_fields = ['created_at', 'updated_at']
