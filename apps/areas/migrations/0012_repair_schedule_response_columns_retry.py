"""
Re-run response-column repair with improved table/column type detection (v2).

If 0011 already applied but columns are still missing (failed DDL, wrong types, or
table name casing), this migration runs the same logic as `repair_schedule_response_columns`.
"""

from django.db import migrations

from apps.areas.schema_repair_schedule import ensure_midwife_schedule_response_columns


def forward(apps, schema_editor):
    ensure_midwife_schedule_response_columns(schema_editor.connection)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("areas", "0011_ensure_midwife_schedule_response_columns_mysql"),
    ]

    atomic = False

    operations = [
        migrations.RunPython(forward, noop_reverse),
    ]
