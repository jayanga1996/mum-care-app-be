"""
User views.
OOP: class-based views using DRF GenericAPIView / ViewSet.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, UserRole
from .serializers import (
    ApproveUserSerializer,
    ChangePasswordSerializer,
    RegisterSerializer,
    UserDetailSerializer,
    UserPublicSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/users/register/
    Open endpoint – anyone can register.
    Family member registrations skip the approval workflow.
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user: User = serializer.save()

        # Family members are auto-approved (no midwife/sister approval needed)
        if user.role == UserRole.FAMILY:
            user.is_approved = True
            user.save(update_fields=["is_approved"])

        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/me/   – retrieve own profile
    PATCH /api/users/me/  – update own profile (name, area)
    """

    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> User:
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """POST /api/users/change-password/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed successfully."})


class PendingUsersView(generics.ListAPIView):
    """
    GET /api/users/pending/
    Returns users pending approval.
    Midwives see pending mothers in their area.
    Sisters see pending midwives.
    """

    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user: User = self.request.user
        if user.role == UserRole.MIDWIFE:
            return User.objects.filter(
                role=UserRole.MOTHER,
                is_approved=False,
                phm_area=user.phm_area,
            )
        if user.role == UserRole.SISTER:
            return User.objects.filter(role=UserRole.MIDWIFE, is_approved=False)
        return User.objects.none()


class ApproveUserView(APIView):
    """POST /api/users/approve/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user: User = request.user
        if user.role not in [UserRole.MIDWIFE, UserRole.SISTER]:
            return Response(
                {"detail": "Only midwives and sisters can approve users."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ApproveUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approved_user = serializer.save(approved_by=user)
        return Response(UserDetailSerializer(approved_user).data)


class UserListView(generics.ListAPIView):
    """
    GET /api/users/
    Sister only: list all users with optional ?role= filter.
    """

    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["role", "is_approved", "phm_area"]
    search_fields = ["full_name", "email"]

    def get_queryset(self):
        user: User = self.request.user
        if user.role == UserRole.SISTER:
            return User.objects.select_related("phm_area", "approved_by").all()
        if user.role == UserRole.MIDWIFE:
            return User.objects.filter(phm_area=user.phm_area)
        return User.objects.none()
