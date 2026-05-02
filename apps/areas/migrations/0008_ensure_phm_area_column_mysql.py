"""
Retry phm_area_id repair for MySQL/MariaDB when 0007 left the DB inconsistent (e.g. FK failed on MyISAM).

Safe to run multiple times (checks information_schema before each DDL step).
"""

from typing import Optional

from django.db import migrations
from django.db.utils import OperationalError


def _mysql_errno(exc: OperationalError) -> Optional[int]:
    args = getattr(exc, "args", ())
    if not args:
        return None
    first = args[0]
    if isinstance(first, int):
        return first
    # mysqlclient sometimes passes (errno, message)
    if isinstance(first, tuple) and first and isinstance(first[0], int):
        return first[0]
    return None


def _robust_add_phm_area_fk(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "mysql":
        return

    with conn.cursor() as cursor:

        def column_exists() -> bool:
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'midwife_schedules'
                  AND COLUMN_NAME = 'phm_area_id'
                """
            )
            return cursor.fetchone()[0] > 0

        def fk_exists() -> bool:
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'midwife_schedules'
                  AND COLUMN_NAME = 'phm_area_id'
                  AND REFERENCED_TABLE_NAME = 'phm_areas'
                """
            )
            return cursor.fetchone()[0] > 0

        def table_engine() -> Optional[str]:
            cursor.execute(
                """
                SELECT ENGINE FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'midwife_schedules'
                """
            )
            row = cursor.fetchone()
            return row[0] if row else None

        eng = (table_engine() or "").upper()
        if eng and eng != "INNODB":
            cursor.execute("ALTER TABLE `midwife_schedules` ENGINE=InnoDB")

        if not column_exists():
            try:
                cursor.execute(
                    """
                    ALTER TABLE `midwife_schedules`
                    ADD COLUMN `phm_area_id` BIGINT NULL
                    """
                )
            except OperationalError as e:
                # 1060: Duplicate column name
                if _mysql_errno(e) != 1060 and "duplicate column" not in str(e).lower():
                    raise

        if column_exists() and not fk_exists():
            try:
                cursor.execute(
                    """
                    ALTER TABLE `midwife_schedules`
                    ADD CONSTRAINT `midwife_schedules_phm_area_id_fk`
                    FOREIGN KEY (`phm_area_id`) REFERENCES `phm_areas` (`id`)
                    ON DELETE RESTRICT
                    """
                )
            except OperationalError as e:
                msg = str(e).lower()
                if _mysql_errno(e) in (1826, 1022) or "duplicate" in msg or "already exists" in msg:
                    return
                raise


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("areas", "0007_ensure_midwife_schedules_phm_area_column"),
    ]

    atomic = False  # MySQL DDL often implicit-commit

    operations = [
        migrations.RunPython(_robust_add_phm_area_fk, noop_reverse),
    ]
