"""
Fix schema drift: django_migrations says migrations applied but `midwife_schedules.phm_area_id`
or its FK is missing (common when FK failed on MyISAM).

Usage on Ubuntu/MySQL:
  python manage.py repair_midwife_phm_column
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError


TABLE = "midwife_schedules"
COLUMN = "phm_area_id"


def _mysql_errno(exc: OperationalError):
    args = getattr(exc, "args", ())
    if not args:
        return None
    first = args[0]
    if isinstance(first, int):
        return first
    if isinstance(first, tuple) and first and isinstance(first[0], int):
        return first[0]
    return None


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

            def column_exists() -> bool:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = %s
                      AND COLUMN_NAME = %s
                    """,
                    [TABLE, COLUMN],
                )
                return cursor.fetchone()[0] > 0

            def fk_exists() -> bool:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = %s
                      AND COLUMN_NAME = %s
                      AND REFERENCED_TABLE_NAME = 'phm_areas'
                    """,
                    [TABLE, COLUMN],
                )
                return cursor.fetchone()[0] > 0

            def table_engine():
                cursor.execute(
                    """
                    SELECT ENGINE FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = %s
                    """,
                    [TABLE],
                )
                row = cursor.fetchone()
                return row[0] if row else None

            eng = (table_engine() or "").upper()
            if eng and eng != "INNODB":
                self.stdout.write(
                    self.style.WARNING(f"Converting `{TABLE}` to InnoDB (required for foreign keys) ...")
                )
                cursor.execute(f"ALTER TABLE `{TABLE}` ENGINE=InnoDB")

            if not column_exists():
                self.stdout.write(self.style.WARNING(f"Adding missing `{TABLE}.{COLUMN}` ..."))
                try:
                    cursor.execute(
                        f"""
                        ALTER TABLE `{TABLE}`
                        ADD COLUMN `{COLUMN}` BIGINT NULL
                        """
                    )
                except OperationalError as e:
                    if _mysql_errno(e) != 1060 and "duplicate column" not in str(e).lower():
                        raise
                    self.stdout.write(self.style.SUCCESS(f"Column already present (race or partial apply)."))

            if column_exists() and not fk_exists():
                self.stdout.write(self.style.WARNING("Adding missing foreign key ..."))
                try:
                    cursor.execute(
                        f"""
                        ALTER TABLE `{TABLE}`
                        ADD CONSTRAINT `midwife_schedules_phm_area_id_fk`
                        FOREIGN KEY (`{COLUMN}`) REFERENCES `phm_areas` (`id`)
                        ON DELETE RESTRICT
                        """
                    )
                except OperationalError as e:
                    msg = str(e).lower()
                    if _mysql_errno(e) in (1826, 1022) or "duplicate" in msg or "already exists" in msg:
                        self.stdout.write(self.style.SUCCESS("Foreign key already present."))
                    else:
                        self.stdout.write(self.style.ERROR(f"FK step failed: {e}"))
                        raise

            if column_exists() and fk_exists():
                self.stdout.write(
                    self.style.SUCCESS(
                        "OK: column and FK are present. Run: python manage.py migrate "
                        "then restart the app server."
                    )
                )
            elif column_exists():
                self.stdout.write(self.style.WARNING("Column exists but FK check failed; inspect MySQL errors above."))
