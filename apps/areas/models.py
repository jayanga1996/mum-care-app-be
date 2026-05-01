"""
Area models: MOH (Medical Officer of Health) and PHM (Public Health Midwife) areas.
"""
from django.db import models


class MOHArea(models.Model):
    """
    Ministry of Health administrative area.
    A MOH area contains one or more PHM areas.
    """

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "moh_areas"
        verbose_name = "MOH Area"
        verbose_name_plural = "MOH Areas"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PHMArea(models.Model):
    """
    Public Health Midwife area – a sub-division of a MOH area.
    Each PHM area is managed by one assigned midwife.
    """

    name = models.CharField(max_length=100, unique=True)
    moh_area = models.ForeignKey(
        MOHArea,
        on_delete=models.CASCADE,
        related_name="phm_areas",
    )
    # assigned_midwife is set after midwife accounts are created
    assigned_midwife = models.OneToOneField(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_area",
        limit_choices_to={"role": "midwife"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phm_areas"
        verbose_name = "PHM Area"
        verbose_name_plural = "PHM Areas"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.moh_area.name})"


# --- Midwife Schedule Model ---
class MidwifeSchedule(models.Model):
    SCHEDULE_TYPE_CHOICES = [
        ("Clinic", "Clinic"),
        ("Home Visit", "Home Visit"),
    ]
    midwife = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="midwife_schedules",
        limit_choices_to={"role": "midwife"},
    )
    type = models.CharField(max_length=50, choices=SCHEDULE_TYPE_CHOICES)
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "midwife_schedules"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.midwife} - {self.type} on {self.date} at {self.time} in {self.location}"
