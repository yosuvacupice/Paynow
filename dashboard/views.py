import random
import re
from collections import OrderedDict
from decimal import Decimal, InvalidOperation
from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.db.models import Q, Sum
from django.core.mail import send_mail
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import UserAccount
from .models import LinkedBankAccount, MoneyRequest, PaymentTransaction


POPULAR_BANKS = [
    {"name": "HDFC Bank", "slug": "hdfc-bank", "logo": "images/hdfc_logo.png"},
    {"name": "State Bank of India", "slug": "state-bank-of-india", "logo": "images/state_bank_india_logo.jpg"},
    {"name": "ICICI Bank", "slug": "icici-bank", "logo": "images/icici_logo.jpg"},
    {"name": "Axis Bank", "slug": "axis-bank", "logo": "images/axis_logo.png"},
]

ALL_BANKS = [
    {"name": "Airtel Payments Bank", "slug": "airtel-payments-bank", "logo": "images/airtel_payment_logo.png"},
    {"name": "Bank of Baroda", "slug": "bank-of-baroda", "logo": "images/bank_baroda_logo.png"},
    {"name": "Canara Bank", "slug": "canara-bank", "logo": "images/canara_logo.png"},
    {"name": "Central Bank of India", "slug": "central-bank-of-india", "logo": "images/cantral_bank_india_logo.png"},
    {"name": "State Bank of India", "slug": "state-bank-of-india", "logo": "images/state_bank_india_logo.jpg"},
    {"name": "India Bank", "slug": "india-bank", "logo": "images/india_bank_logo.png"},
    {"name": "Paytm Payments Bank", "slug": "paytm-payments-bank", "logo": "images/paytm_payments_logo.png"},
    {"name": "Punjab National Bank", "slug": "punjab-national-bank", "logo": "images/punjab_national_bank_logo.png"},
    {"name": "Union Bank of India", "slug": "union-bank-of-india", "logo": "images/union_bank_logo.png"},
    {"name": "Yes Bank", "slug": "yes-bank", "logo": "images/yes_bank_logo.png"},
]

ACCOUNT_TYPE_OPTIONS = ["Savings", "Current", "Salary", "Business"]


def get_bank_name(bank_slug):
    for bank in POPULAR_BANKS + ALL_BANKS:
        if bank["slug"] == bank_slug:
            return bank["name"]
    return bank_slug.replace('-', ' ').title()


def get_bank_logo(bank_slug):
    for bank in POPULAR_BANKS + ALL_BANKS:
        if bank["slug"] == bank_slug:
            return bank["logo"]
    return "images/hdfc_logo.png"


def get_dashboard_user_and_bank(request):
    user_email = request.session.get('user_email')
    if not user_email:
        return None, None, None

    user = UserAccount.objects.filter(email=user_email).first()
    if not user:
        return None, None, None

    linked_bank = LinkedBankAccount.objects.filter(user=user).order_by('-updated_at').first()
    if not linked_bank:
        return user, None, None

    linked_bank_public = {
        'bank_name': linked_bank.bank_name,
        'bank_slug': linked_bank.bank_slug,
        'bank_logo': get_bank_logo(linked_bank.bank_slug),
        'account_holder_name': linked_bank.account_holder_name,
        'account_number': linked_bank.account_number,
        'ifsc_code': linked_bank.ifsc_code,
        'account_type': linked_bank.account_type,
        'phone_number': user.phone_number if user.phone_number else "Not added",
        'upi_id': linked_bank.upi_id or "Not set",
        'upi_pin_masked': '******' if linked_bank.upi_pin else "Not set",
        'balance': linked_bank.balance,
    }
    return user, linked_bank, linked_bank_public


def dashboard_home(request):
    user, linked_bank, linked_bank_public = get_dashboard_user_and_bank(request)

    success_message = request.session.pop('dashboard_success_message', '')
    notice_message = request.session.pop('dashboard_notice_message', '')
    notice_type = request.session.pop('dashboard_notice_type', '')

    return render(request, 'dashboard/dashboard_home.html', {
        'page': 'dashboard',
        'popular_banks': POPULAR_BANKS,
        'all_banks': ALL_BANKS,
        'linked_bank': linked_bank_public,
        'dashboard_success_message': success_message,
        'dashboard_notice_message': notice_message,
        'dashboard_notice_type': notice_type,
    })


def dashboard_overview(request):
    user, linked_bank, linked_bank_public = get_dashboard_user_and_bank(request)

    if not request.session.get('user_email'):
        return redirect('/dashboard/')

    if not user or not linked_bank or not linked_bank_public:
        messages.error(request, "Please link your bank account first.")
        return redirect('/dashboard/')

    return render(request, 'dashboard/dashboard_overview.html', {
        'page': 'dashboard_overview',
        'linked_bank': linked_bank_public,
        'overview_transactions': build_dashboard_overview_transactions(linked_bank),
    })


def view_qr_code(request):
    if not request.session.get('user_email'):
        return redirect('/dashboard/')

    user, linked_bank, linked_bank_public = get_dashboard_user_and_bank(request)
    if not user or not linked_bank or not linked_bank_public:
        messages.error(request, "Please link your bank account first.")
        return redirect('/dashboard/')

    scan_url = build_qr_scan_url(request, linked_bank.upi_id)
    qr_image_url = build_qr_image_url(scan_url)

    return render(request, 'dashboard/view_qr_code.html', {
        'page': 'view_qr_code',
        'linked_bank': linked_bank_public,
        'qr_scan_url': scan_url,
        'qr_image_url': qr_image_url,
    })


def qr_pay_redirect(request):
    upi_id = request.GET.get('upi', '').strip()

    if not upi_id:
        request.session['dashboard_notice_message'] = "Invalid QR code."
        request.session['dashboard_notice_type'] = "error"
        return redirect('/dashboard/')

    target_bank = LinkedBankAccount.objects.filter(upi_id__iexact=upi_id).first()
    if not target_bank:
        request.session['dashboard_notice_message'] = "This QR code is not linked to a valid UPI account."
        request.session['dashboard_notice_type'] = "error"
        return redirect('/dashboard/')

    if not request.session.get('user_email'):
        request.session['dashboard_notice_message'] = "You must log in before using this QR code."
        request.session['dashboard_notice_type'] = "error"
        return redirect('/dashboard/')

    user, linked_bank, _ = get_dashboard_user_and_bank(request)
    if not user:
        request.session['dashboard_notice_message'] = "You must log in before using this QR code."
        request.session['dashboard_notice_type'] = "error"
        return redirect('/dashboard/')

    if not linked_bank:
        request.session['dashboard_notice_message'] = "Link your bank account before sending a payment."
        request.session['dashboard_notice_type'] = "error"
        return redirect('/dashboard/')

    query = urlencode({'recipient': target_bank.upi_id})
    return redirect(f"/dashboard/send-money/?{query}")


def send_money(request):
    user_email = request.session.get('user_email')

    if not user_email:
        return redirect('/dashboard/')

    user = UserAccount.objects.filter(email=user_email).first()
    if not user:
        return redirect('/dashboard/')

    linked_bank = LinkedBankAccount.objects.filter(user=user).order_by('-updated_at').first()
    if not linked_bank:
        messages.error(request, "Please link your bank account first.")
        return redirect('/dashboard/')

    form_values = {
        'recipient_upi_id': request.GET.get('recipient', '').strip(),
        'amount': request.GET.get('amount', '').strip(),
        'note': '',
        'balance_pin': '',
        'payment_pin': '',
    }
    form_errors = {}
    balance_status = {}
    payment_status = {}
    open_balance_panel = False
    open_payment_panel = False

    if request.method == "POST":
        action = request.POST.get('action', '').strip()
        form_values = {
            'recipient_upi_id': request.POST.get('recipient_upi_id', '').strip(),
            'amount': request.POST.get('amount', '').strip(),
            'note': request.POST.get('note', '').strip(),
            'balance_pin': request.POST.get('balance_pin', '').strip(),
            'payment_pin': request.POST.get('payment_pin', '').strip(),
        }

        if action == 'check_balance':
            open_balance_panel = True
            balance_pin = form_values['balance_pin']

            if not linked_bank.upi_pin:
                balance_status = {'type': 'error', 'message': "Set your UPI PIN before checking balance."}
            elif not balance_pin:
                form_errors['balance_pin'] = "Enter your 6 digit UPI PIN."
            elif not balance_pin.isdigit() or len(balance_pin) != 6:
                form_errors['balance_pin'] = "UPI PIN must be exactly 6 digits."
            elif not check_password(balance_pin, linked_bank.upi_pin):
                form_errors['balance_pin'] = "Incorrect UPI PIN."
            else:
                balance_status = {
                    'type': 'success',
                    'message': f"Available balance: Rs. {linked_bank.balance:.2f}"
                }

        elif action == 'send_money':
            open_payment_panel = True
            recipient_upi_id = form_values['recipient_upi_id']
            note = form_values['note']
            payment_pin = form_values['payment_pin']
            recipient_bank = None
            amount = None

            if not recipient_upi_id:
                form_errors['recipient_upi_id'] = "Recipient UPI ID is required."
            elif not re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", recipient_upi_id):
                form_errors['recipient_upi_id'] = "Use valid UPI ID like name@bank."
            elif linked_bank.upi_id and recipient_upi_id.lower() == linked_bank.upi_id.lower():
                form_errors['recipient_upi_id'] = "You cannot send money to your own UPI ID."
            else:
                recipient_bank = LinkedBankAccount.objects.filter(upi_id__iexact=recipient_upi_id).exclude(id=linked_bank.id).first()
                if not recipient_bank:
                    form_errors['recipient_upi_id'] = "This UPI ID is not linked to any user."

            if not form_values['amount']:
                form_errors['amount'] = "Amount is required."
            else:
                try:
                    amount = Decimal(form_values['amount'])
                except (InvalidOperation, TypeError):
                    form_errors['amount'] = "Enter a valid amount."

            if amount is not None:
                if amount <= 0:
                    form_errors['amount'] = "Amount must be greater than zero."
                elif amount > Decimal('10000.00'):
                    form_errors['amount'] = "Per day transfer limit is Rs. 10,000."

            if note and len(note) > 160:
                form_errors['note'] = "Note can be at most 160 characters."

            if not linked_bank.upi_pin:
                form_errors['payment_pin'] = "Set your UPI PIN before sending money."
            elif not payment_pin:
                form_errors['payment_pin'] = "Enter your 6 digit UPI PIN."
            elif not payment_pin.isdigit() or len(payment_pin) != 6:
                form_errors['payment_pin'] = "UPI PIN must be exactly 6 digits."
            elif not check_password(payment_pin, linked_bank.upi_pin):
                form_errors['payment_pin'] = "Incorrect UPI PIN."

            if amount is not None and 'amount' not in form_errors:
                today = timezone.localdate()
                daily_total = PaymentTransaction.objects.filter(
                    sender_bank=linked_bank,
                    created_at__date=today,
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

                if daily_total + amount > Decimal('10000.00'):
                    remaining = max(Decimal('0.00'), Decimal('10000.00') - daily_total)
                    form_errors['amount'] = f"Today's remaining limit is Rs. {remaining:.2f}."
                elif linked_bank.balance < amount:
                    form_errors['amount'] = "Insufficient balance in your linked account."

            if not form_errors and recipient_bank and amount is not None:
                with transaction.atomic():
                    sender_bank = LinkedBankAccount.objects.select_for_update().get(id=linked_bank.id)
                    receiver_bank = LinkedBankAccount.objects.select_for_update().get(id=recipient_bank.id)

                    if sender_bank.balance < amount:
                        form_errors['amount'] = "Insufficient balance in your linked account."
                    else:
                        sender_bank.balance -= amount
                        receiver_bank.balance += amount
                        sender_bank.save(update_fields=['balance', 'updated_at'])
                        receiver_bank.save(update_fields=['balance', 'updated_at'])

                        PaymentTransaction.objects.create(
                            sender_bank=sender_bank,
                            recipient_bank=receiver_bank,
                            recipient_upi_id=receiver_bank.upi_id,
                            amount=amount,
                            note=note,
                        )

                        request.session['dashboard_success_message'] = "Payment sent successfully."
                        return redirect('/dashboard/send-money/')

            if form_errors:
                payment_status = {'type': 'error', 'message': "Please fix the highlighted fields and try again."}

    recent_payments = []
    for payment in PaymentTransaction.objects.filter(sender_bank=linked_bank)[:5]:
        recent_payments.append({
            'recipient_name': payment.recipient_bank.account_holder_name or payment.recipient_bank.user.name,
            'recipient_upi_id': payment.recipient_upi_id,
            'amount': payment.amount,
            'time_label': get_payment_time_label(payment.created_at),
        })

    success_message = request.session.pop('dashboard_success_message', '')
    if success_message:
        payment_status = {'type': 'success', 'message': success_message}

    return render(request, 'dashboard/send_money.html', {
        'page': 'send_money',
        'linked_bank': linked_bank,
        'form_values': form_values,
        'form_errors': form_errors,
        'recent_payments': recent_payments,
        'balance_status': balance_status,
        'payment_status': payment_status,
        'open_balance_panel': open_balance_panel,
        'open_payment_panel': open_payment_panel,
    })


def request_money(request):
    user_email = request.session.get('user_email')

    if not user_email:
        return redirect('/dashboard/')

    user = UserAccount.objects.filter(email=user_email).first()
    if not user:
        return redirect('/dashboard/')

    linked_bank = LinkedBankAccount.objects.filter(user=user).order_by('-updated_at').first()
    if not linked_bank:
        messages.error(request, "Please link your bank account first.")
        return redirect('/dashboard/')

    form_values = {
        'recipient_identifier': request.GET.get('recipient', '').strip(),
        'amount': '',
        'note': '',
    }
    form_errors = {}
    request_status = {}

    if request.method == "POST":
        form_values = {
            'recipient_identifier': request.POST.get('recipient_identifier', '').strip(),
            'amount': request.POST.get('amount', '').strip(),
            'note': request.POST.get('note', '').strip(),
        }

        recipient_identifier = form_values['recipient_identifier']
        note = form_values['note']
        recipient_user = None
        recipient_bank = None
        amount = None

        if not recipient_identifier:
            form_errors['recipient_identifier'] = "Receiver UPI ID or phone number is required."
        elif re.fullmatch(r'\d{10}', recipient_identifier):
            recipient_user = UserAccount.objects.filter(phone_number=recipient_identifier).first()
            if not recipient_user:
                form_errors['recipient_identifier'] = "This phone number is not registered."
            elif user.phone_number and recipient_identifier == user.phone_number:
                form_errors['recipient_identifier'] = "You cannot request money from your own number."
            else:
                recipient_bank = LinkedBankAccount.objects.filter(user=recipient_user).order_by('-updated_at').first()
        elif re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", recipient_identifier):
            recipient_bank = LinkedBankAccount.objects.filter(upi_id__iexact=recipient_identifier).first()
            if not recipient_bank:
                form_errors['recipient_identifier'] = "This UPI ID is not linked to any user."
            elif linked_bank.upi_id and recipient_identifier.lower() == linked_bank.upi_id.lower():
                form_errors['recipient_identifier'] = "You cannot request money from your own UPI ID."
            else:
                recipient_user = recipient_bank.user
        else:
            form_errors['recipient_identifier'] = "Enter a valid UPI ID or 10 digit phone number."

        if recipient_user and recipient_user.id == user.id:
            form_errors['recipient_identifier'] = "You cannot request money from yourself."

        if not form_values['amount']:
            form_errors['amount'] = "Amount is required."
        else:
            try:
                amount = Decimal(form_values['amount'])
            except (InvalidOperation, TypeError):
                form_errors['amount'] = "Enter a valid amount."

        if amount is not None:
            if amount <= 0:
                form_errors['amount'] = "Amount must be greater than zero."
            elif amount > Decimal('10000.00'):
                form_errors['amount'] = "Request amount limit is Rs. 10,000."

        if note and len(note) > 160:
            form_errors['note'] = "Note can be at most 160 characters."

        if not form_errors and recipient_user and amount is not None:
            MoneyRequest.objects.create(
                requester_bank=linked_bank,
                recipient_user=recipient_user,
                recipient_bank=recipient_bank,
                recipient_identifier=recipient_identifier,
                amount=amount,
                note=note,
            )
            request.session['dashboard_success_message'] = "Money request sent successfully."
            return redirect('/dashboard/request-money/')

        if form_errors:
            request_status = {'type': 'error', 'message': "Please fix the highlighted fields and try again."}

    recent_transactions = build_recent_request_transactions(user, linked_bank)
    recent_contacts = build_recent_request_contacts(user, linked_bank)

    selected_contact_name = ''
    if form_values['recipient_identifier']:
        matched_contact = next(
            (contact for contact in recent_contacts if contact['identifier'] == form_values['recipient_identifier']),
            None
        )
        if matched_contact:
            selected_contact_name = matched_contact['name']
        else:
            selected_contact_name = get_recipient_name_from_identifier(form_values['recipient_identifier'])

    success_message = request.session.pop('dashboard_success_message', '')
    if success_message:
        request_status = {'type': 'success', 'message': success_message}

    return render(request, 'dashboard/request_money.html', {
        'page': 'request_money',
        'linked_bank': linked_bank,
        'form_values': form_values,
        'form_errors': form_errors,
        'request_status': request_status,
        'recent_transactions': recent_transactions,
        'recent_contacts': recent_contacts,
        'selected_contact_name': selected_contact_name,
    })


def decline_money_request(request, request_id):
    if request.method != "POST":
        return redirect('/dashboard/')

    user_email = request.session.get('user_email')
    if not user_email:
        return redirect('/dashboard/')

    user = UserAccount.objects.filter(email=user_email).first()
    if not user:
        return redirect('/dashboard/')

    money_request = MoneyRequest.objects.filter(
        id=request_id,
        recipient_user=user,
        status=MoneyRequest.STATUS_PENDING,
    ).first()

    if money_request:
        money_request.status = MoneyRequest.STATUS_DECLINED
        money_request.save(update_fields=['status'])

    return redirect(request.META.get('HTTP_REFERER', '/dashboard/'))


def link_bank_verify(request, bank_slug):
    user_email = request.session.get('user_email')

    if not user_email:
        return redirect('/dashboard/')

    bank_name = get_bank_name(bank_slug)

    return render(request, 'dashboard/link_bank_verify.html', {
        'page': 'dashboard',
        'selected_bank_slug': bank_slug,
        'selected_bank_name': bank_name,
        'user_email': user_email,
    })


def link_bank_details(request, bank_slug):
    user_email = request.session.get('user_email')

    if not user_email:
        return redirect('/dashboard/')

    user = UserAccount.objects.filter(email=user_email).first()
    if not user:
        return redirect('/dashboard/')

    existing_bank = LinkedBankAccount.objects.filter(user=user, bank_slug=bank_slug).first()

    if not existing_bank and (not request.session.get('bank_verify_success') or request.session.get('bank_verify_slug') != bank_slug):
        messages.error(request, "Please verify your email first.")
        return redirect(f'/dashboard/link-bank/{bank_slug}/')

    bank_name = get_bank_name(bank_slug)
    form_values = {
        'account_holder_name': existing_bank.account_holder_name if existing_bank else '',
        'account_number': existing_bank.account_number if existing_bank else '',
        'ifsc_code': existing_bank.ifsc_code if existing_bank else '',
        'branch_name': existing_bank.branch_name if existing_bank else '',
        'account_type': existing_bank.account_type if existing_bank else '',
    }
    form_errors = {}

    if request.method == "POST":
        account_holder_name = request.POST.get('account_holder_name', '').strip()
        account_number = request.POST.get('account_number', '').strip()
        ifsc_code = request.POST.get('ifsc_code', '').strip().upper()
        branch_name = request.POST.get('branch_name', '').strip()
        account_type = request.POST.get('account_type', '').strip()
        form_values = {
            'account_holder_name': account_holder_name,
            'account_number': account_number,
            'ifsc_code': ifsc_code,
            'branch_name': branch_name,
            'account_type': account_type,
        }

        if not account_holder_name or not account_number or not ifsc_code or not branch_name or not account_type:
            if not account_holder_name:
                form_errors['account_holder_name'] = "Account holder name is required."
            if not account_number:
                form_errors['account_number'] = "Account number is required."
            if not ifsc_code:
                form_errors['ifsc_code'] = "IFSC code is required."
            if not branch_name:
                form_errors['branch_name'] = "Branch name is required."
            if not account_type:
                form_errors['account_type'] = "Please select an account type."
        elif len(account_holder_name) < 3:
            form_errors['account_holder_name'] = "Minimum 3 characters required."
        elif not account_number.isdigit():
            form_errors['account_number'] = "Digits only allowed."
        elif len(account_number) < 9 or len(account_number) > 18:
            form_errors['account_number'] = "Enter 9 to 18 digits."
        elif not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc_code):
            form_errors['ifsc_code'] = "Use valid IFSC format like ABCD0123456."
        elif account_type not in ACCOUNT_TYPE_OPTIONS:
            form_errors['account_type'] = "Choose a valid account type."
        else:
            linked_bank, _ = LinkedBankAccount.objects.get_or_create(
                user=user,
                bank_slug=bank_slug,
                defaults={
                    'bank_name': bank_name,
                    'account_holder_name': account_holder_name,
                    'account_number': account_number,
                    'ifsc_code': ifsc_code,
                    'branch_name': branch_name,
                    'account_type': account_type,
                    'email_verified': True,
                }
            )

            linked_bank.bank_name = bank_name
            linked_bank.account_holder_name = account_holder_name
            linked_bank.account_number = account_number
            linked_bank.ifsc_code = ifsc_code
            linked_bank.branch_name = branch_name
            linked_bank.account_type = account_type
            linked_bank.email_verified = True
            linked_bank.save()

            request.session['linked_bank_id'] = linked_bank.id
            return redirect(f'/dashboard/link-bank/{bank_slug}/set-upi/')

    return render(request, 'dashboard/link_bank_details.html', {
        'page': 'dashboard',
        'selected_bank_slug': bank_slug,
        'selected_bank_name': bank_name,
        'form_values': form_values,
        'form_errors': form_errors,
        'account_type_options': ACCOUNT_TYPE_OPTIONS,
    })


def set_upi_pin(request, bank_slug):
    user_email = request.session.get('user_email')
    linked_bank_id = request.session.get('linked_bank_id')

    if not user_email or not linked_bank_id:
        return redirect('/dashboard/')

    user = UserAccount.objects.filter(email=user_email).first()
    linked_bank = LinkedBankAccount.objects.filter(id=linked_bank_id, user=user, bank_slug=bank_slug).first()

    if not linked_bank:
        return redirect('/dashboard/')

    form_values = {
        'debit_card_last6': '',
        'expiry_date': '',
        'upi_id': '',
        'upi_pin': '',
        'confirm_upi_pin': '',
    }
    form_errors = {}

    if request.method == "POST":
        debit_card_last6 = request.POST.get('debit_card_last6', '').strip()
        expiry_date = request.POST.get('expiry_date', '').strip()
        upi_id = request.POST.get('upi_id', '').strip()
        upi_pin = request.POST.get('upi_pin', '').strip()
        confirm_upi_pin = request.POST.get('confirm_upi_pin', '').strip()
        form_values = {
            'debit_card_last6': debit_card_last6,
            'expiry_date': expiry_date,
            'upi_id': upi_id,
            'upi_pin': upi_pin,
            'confirm_upi_pin': confirm_upi_pin,
        }

        if not debit_card_last6 or not expiry_date or not upi_id or not upi_pin or not confirm_upi_pin:
            if not debit_card_last6:
                form_errors['debit_card_last6'] = "Last 6 digits are required."
            if not expiry_date:
                form_errors['expiry_date'] = "Expiry date is required."
            if not upi_id:
                form_errors['upi_id'] = "UPI ID is required."
            if not upi_pin:
                form_errors['upi_pin'] = "UPI PIN is required."
            if not confirm_upi_pin:
                form_errors['confirm_upi_pin'] = "Please confirm your UPI PIN."
        elif not debit_card_last6.isdigit() or len(debit_card_last6) != 6:
            form_errors['debit_card_last6'] = "Enter exactly 6 digits."
        elif not re.fullmatch(r"(0[1-9]|1[0-2])/[0-9]{2}", expiry_date):
            form_errors['expiry_date'] = "Use MM/YY format."
        elif not is_valid_future_expiry(expiry_date):
            form_errors['expiry_date'] = "Enter current or future expiry date."
        elif not re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", upi_id):
            form_errors['upi_id'] = "Use valid UPI ID like name@bank."
        elif not upi_pin.isdigit() or len(upi_pin) != 6:
            form_errors['upi_pin'] = "UPI PIN must be exactly 6 digits."
        elif upi_pin != confirm_upi_pin:
            form_errors['confirm_upi_pin'] = "UPI PIN does not match."
        else:
            linked_bank.debit_card_last6 = debit_card_last6
            linked_bank.expiry_date = expiry_date
            linked_bank.upi_id = upi_id
            linked_bank.upi_pin = make_password(upi_pin)
            linked_bank.save()

            request.session.pop('bank_verify_otp', None)
            request.session.pop('bank_verify_email', None)
            request.session.pop('bank_verify_slug', None)
            request.session.pop('bank_verify_success', None)
            request.session.pop('linked_bank_id', None)
            request.session['dashboard_success_message'] = "Bank account linked successfully."

            messages.success(request, "Bank account linked successfully.")
            return redirect('/dashboard/')

    return render(request, 'dashboard/set_upi_pin.html', {
        'page': 'dashboard',
        'selected_bank_name': linked_bank.bank_name,
        'form_values': form_values,
        'form_errors': form_errors,
    })


def send_bank_verification_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=405)

    session_email = request.session.get('user_email')
    email = request.POST.get("email", "").strip()
    bank_slug = request.POST.get("bank_slug", "").strip()

    if not session_email:
        return JsonResponse({"status": "error", "message": "You must log in first."}, status=403)

    if not email:
        return JsonResponse({"status": "error", "message": "Please enter your email address."}, status=400)

    if email.lower() != session_email.lower():
        return JsonResponse({"status": "error", "message": "Wrong email address."}, status=400)

    user = UserAccount.objects.filter(email=session_email).first()
    if not user:
        return JsonResponse({"status": "error", "message": "User not found."}, status=404)

    otp = str(random.randint(100000, 999999))
    request.session['bank_verify_otp'] = otp
    request.session['bank_verify_email'] = session_email
    request.session['bank_verify_slug'] = bank_slug

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return JsonResponse({"status": "error", "message": "Email service is not configured."}, status=500)

    try:
        send_mail(
            "Your PayNow Bank Verification OTP",
            f"Your OTP is {otp}. Use it to verify your email before linking your bank account.",
            settings.EMAIL_HOST_USER,
            [session_email],
            fail_silently=False,
        )
    except Exception:
        return JsonResponse({"status": "error", "message": "Unable to send OTP email. Check your email settings."}, status=500)

    return JsonResponse({"status": "success", "message": "OTP sent successfully."})


def verify_bank_verification_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=405)

    session_email = request.session.get('user_email')
    entered_otp = request.POST.get("otp", "").strip()
    session_otp = request.session.get("bank_verify_otp")

    if not session_email:
        return JsonResponse({"status": "error", "message": "You must log in first."}, status=403)

    if not entered_otp:
        return JsonResponse({"status": "error", "message": "Please enter the OTP."}, status=400)

    if entered_otp != session_otp:
        return JsonResponse({"status": "error", "message": "OTP verification failed."}, status=400)

    request.session['bank_verify_success'] = True
    return JsonResponse({
        "status": "success",
        "message": "OTP verified successfully.",
        "redirect_url": f"/dashboard/link-bank/{request.session.get('bank_verify_slug')}/details/"
    })


def is_valid_future_expiry(expiry_date):
    try:
        month, year = expiry_date.split('/')
        expiry = datetime(int(f"20{year}"), int(month), 1)
        current = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return expiry >= current
    except (ValueError, TypeError):
        return False


def get_payment_time_label(created_at):
    local_time = timezone.localtime(created_at)
    today = timezone.localdate()
    payment_date = local_time.date()

    if payment_date == today:
        return "Sent today"
    if (today - payment_date).days == 1:
        return "Sent yesterday"
    if (today - payment_date).days < 7:
        return f"Sent on {payment_date.strftime('%A').lower()}"
    return f"Sent on {payment_date.strftime('%d %b %Y')}"


def get_request_time_label(created_at):
    local_time = timezone.localtime(created_at)
    today = timezone.localdate()
    request_date = local_time.date()

    if request_date == today:
        return "Requested today"
    if (today - request_date).days == 1:
        return "Requested yesterday"
    if (today - request_date).days < 7:
        return f"Requested on {request_date.strftime('%A').lower()}"
    return f"Requested on {request_date.strftime('%d %b %Y')}"


def build_recent_request_transactions(user, linked_bank):
    recent_items = []
    requests = MoneyRequest.objects.filter(
        Q(requester_bank=linked_bank) | Q(recipient_user=user)
    ).select_related('requester_bank__user', 'recipient_user')[:5]

    for money_request in requests:
        is_sent = money_request.requester_bank_id == linked_bank.id
        counterpart_user = money_request.recipient_user if is_sent else money_request.requester_bank.user
        recent_items.append({
            'name': counterpart_user.name,
            'amount': money_request.amount,
            'time_label': get_request_time_label(money_request.created_at),
            'direction_label': 'Request sent' if is_sent else 'Request received',
        })

    return recent_items


def build_recent_request_contacts(user, linked_bank):
    contacts = OrderedDict()

    recent_payments = PaymentTransaction.objects.filter(
        Q(sender_bank=linked_bank) | Q(recipient_bank=linked_bank)
    ).select_related('sender_bank__user', 'recipient_bank__user')[:8]
    recent_requests = MoneyRequest.objects.filter(
        Q(requester_bank=linked_bank) | Q(recipient_user=user)
    ).select_related('requester_bank__user', 'recipient_user', 'recipient_bank')[:8]

    for payment in recent_payments:
        counterpart_bank = payment.recipient_bank if payment.sender_bank_id == linked_bank.id else payment.sender_bank
        counterpart_user = counterpart_bank.user
        identifier = counterpart_user.phone_number or counterpart_bank.upi_id

        if identifier and counterpart_user.id != user.id and identifier not in contacts:
            contacts[identifier] = {
                'name': counterpart_user.name,
                'identifier': identifier,
                'initial': (counterpart_user.name[:1] or 'U').upper(),
            }

    for money_request in recent_requests:
        if money_request.requester_bank_id == linked_bank.id:
            counterpart_user = money_request.recipient_user
            identifier = counterpart_user.phone_number or (money_request.recipient_bank.upi_id if money_request.recipient_bank else money_request.recipient_identifier)
        else:
            counterpart_user = money_request.requester_bank.user
            identifier = counterpart_user.phone_number or money_request.requester_bank.upi_id

        if identifier and counterpart_user.id != user.id and identifier not in contacts:
            contacts[identifier] = {
                'name': counterpart_user.name,
                'identifier': identifier,
                'initial': (counterpart_user.name[:1] or 'U').upper(),
            }

    return list(contacts.values())[:4]


def get_recipient_name_from_identifier(identifier):
    if re.fullmatch(r'\d{10}', identifier):
        user = UserAccount.objects.filter(phone_number=identifier).first()
        return user.name if user else ''

    bank = LinkedBankAccount.objects.filter(upi_id__iexact=identifier).select_related('user').first()
    if bank:
        return bank.user.name

    return ''


def build_dashboard_overview_transactions(linked_bank):
    transactions = PaymentTransaction.objects.filter(
        Q(sender_bank=linked_bank) | Q(recipient_bank=linked_bank)
    ).select_related('sender_bank__user', 'recipient_bank__user')

    overview_rows = []
    for payment in transactions:
        is_sent = payment.sender_bank_id == linked_bank.id
        counterpart_bank = payment.recipient_bank if is_sent else payment.sender_bank
        counterpart_name = counterpart_bank.account_holder_name or counterpart_bank.user.name
        created_local = timezone.localtime(payment.created_at)
        amount_value = float(payment.amount)

        overview_rows.append({
            'id': payment.id,
            'date': created_local.date().isoformat(),
            'datetime': created_local.isoformat(),
            'display_date': created_local.strftime('%b %d, %Y'),
            'weekday': created_local.strftime('%A'),
            'time': created_local.strftime('%I:%M %p'),
            'counterpart': counterpart_name,
            'upi_id': counterpart_bank.upi_id or '',
            'note': payment.note or ('Payment transfer' if is_sent else 'Money received'),
            'amount': amount_value,
            'signed_amount': -amount_value if is_sent else amount_value,
            'direction': 'Sent' if is_sent else 'Received',
            'flow_label': 'Deducted' if is_sent else 'Received',
            'status': 'Completed',
        })

    return overview_rows


def build_qr_scan_url(request, upi_id):
    base_url = request.build_absolute_uri(reverse('qr_pay_redirect'))
    return f"{base_url}?{urlencode({'upi': upi_id})}"


def build_qr_image_url(scan_url):
    return f"https://quickchart.io/qr?size=320&format=png&text={urlencode({'': scan_url})[1:]}"
