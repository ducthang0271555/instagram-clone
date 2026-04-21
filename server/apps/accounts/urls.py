from django.urls import path
from .views import RegisterView, VerifyOTPView, SendOTPView

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('verify_otp/', VerifyOTPView.as_view()),
    path('send_otp/', SendOTPView.as_view()),
]