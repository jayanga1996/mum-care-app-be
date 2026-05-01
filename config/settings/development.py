"""Development settings – DEBUG on, local media storage, relaxed CORS."""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# In development, default to local SQLite so the project runs without MySQL/RDS.
# (Production settings still use MySQL via `base.py`.)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Use local filesystem for uploads during development (no AWS needed)
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
MEDIA_URL = "/media/"
STATIC_URL = "/static/"

# Relaxed CORS in development
CORS_ALLOW_ALL_ORIGINS = True
