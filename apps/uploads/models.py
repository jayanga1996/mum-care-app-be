"""
File upload model – files are stored in AWS S3 in production.
"""
import uuid

from django.db import models


def upload_path(instance: "FileUpload", filename: str) -> str:
    """Build a structured S3/local path: uploads/<role>/<user_id>/<uuid>/<filename>"""
    return f"uploads/{instance.user.role}/{instance.user.id}/{instance.id}/{filename}"


class FileType(models.TextChoices):
    PHOTO = "photo", "Photo"
    DOCUMENT = "document", "Document"
    REPORT = "report", "Medical Report"
    OTHER = "other", "Other"


class FileUpload(models.Model):
    """Represents a file uploaded by any user, stored in S3."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="uploads",
    )
    # Related registration (optional – links photo/document to a family record)
    family_registration = models.ForeignKey(
        "family.FamilyRegistration",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploads",
    )
    file = models.FileField(upload_to=upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(
        max_length=10, choices=FileType.choices, default=FileType.OTHER
    )
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "file_uploads"
        verbose_name = "File Upload"
        verbose_name_plural = "File Uploads"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.file_type}: {self.original_filename} by {self.user}"

    def save(self, *args, **kwargs) -> None:
        """Persist original filename before saving."""
        if self.file and not self.original_filename:
            self.original_filename = self.file.name.split("/")[-1]
        super().save(*args, **kwargs)
