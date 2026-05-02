"""
Manual repair when `response_status` (or related columns) is missing on MySQL.

  python manage.py repair_schedule_response_columns

Uses the same DDL as migration 0012. Safe to run multiple times.
"""
from django.core.management.base import BaseCommand
from django.db import connection

from apps.areas.schema_repair_schedule import ensure_midwife_schedule_response_columns


class Command(BaseCommand):
    help = "Add midwife_schedules response_status + related columns on MySQL if missing."

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped: DB vendor is {connection.vendor!r} (this command is for MySQL/MariaDB)."
                )
            )
            return

        def log(msg: str) -> None:
            self.stdout.write(msg)

        lines = ensure_midwife_schedule_response_columns(connection, log=log)
        if not lines:
            self.stdout.write(self.style.WARNING("No actions logged."))
            return
        if any(line.startswith("ERROR:") for line in lines):
            self.stdout.write(self.style.ERROR("Repair finished with errors — check output above."))
        else:
            self.stdout.write(
                self.style.SUCCESS("Done. Restart the app server, then re-try the API.")
            )
