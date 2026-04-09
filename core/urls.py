from django.urls import path
from . import views

urlpatterns = [
    path('', views.home),
    path('signup/', views.signup),
    path('login/', views.login_view),
    path('logout/', views.logout_view),
    path('about/', views.about, name='about'),
    path('faq/', views.faq, name='faq'),
    path('contact/', views.contact, name='contact'),
    path('myaccount/', views.myaccount, name='myaccount'),
    path('send-otp/', views.send_otp),
    path('verify-otp/', views.verify_otp),
]
