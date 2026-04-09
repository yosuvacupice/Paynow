from django.db import models

from core.models import UserAccount


class LinkedBankAccount(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='linked_banks')
    bank_slug = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=120)
    account_holder_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=20)
    branch_name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=40)
    debit_card_last6 = models.CharField(max_length=6, blank=True)
    expiry_date = models.CharField(max_length=10, blank=True)
    upi_id = models.CharField(max_length=120, blank=True)
    upi_pin = models.CharField(max_length=255, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=100000.00)
    email_verified = models.BooleanField(default=False)
    linked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.bank_name}"


class PaymentTransaction(models.Model):
    sender_bank = models.ForeignKey(LinkedBankAccount, on_delete=models.CASCADE, related_name='sent_transactions')
    recipient_bank = models.ForeignKey(LinkedBankAccount, on_delete=models.CASCADE, related_name='received_transactions')
    recipient_upi_id = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender_bank.user.email} -> {self.recipient_upi_id} ({self.amount})"


class MoneyRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_DECLINED, 'Declined'),
    ]

    requester_bank = models.ForeignKey(LinkedBankAccount, on_delete=models.CASCADE, related_name='sent_money_requests')
    recipient_user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='received_money_requests')
    recipient_bank = models.ForeignKey(
        LinkedBankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_money_requests'
    )
    recipient_identifier = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.requester_bank.user.email} requested {self.amount} from {self.recipient_user.email}"
