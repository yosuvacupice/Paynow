from django.urls import path

from . import views


urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('overview/', views.dashboard_overview, name='dashboard_overview'),
    path('view-qr/', views.view_qr_code, name='view_qr_code'),
    path('qr/scan/', views.qr_pay_redirect, name='qr_pay_redirect'),
    path('send-money/', views.send_money, name='send_money'),
    path('request-money/', views.request_money, name='request_money'),
    path('requests/<int:request_id>/decline/', views.decline_money_request, name='decline_money_request'),
    path('link-bank/<slug:bank_slug>/', views.link_bank_verify, name='link_bank_verify'),
    path('link-bank/<slug:bank_slug>/details/', views.link_bank_details, name='link_bank_details'),
    path('link-bank/<slug:bank_slug>/set-upi/', views.set_upi_pin, name='set_upi_pin'),
    path('send-bank-verification-otp/', views.send_bank_verification_otp, name='send_bank_verification_otp'),
    path('verify-bank-verification-otp/', views.verify_bank_verification_otp, name='verify_bank_verification_otp'),
]
