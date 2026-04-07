from django.urls import path
from .views import (
    ApproveUserView,
    ChangePasswordView,
    MeView,
    PendingUsersView,
    RegisterView,
    UserListView,
)

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("pending/", PendingUsersView.as_view(), name="pending"),
    path("approve/", ApproveUserView.as_view(), name="approve"),
    path("", UserListView.as_view(), name="list"),
]
