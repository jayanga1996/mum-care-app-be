"""
MySQL/MariaDB DDL to add MidwifeSchedule response fields when migrations drift.

Used by migration 0012 and management command repair_schedule_response_columns.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


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


def _resolve_table_name(cursor, logical_name: str) -> Optional[str]:
    cursor.execute(
        """
        SELECT TABLE_NAME FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND LOWER(TABLE_NAME) = LOWER(%s)
        """,
        [logical_name],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _has_column(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        [table, column],
    )
    return cursor.fetchone()[0] > 0


def _users_id_column_type(cursor, users_table: str) -> str:
    cursor.execute(
        """
        SELECT COLUMN_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = 'id'
        """,
        [users_table],
    )
    row = cursor.fetchone()
    if row and row[0]:
        return row[0]
    return "CHAR(32)"


def _fk_cancelled_by_exists(cursor, schedule_table: str, users_table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = 'cancelled_by_id'
          AND REFERENCED_TABLE_NAME = %s
        """,
        [schedule_table, users_table],
    )
    return cursor.fetchone()[0] > 0


def ensure_midwife_schedule_response_columns(
    connection, log: Optional[Callable[[str], None]] = None
) -> List[str]:
    """
    Idempotent ALTER TABLE for midwife_schedules response_* columns + FK.
    Returns human-readable log lines (also passed to log(line) if provided).
    """
    lines: List[str] = []

    def out(msg: str) -> None:
        lines.append(msg)
        if log:
            log(msg)
        else:
            logger.info(msg)

    if connection.vendor != "mysql":
        out("Skipped: not MySQL/MariaDB.")
        return lines

    with connection.cursor() as cursor:
        sched = _resolve_table_name(cursor, "midwife_schedules")
        users_tbl = _resolve_table_name(cursor, "users")
        if not sched:
            out("ERROR: table midwife_schedules not found in this database.")
            return lines
        if not users_tbl:
            out("ERROR: table users not found in this database.")
            return lines

        out(f"Using tables: `{sched}`, `{users_tbl}`.")

        def add_col_safe(sql: str, label: str) -> None:
            try:
                cursor.execute(sql)
                out(f"OK: {label}")
            except OperationalError as e:
                if _mysql_errno(e) == 1060 or "duplicate column" in str(e).lower():
                    out(f"Skip (already exists): {label}")
                else:
                    out(f"FAILED {label}: {e}")
                    raise

        if not _has_column(cursor, sched, "response_status"):
            add_col_safe(
                f"""
                ALTER TABLE `{sched}`
                ADD COLUMN `response_status` VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                """,
                "add response_status",
            )

        for col in ("confirmed_at", "cancelled_at"):
            if not _has_column(cursor, sched, col):
                ddl_opts = ("DATETIME(6) NULL", "DATETIME NULL")
                last_err: Optional[Exception] = None
                for ddl in ddl_opts:
                    try:
                        cursor.execute(
                            f"ALTER TABLE `{sched}` ADD COLUMN `{col}` {ddl}"
                        )
                        out(f"OK: add {col} ({ddl})")
                        last_err = None
                        break
                    except OperationalError as e:
                        if _mysql_errno(e) == 1060 or "duplicate column" in str(e).lower():
                            out(f"Skip (already exists): {col}")
                            last_err = None
                            break
                        last_err = e
                if last_err is not None:
                    raise last_err

        if not _has_column(cursor, sched, "cancellation_reason"):
            add_col_safe(
                f"""
                ALTER TABLE `{sched}`
                ADD COLUMN `cancellation_reason` VARCHAR(500) NOT NULL DEFAULT ''
                """,
                "add cancellation_reason",
            )

        id_type = _users_id_column_type(cursor, users_tbl)
        out(f"users.id column type: {id_type}")

        if not _has_column(cursor, sched, "cancelled_by_id"):
            add_col_safe(
                f"ALTER TABLE `{sched}` ADD COLUMN `cancelled_by_id` {id_type} NULL",
                "add cancelled_by_id",
            )

        if _has_column(cursor, sched, "cancelled_by_id") and not _fk_cancelled_by_exists(
            cursor, sched, users_tbl
        ):
            try:
                cursor.execute(
                    f"""
                    ALTER TABLE `{sched}`
                    ADD CONSTRAINT `midwife_schedules_cancelled_by_id_fk`
                    FOREIGN KEY (`cancelled_by_id`) REFERENCES `{users_tbl}` (`id`)
                    ON DELETE SET NULL
                    """
                )
                out("OK: add FK cancelled_by -> users.id")
            except OperationalError as e:
                msg = str(e).lower()
                if _mysql_errno(e) in (1826, 1022) or "duplicate" in msg or "already exists" in msg:
                    out("Skip FK (duplicate or exists).")
                else:
                    out(
                        f"WARNING: could not add FK (app may still work): {e}. "
                        "If needed, add the constraint manually in MySQL."
                    )

    return lines
