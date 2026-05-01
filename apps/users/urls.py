from django.urls import path
from .views import (
    ApproveUserView,
    ChangePasswordView,
    MeView,
    MidwifeMothersView,
    PendingUsersView,
    RegisterView,
    ResendOTPView,
    UserListView,
    VerifyOTPView,
)

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("pending/", PendingUsersView.as_view(), name="pending"),
    path("approve/", ApproveUserView.as_view(), name="approve"),
    path("mothers/", MidwifeMothersView.as_view(), name="mothers"),
    path("", UserListView.as_view(), name="list"),
]
