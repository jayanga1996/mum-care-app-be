"""
Custom User model with role-based access for the Mum Care App.
OOP: AbstractBaseUser + PermissionsMixin for full customisation.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    """Enumeration of all user roles in the system."""
    MOTHER = "mother", "Mother"
    MIDWIFE = "midwife", "Midwife"
    SISTER = "sister", "Public Health Nursing Sister"
    FAMILY = "family", "Family Member"


class UserManager(BaseUserManager):
    """Custom manager for the User model."""

    def _create_user(self, email: str, password: str, **extra_fields) -> "User":
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str = None, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_approved", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user model.

    All four roles (mother, midwife, sister, family) share this table.
    Role-specific profile data lives in separate models.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.MOTHER)

    # Approval workflow
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_users",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Area assignment (nullable – only relevant for mother/midwife)
    phm_area = models.ForeignKey(
        "areas.PHMArea",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    # Django auth fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.role})"

    @property
    def assigned_midwife(self) -> "User | None":
        """Return the midwife assigned to this user's PHM area (for mothers)."""
        if self.phm_area:
            return self.phm_area.assigned_midwife
        return None
