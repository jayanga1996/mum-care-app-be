"""Uploads views – handles S3 file upload/download."""
from rest_framework import generics, permissions, parsers
from .models import FileUpload
from .serializers import FileUploadSerializer


class FileUploadCreateView(generics.CreateAPIView):
    """
    POST /api/uploads/
    Accepts multipart/form-data.
    Files are stored in AWS S3 in production via django-storages.
    """

    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class FileUploadListView(generics.ListAPIView):
    """GET /api/uploads/ – list own uploads (or all for staff)."""

    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["file_type", "family_registration"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return FileUpload.objects.select_related("user").all()
        return FileUpload.objects.filter(user=user)


class FileUploadDetailView(generics.RetrieveDestroyAPIView):
    """GET / DELETE /api/uploads/<pk>/"""

    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return FileUpload.objects.all()
        return FileUpload.objects.filter(user=user)
