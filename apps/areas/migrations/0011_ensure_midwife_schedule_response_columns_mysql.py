"""
Repair MySQL/MariaDB when django_migrations lists 0010 applied but DDL for response fields did not run.

Adds response_status, timestamps, cancellation_reason, cancelled_by_id + FK when missing.
Safe to run multiple times (information_schema checks).
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
    if isinstance(first, tuple) and first and isinstance(first[0], int):
        return first[0]
    return None


def _has_column(cursor, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'midwife_schedules'
          AND COLUMN_NAME = %s
        """,
        [column],
    )
    return cursor.fetchone()[0] > 0


def _fk_cancelled_by_exists(cursor) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'midwife_schedules'
          AND COLUMN_NAME = 'cancelled_by_id'
          AND REFERENCED_TABLE_NAME = 'users'
        """
    )
    return cursor.fetchone()[0] > 0


def _ensure_response_columns(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "mysql":
        return

    with conn.cursor() as cursor:
        if not _has_column(cursor, "response_status"):
            try:
                cursor.execute(
                    """
                    ALTER TABLE `midwife_schedules`
                    ADD COLUMN `response_status` VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                    """
                )
            except OperationalError as e:
                if _mysql_errno(e) != 1060 and "duplicate column" not in str(e).lower():
                    raise

        for col, ddl in (
            ("confirmed_at", "DATETIME(6) NULL"),
            ("cancelled_at", "DATETIME(6) NULL"),
        ):
            if not _has_column(cursor, col):
                try:
                    cursor.execute(
                        f"ALTER TABLE `midwife_schedules` ADD COLUMN `{col}` {ddl}"
                    )
                except OperationalError as e:
                    if _mysql_errno(e) != 1060 and "duplicate column" not in str(e).lower():
                        raise

        if not _has_column(cursor, "cancellation_reason"):
            try:
                cursor.execute(
                    """
                    ALTER TABLE `midwife_schedules`
                    ADD COLUMN `cancellation_reason` VARCHAR(500) NOT NULL DEFAULT ''
                    """
                )
            except OperationalError as e:
                if _mysql_errno(e) != 1060 and "duplicate column" not in str(e).lower():
                    raise

        if not _has_column(cursor, "cancelled_by_id"):
            try:
                cursor.execute(
                    """
                    ALTER TABLE `midwife_schedules`
                    ADD COLUMN `cancelled_by_id` CHAR(32) NULL
                    """
                )
            except OperationalError as e:
                if _mysql_errno(e) != 1060 and "duplicate column" not in str(e).lower():
                    raise

        if _has_column(cursor, "cancelled_by_id") and not _fk_cancelled_by_exists(cursor):
            try:
                cursor.execute(
                    """
                    ALTER TABLE `midwife_schedules`
                    ADD CONSTRAINT `midwife_schedules_cancelled_by_id_fk`
                    FOREIGN KEY (`cancelled_by_id`) REFERENCES `users` (`id`)
                    ON DELETE SET NULL
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
        ("areas", "0010_midwifeschedule_response_status"),
    ]

    atomic = False

    operations = [
        migrations.RunPython(_ensure_response_columns, noop_reverse),
    ]
