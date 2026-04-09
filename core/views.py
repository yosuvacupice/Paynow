import random
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import ContactMessage, UserAccount


def is_password_match(raw_password, stored_password):
    if not stored_password:
        return False

    if stored_password.startswith("pbkdf2_"):
        return check_password(raw_password, stored_password)

    return stored_password == raw_password


def is_valid_person_name(name):
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z\s]{2,19}", name))


def is_valid_profile_name(name, minimum_length=2, maximum_length=50):
    pattern = rf"[A-Za-z][A-Za-z\s]{{{minimum_length - 1},{maximum_length - 1}}}"
    return bool(re.fullmatch(pattern, name))


def home(request):
    return render(request, 'home.html', {'page': 'home'})


def about(request):
    return render(request, 'about.html', {'page': 'about'})


def faq(request):
    return render(request, 'faq.html', {'page': 'faq'})


@ensure_csrf_cookie
def myaccount(request):
    session_user_email = request.session.get('user_email', '')
    otp_verified_for_reset = request.session.get('otp_verified') and request.session.get('otp_email')
    user_email = session_user_email or request.session.get('otp_email', '')

    if not user_email:
        messages.error(request, "Please log in to open account settings.")
        return redirect('/')

    user = UserAccount.objects.filter(email=user_email).first()

    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('/')

    active_section = request.GET.get('section', 'password' if otp_verified_for_reset and not session_user_email else 'personal')

    if request.method == "POST":
        form_type = request.POST.get('form_type')

        if form_type == 'personal':
            if not session_user_email or session_user_email != user.email:
                messages.error(request, "Please log in to update personal information.")
                return redirect('/')

            name = request.POST.get('name', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            gender = request.POST.get('gender', '').strip()

            if len(name) < 3:
                messages.error(request, "Name must be at least 3 characters")
                return redirect('/myaccount/?section=personal')

            if len(name) > 100:
                messages.error(request, "Name must be less than 100 characters")
                return redirect('/myaccount/?section=personal')

            if not re.fullmatch(r"[A-Za-z][A-Za-z\s]{2,99}", name):
                messages.error(request, "Name must contain letters only")
                return redirect('/myaccount/?section=personal')

            if first_name and len(first_name) < 2:
                messages.error(request, "First name must be at least 2 characters")
                return redirect('/myaccount/?section=personal')

            if first_name and not is_valid_profile_name(first_name, minimum_length=2):
                messages.error(request, "First name must contain letters only")
                return redirect('/myaccount/?section=personal')

            if last_name and not is_valid_profile_name(last_name, minimum_length=2):
                messages.error(request, "Last name must contain letters only")
                return redirect('/myaccount/?section=personal')

            if not re.match(r'^[\w\.-]+@gmail\.com$', email):
                messages.error(request, "Enter valid Gmail (example@gmail.com)")
                return redirect('/myaccount/?section=personal')

            existing_user = UserAccount.objects.filter(email=email).exclude(id=user.id).first()
            if existing_user:
                messages.error(request, "Email already exists")
                return redirect('/myaccount/?section=personal')

            if phone_number and not re.match(r'^\d{10}$', phone_number):
                messages.error(request, "Phone number must be 10 digits")
                return redirect('/myaccount/?section=personal')

            user.name = name
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone_number = phone_number
            user.gender = gender
            user.save()

            request.session['user_name'] = user.name
            request.session['user_email'] = user.email

            messages.success(request, "Personal information updated successfully")
            return redirect('/myaccount/?section=personal')

        if form_type == 'password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            otp_verified_for_user = (
                request.session.get('otp_verified') and
                request.session.get('otp_email') == user.email
            )

            if not otp_verified_for_user and not is_password_match(current_password, user.password):
                messages.error(request, "Current password is incorrect.")
                return redirect('/myaccount/?section=password')

            if len(new_password) < 6:
                messages.error(request, "New password must be at least 6 characters")
                return redirect('/myaccount/?section=password')

            if len(new_password) > 20:
                messages.error(request, "New password must be less than 20 characters")
                return redirect('/myaccount/?section=password')

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match")
                return redirect('/myaccount/?section=password')

            user.password = make_password(new_password)
            user.save(update_fields=['password'])
            request.session.pop('otp', None)
            request.session.pop('otp_email', None)
            request.session.pop('otp_verified', None)
            if not session_user_email:
                request.session['user_name'] = user.name
                request.session['user_email'] = user.email
            messages.success(request, "Password updated successfully")
            return redirect('/myaccount/?section=password')

    first_name = user.first_name
    last_name = user.last_name

    if not first_name and user.name:
        name_parts = user.name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ''
        last_name = user.last_name or (name_parts[1] if len(name_parts) > 1 else '')

    return render(request, 'myaccount.html', {
        'page': 'myaccount',
        'active_section': active_section,
        'otp_verified_for_user': (
            request.session.get('otp_verified') and
            request.session.get('otp_email') == user.email
        ),
        'user_name': user.name,
        'user_email': user.email,
        'phone_number': user.phone_number,
        'gender': user.gender,
        'first_name': first_name,
        'last_name': last_name,
    })


def signup(request):
    if request.method == "POST":
        name = request.POST['name'].strip()
        email = request.POST['email'].strip()
        password = request.POST['password']

        if len(name) < 3:
            messages.error(request, "Name must be at least 3 characters")
            return redirect('/')

        if len(name) > 20:
            messages.error(request, "Name must be less than 20 characters")
            return redirect('/')

        if not is_valid_person_name(name):
            messages.error(request, "Name must contain letters only")
            return redirect('/')

        if not re.match(r'^[\w\.-]+@gmail\.com$', email):
            messages.error(request, "Enter valid Gmail (example@gmail.com)")
            return redirect('/')

        if len(email) > 30:
            messages.error(request, "Email must be less than 30 characters")
            return redirect('/')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return redirect('/')

        if len(password) > 20:
            messages.error(request, "Password must be less than 20 characters")
            return redirect('/')

        if UserAccount.objects.filter(email=email).exists():
            messages.error(request, "User already exists")
            return redirect('/')

        name_parts = name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        UserAccount.objects.create(
            name=name,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=make_password(password)
        )
        messages.success(request, "Account created successfully")
        return redirect('/')


def login_view(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']

        user = UserAccount.objects.filter(email=email).first()

        if not user:
            messages.error(request, "User not found.")
            return redirect('/')

        if not is_password_match(password, user.password):
            messages.error(request, "Incorrect password.")
            return redirect('/')

        if not user.password.startswith("pbkdf2_"):
            user.password = make_password(password)
            user.save(update_fields=['password'])

        request.session['user_name'] = user.name
        request.session['user_email'] = user.email
        return redirect('/')


def logout_view(request):
    request.session.flush()
    return redirect('/')


def contact(request):
    user_name = request.session.get('user_name')
    user_email = request.session.get('user_email')

    if request.method == "POST":
        if not user_email:
            messages.error(request, "Please log in to send a message.")
            return redirect('/contact/')

        name = request.POST['name'].strip()
        email = request.POST['email'].strip()
        message = request.POST['message'].strip()

        if not is_valid_profile_name(name, minimum_length=3, maximum_length=50):
            messages.error(request, "Name must contain letters only.")
            return redirect('/contact/')

        if email != user_email or not re.match(r'^[\w\.-]+@gmail\.com$', email):
            messages.error(request, "Use your registered Gmail address.")
            return redirect('/contact/')

        if len(message) < 10:
            messages.error(request, "Message must be at least 10 characters.")
            return redirect('/contact/')

        if len(message) > 500:
            messages.error(request, "Message must be less than 500 characters.")
            return redirect('/contact/')

        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message
        )

        messages.success(request, "Message sent successfully.")
        return redirect('/contact/')

    return render(request, 'contact.html', {
        'page': 'contact',
        'user_name': user_name,
        'user_email': user_email
    })


def send_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=405)

    email = request.POST.get("email", "").strip()

    if not email:
        return JsonResponse({"status": "error", "message": "Email is required"}, status=400)

    user = UserAccount.objects.filter(email=email).first()

    if not user:
        return JsonResponse({"status": "error", "message": "Email not found"}, status=404)

    otp = str(random.randint(100000, 999999))
    request.session['otp'] = otp
    request.session['otp_email'] = email

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return JsonResponse({"status": "error", "message": "Email service is not configured."}, status=500)

    try:
        send_mail(
            "Your PayNow OTP Code",
            f"Your OTP is {otp}. It is valid for your current password reset verification.",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
    except Exception:
        return JsonResponse({"status": "error", "message": "Unable to send OTP email. Check your email settings."}, status=500)

    return JsonResponse({"status": "success", "message": "OTP sent successfully"})


def verify_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=405)

    entered_otp = request.POST.get("otp", "").strip()
    session_otp = request.session.get('otp')
    email = request.session.get('otp_email')

    if entered_otp and entered_otp == session_otp:
        user = UserAccount.objects.filter(email=email).first()

        if user:
            request.session['user_name'] = user.name
            request.session['user_email'] = user.email

        request.session['otp_verified'] = True
        return JsonResponse({
            "status": "success",
            "message": "OTP verified successfully",
            "redirect_url": "/myaccount/?section=password"
        })

    return JsonResponse({"status": "error", "message": "Invalid OTP"}, status=400)
