"""
Repair schema drift: django_migrations may list 0005 as applied while MySQL never received
`midwife_schedules.phm_area_id`. This migration adds the column + FK only when missing.
"""

from django.db import migrations


def ensure_phm_area_column(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "mysql":
        return

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'midwife_schedules'
              AND COLUMN_NAME = 'phm_area_id'
            """
        )
        if cursor.fetchone()[0] > 0:
            return

    # Match areas.0005_midwifeschedule_phm_area (PROTECT → RESTRICT in MySQL FK syntax)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE `midwife_schedules`
            ADD COLUMN `phm_area_id` BIGINT NULL
            """
        )
        cursor.execute(
            """
            ALTER TABLE `midwife_schedules`
            ADD CONSTRAINT `midwife_schedules_phm_area_id_fk`
            FOREIGN KEY (`phm_area_id`) REFERENCES `phm_areas` (`id`)
            ON DELETE RESTRICT
            """
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("areas", "0006_sync_phm_assigned_midwife"),
    ]

    operations = [
        migrations.RunPython(ensure_phm_area_column, noop_reverse),
    ]
