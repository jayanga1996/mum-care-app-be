"""
User serializers.
OOP: Composed of nested serializers & custom validation methods.
"""
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from apps.areas.serializers import PHMAreaSerializer
from .models import User, UserRole


class UserPublicSerializer(serializers.ModelSerializer):
    """Read-only public profile (no sensitive fields)."""

    class Meta:
        model = User
        fields = ["id", "full_name", "role", "is_approved", "created_at"]
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    """Full user detail including area info."""

    phm_area = PHMAreaSerializer(read_only=True)
    assigned_midwife_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role",
            "is_approved", "approved_at",
            "phm_area", "assigned_midwife_name",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_assigned_midwife_name(self, obj: User) -> str | None:
        midwife = obj.assigned_midwife
        return midwife.full_name if midwife else None


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
