"""
User serializers.
OOP: Composed of nested serializers & custom validation methods.
"""
from typing import Optional

from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from apps.areas.serializers import PHMAreaSerializer
from .models import OTPVerification, User, UserRole


class UserPublicSerializer(serializers.ModelSerializer):
    """Read-only public profile (no sensitive fields)."""

    class Meta:
        model = User
        fields = ["id", "full_name", "role", "is_approved", "created_at"]
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    """Full user detail including area info."""

    phm_area = PHMAreaSerializer(read_only=True)
    # PHM area this midwife manages (reverse of PHMArea.assigned_midwife), when set.
    managed_phm_area = serializers.SerializerMethodField()
    assigned_midwife_name = serializers.SerializerMethodField()
    # Plain string for clients that do not rely on nested phm_area (more resilient).
    phm_area_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role",
            "is_approved", "approved_at",
            "phm_area", "phm_area_name", "managed_phm_area", "assigned_midwife_name",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_managed_phm_area(self, obj: User) -> Optional[dict]:
        ma = getattr(obj, "managed_area", None)
        if ma is None:
            return None
        try:
            return PHMAreaSerializer(ma).data
        except Exception:
            return None

    def get_assigned_midwife_name(self, obj: User) -> Optional[str]:
        midwife = obj.assigned_midwife
        return midwife.full_name if midwife else None

    def get_phm_area_name(self, obj: User) -> Optional[str]:
        pa = getattr(obj, "phm_area", None)
        if pa is None:
            return None
        try:
            return pa.name
        except Exception:
            return None


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles new user registration.
    Validates passwords and creates User via the custom manager.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    phm_area_id = serializers.PrimaryKeyRelatedField(
        source="phm_area",
        queryset=__import__("apps.areas.models", fromlist=["PHMArea"]).PHMArea.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            "email", "full_name", "role",
            "password", "password_confirm",
            "phm_area_id",
        ]

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        role = attrs.get("role")
        if role not in [r.value for r in UserRole]:
            raise serializers.ValidationError({"role": f"Invalid role: {role}"})
        return attrs

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ApproveUserSerializer(serializers.Serializer):
    """Used by midwife/sister to approve a pending user."""

    user_id = serializers.UUIDField()

    def validate_user_id(self, value):
        try:
            return User.objects.get(id=value, is_approved=False)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found or already approved.")

    def save(self, approved_by: User, **kwargs) -> User:
        user: User = self.validated_data["user_id"]
        user.is_approved = True
        user.approved_by = approved_by
        user.approved_at = timezone.now()
        user.save(update_fields=["is_approved", "approved_by", "approved_at"])
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value: str) -> str:
        user: User = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs) -> None:
        user: User = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])


class VerifyOTPSerializer(serializers.Serializer):
    """Verify the OTP code submitted during signup."""

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"]
        code = attrs["code"]

        try:
            user = User.objects.get(email=email, is_active=False)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"email": "No pending verification account found for this email."}
            )

        try:
            otp = user.otp_verification
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError({"code": "No OTP found. Please request a new one."})

        if not otp.is_valid():
            raise serializers.ValidationError({"code": "OTP has expired. Please request a new one."})

        if otp.code != code:
            raise serializers.ValidationError({"code": "Invalid OTP code."})

        attrs["user"] = user
        return attrs

    def save(self, **kwargs) -> User:
        user: User = self.validated_data["user"]
        user.is_active = True
        user.save(update_fields=["is_active"])
        user.otp_verification.delete()
        return user


class ResendOTPSerializer(serializers.Serializer):
    """Resend an OTP to a user whose account is still pending verification."""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        try:
            user = User.objects.get(email=value, is_active=False)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No pending verification account found for this email."
            )
        self.user = user
        return value

    def save(self, **kwargs) -> User:
        return self.user
