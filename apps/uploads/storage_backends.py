"""
Custom S3 storage backends for media and static files.
Used exclusively in production (config/settings/production.py).
"""
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """Stores static files under the 'static/' prefix in S3."""

    location = "static"
    default_acl = None


class MediaStorage(S3Boto3Storage):
    """Stores user-uploaded media files under the 'media/' prefix in S3."""

    location = "media"
    default_acl = None
    file_overwrite = False
