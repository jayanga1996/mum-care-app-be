"""
Remove leftover physical columns on midwife_schedules after 0013 state-only removal.

Until dropped, INSERTs omit those columns and SQLite/MySQL raise NOT NULL violations.
"""

from django.db import migrations


def _mysql_drop_if_exists(cursor, table: str):
    cursor.execute(
        """
        SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND CONSTRAINT_TYPE = 'FOREIGN KEY'
          AND CONSTRAINT_NAME = 'midwife_schedules_cancelled_by_id_fk'
        """,
        [table],
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{row[0]}`")

    for col in (
        "cancellation_reason",
        "response_status",
        "confirmed_at",
        "cancelled_at",
        "cancelled_by_id",
    ):
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            """,
            [table, col],
        )
        if cursor.fetchone()[0]:
            cursor.execute(f"ALTER TABLE `{table}` DROP COLUMN `{col}`")


def _sqlite_drop_if_exists(cursor, table: str):
    cursor.execute(f'PRAGMA table_info("{table}")')
    cols = {row[1] for row in cursor.fetchall()}
    drop = [
        c
        for c in (
            "cancellation_reason",
            "response_status",
            "confirmed_at",
            "cancelled_at",
            "cancelled_by_id",
        )
        if c in cols
    ]
    for col in drop:
        try:
            cursor.execute(f'ALTER TABLE "{table}" DROP COLUMN "{col}"')
        except Exception:
            pass


def drop_orphans(apps, schema_editor):
    conn = schema_editor.connection
    vendor = conn.vendor
    with conn.cursor() as cursor:
        if vendor == "mysql":
            cursor.execute(
                """
                SELECT TABLE_NAME FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND LOWER(TABLE_NAME) = 'midwife_schedules'
                """
            )
            row = cursor.fetchone()
            if not row:
                return
            _mysql_drop_if_exists(cursor, row[0])
        elif vendor == "sqlite":
            _sqlite_drop_if_exists(cursor, "midwife_schedules")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("areas", "0013_move_response_to_separate_table"),
    ]

    atomic = False

    operations = [
        migrations.RunPython(drop_orphans, noop_reverse),
    ]
