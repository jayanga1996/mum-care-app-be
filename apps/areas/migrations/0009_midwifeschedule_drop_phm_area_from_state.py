"""
Stop ORM use of midwife_schedules.phm_area_id.

Production MySQL sometimes never received this column (migration drift). Midwife flows already
store the PHM context in `location` (PHM area name). Removing the FK from Django's model state
only — no ALTER TABLE — avoids touching a broken/missing column while keeping behaviour via
`location__iexact` filtering.

Any existing phm_area_id column in the DB is left unused (nullable orphan).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("areas", "0008_ensure_phm_area_column_mysql"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="midwifeschedule",
                    name="phm_area",
                ),
            ],
            database_operations=[],
        ),
    ]
