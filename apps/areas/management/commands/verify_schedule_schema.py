"""
Verify schedule-related tables exist (after areas migrations 0013–0014).

  python manage.py verify_schedule_schema

Exit code 1 if the responses table is missing (run migrate on this DB).
"""
import sys

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Check midwife_schedules + midwife_schedule_responses exist."

    def handle(self, *args, **options):
        cursor = connection.cursor()
        names = connection.introspection.table_names(cursor)
        lower = {n.lower() for n in names}

        need = ("midwife_schedules", "midwife_schedule_responses")
        missing = [t for t in need if t not in lower]

        self.stdout.write(f"Database vendor: {connection.vendor}")
        self.stdout.write(f"Looking for tables: {need}")

        if connection.vendor == "sqlite":
            self.stdout.write(
                self.style.WARNING(
                    "Using SQLite (development settings). Gunicorn uses production/MySQL — "
                    "migrate with the same DB as the app: "
                    "DJANGO_SETTINGS_MODULE=config.settings.production python manage.py migrate areas "
                    "or export DJANGO_USE_PRODUCTION_SETTINGS=1."
                )
            )

        if missing:
            self.stdout.write(self.style.ERROR(f"MISSING: {missing}"))
            self.stdout.write(
                "Run: python manage.py migrate areas\n"
                "Ensure this uses the same DATABASE config as your running app."
            )
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS("OK — schedule tables present."))
