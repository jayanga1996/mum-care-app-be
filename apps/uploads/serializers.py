"""Uploads serializers."""
from typing import Optional

from rest_framework import serializers
from .models import FileUpload


class FileUploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FileUpload
        fields = [
            "id", "file", "file_url",
            "original_filename", "file_type",
            "file_size_bytes", "family_registration",
            "uploaded_at",
        ]
        read_only_fields = [
            "id", "file_url", "original_filename",
            "file_size_bytes", "uploaded_at",
        ]

    def get_file_url(self, obj: FileUpload) -> Optional[str]:
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def create(self, validated_data: dict) -> FileUpload:
        file = validated_data.get("file")
        if file:
            validated_data["original_filename"] = file.name
            validated_data["file_size_bytes"] = file.size
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
