from django.urls import path

from .views import (
    RegisterView,
    PhoneOTPRequestView,PhoneOTPVerifyView,CurrentUserView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),

    path(
        'phone/request-otp/',
        PhoneOTPRequestView.as_view(),
        name='phone-request-otp'
    ),
    path(
        'phone/verify-otp/',
        PhoneOTPVerifyView.as_view(),
        name='phone-verify-otp'
    ),
    path('me/', CurrentUserView.as_view(), name='current-user'),
]