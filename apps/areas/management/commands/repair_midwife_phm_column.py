"""
Fix schema drift: django_migrations says 0005 applied but `midwife_schedules.phm_area_id` is missing.

Usage on Ubuntu/MySQL:
  python manage.py repair_midwife_phm_column
"""
from django.core.management.base import BaseCommand
from django.db import connection


TABLE = "midwife_schedules"
COLUMN = "phm_area_id"


class Command(BaseCommand):
    help = "Add midwife_schedules.phm_area_id + FK if missing (MySQL/MariaDB)."

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped: connection vendor is {connection.vendor!r} (this repair is for MySQL/MariaDB)."
                )
            )
            return

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
                  AND COLUMN_NAME = %s
                """,
                [TABLE, COLUMN],
            )
            if cursor.fetchone()[0] > 0:
                self.stdout.write(self.style.SUCCESS(f"OK: `{TABLE}.{COLUMN}` already exists."))
                return

        self.stdout.write(self.style.WARNING(f"Adding missing `{TABLE}.{COLUMN}` ..."))

        sql_add_col = f"""
            ALTER TABLE `{TABLE}`
            ADD COLUMN `{COLUMN}` BIGINT NULL
        """

        # PROTECT -> RESTRICT in MySQL FK syntax
        sql_fk = f"""
            ALTER TABLE `{TABLE}`
            ADD CONSTRAINT `midwife_schedules_phm_area_id_fk`
            FOREIGN KEY (`{COLUMN}`) REFERENCES `phm_areas` (`id`)
            ON DELETE RESTRICT
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_add_col)
            try:
                cursor.execute(sql_fk)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FK step failed (column may exist): {e}"))
                raise

        self.stdout.write(
            self.style.SUCCESS(
                "Column + foreign key added. Run: python manage.py migrate (should no-op) "
                "then restart gunicorn."
            )
        )
