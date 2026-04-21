from celery import shared_task
from django.core.mail import send_mail
from .models import User
from config.settings import DEFAULT_FROM_EMAIL


@shared_task
def send_otp_email_task(email, code):
    send_mail(
        subject="Your OTP Code",
        message=f"Your OTP is: {code}. It expires in 3 minutes.",
        from_email=DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )

@shared_task
def delete_unverified_user(user_id):
    try:
        user = User.objects.get(id=user_id)

        if not user.is_verified:
            user.delete()

    except User.DoesNotExist:
        pass