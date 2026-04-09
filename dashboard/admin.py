from django.contrib import admin

from .models import LinkedBankAccount, MoneyRequest, PaymentTransaction


@admin.register(LinkedBankAccount)
class LinkedBankAccountAdmin(admin.ModelAdmin):
    list_display = (
        'user_email',
        'bank_name',
        'account_holder_name',
        'masked_account_number',
        'balance',
        'ifsc_code',
        'branch_name',
        'account_type',
        'email_verified',
        'linked_at',
    )
    readonly_fields = (
        'user',
        'bank_name',
        'account_holder_name',
        'account_number',
        'ifsc_code',
        'branch_name',
        'account_type',
        'email_verified',
        'linked_at',
        'updated_at',
    )
    exclude = ('bank_slug', 'debit_card_last6', 'expiry_date', 'upi_id', 'upi_pin')
    search_fields = ('user__email', 'bank_name', 'account_holder_name', 'account_number', 'ifsc_code')

    def user_email(self, obj):
        return obj.user.email

    def masked_account_number(self, obj):
        if len(obj.account_number) <= 4:
            return obj.account_number
        return f"{'*' * (len(obj.account_number) - 4)}{obj.account_number[-4:]}"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('sender_email', 'recipient_upi_id', 'recipient_bank_name', 'amount', 'created_at')
    readonly_fields = ('sender_bank', 'recipient_bank', 'recipient_upi_id', 'amount', 'note', 'created_at')
    search_fields = ('sender_bank__user__email', 'recipient_upi_id', 'recipient_bank__user__email', 'recipient_bank__bank_name')

    def sender_email(self, obj):
        return obj.sender_bank.user.email

    def recipient_bank_name(self, obj):
        return obj.recipient_bank.bank_name

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True


@admin.register(MoneyRequest)
class MoneyRequestAdmin(admin.ModelAdmin):
    list_display = ('requester_email', 'recipient_email', 'recipient_identifier', 'amount', 'status', 'created_at')
    readonly_fields = (
        'requester_bank',
        'recipient_user',
        'recipient_bank',
        'recipient_identifier',
        'amount',
        'note',
        'status',
        'created_at',
    )
    search_fields = (
        'requester_bank__user__email',
        'recipient_user__email',
        'recipient_identifier',
        'requester_bank__account_holder_name',
        'recipient_user__name',
    )

    def requester_email(self, obj):
        return obj.requester_bank.user.email

    def recipient_email(self, obj):
        return obj.recipient_user.email

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True
