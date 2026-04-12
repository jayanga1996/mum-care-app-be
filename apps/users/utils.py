"""
Email utility functions for the users app.
"""
from django.conf import settings
from django.core.mail import send_mail


def send_otp_email(email: str, full_name: str, otp_code: str) -> None:
    """Send a signup OTP verification email to the user."""
    subject = "Your Mum Care App Verification Code"
    message = (
        f"Hi {full_name},\n\n"
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you did not sign up for Mum Care App, please ignore this email.\n\n"
        f"Regards,\nMum Care App Team"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
