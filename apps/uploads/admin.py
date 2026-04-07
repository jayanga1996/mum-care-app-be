from django.contrib import admin
from .models import FileUpload


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "file_type", "user", "file_size_bytes", "uploaded_at"]
    list_filter = ["file_type"]
    search_fields = ["original_filename", "user__email"]
    readonly_fields = ["uploaded_at", "file_size_bytes", "original_filename"]
