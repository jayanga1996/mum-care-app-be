# Data migration: link PHMArea.assigned_midwife when only User.phm_area was set for midwives.

from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model("users", "User")
    PHMArea = apps.get_model("areas", "PHMArea")

    for area in PHMArea.objects.filter(assigned_midwife__isnull=True):
        mids = list(User.objects.filter(role="midwife", phm_area_id=area.id))
        if len(mids) == 1:
            area.assigned_midwife_id = mids[0].id
            area.save(update_fields=["assigned_midwife_id"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("areas", "0005_midwifeschedule_phm_area"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
