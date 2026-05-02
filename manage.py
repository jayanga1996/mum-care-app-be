#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    # Local dev: defaults to development (SQLite). Production (Gunicorn) uses
    # config.settings.production via wsgi. SSH shells often omit DJANGO_SETTINGS_MODULE,
    # so migrate would touch SQLite while the app serves MySQL — set either:
    #   export DJANGO_SETTINGS_MODULE=config.settings.production
    #   export DJANGO_USE_PRODUCTION_SETTINGS=1
    if "DJANGO_SETTINGS_MODULE" not in os.environ:
        use_prod = os.environ.get("DJANGO_USE_PRODUCTION_SETTINGS", "").lower() in (
            "1",
            "true",
            "yes",
        )
        os.environ["DJANGO_SETTINGS_MODULE"] = (
            "config.settings.production" if use_prod else "config.settings.development"
        )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Activate your virtual environment first."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
