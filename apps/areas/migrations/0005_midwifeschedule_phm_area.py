# Generated manually for PHM-area–scoped schedules

from django.db import migrations, models
import django.db.models.deletion


def link_schedules_to_phm_areas(apps, schema_editor):
    MidwifeSchedule = apps.get_model("areas", "MidwifeSchedule")
    PHMArea = apps.get_model("areas", "PHMArea")
    for s in MidwifeSchedule.objects.all():
        if getattr(s, "phm_area_id", None):
            continue
        loc = (getattr(s, "location", None) or "").strip()
        if not loc:
            continue
        area = PHMArea.objects.filter(name__iexact=loc).first()
        if area:
            s.phm_area_id = area.id
            s.save(update_fields=["phm_area_id"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("areas", "0004_alter_midwifeschedule_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="midwifeschedule",
            name="phm_area",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="schedules",
                to="areas.phmarea",
            ),
        ),
        migrations.RunPython(link_schedules_to_phm_areas, noop_reverse),
    ]
