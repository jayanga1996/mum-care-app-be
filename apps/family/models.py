"""
Family member registration models.

Maps directly to the 4-step wizard in the React Native app:
  Step 1 – MOH/PHM area + personal info
  Step 2 – DOB, contact, education, marriage date
  Step 3 – Diseases (husband / wife)
  Step 4 – Vitals (weight, height, blood type) + special women info
"""
from django.db import models


class BloodType(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"


class EducationLevel(models.TextChoices):
    NO_FORMAL = "no_formal", "No Formal Education"
    PRIMARY = "primary", "Primary (Grade 1–5)"
    SECONDARY = "secondary", "Secondary (Grade 6–10)"
    OL = "ol", "O/L Passed"
    AL = "al", "A/L Passed"
    DIPLOMA = "diploma", "Diploma"
    BACHELOR = "bachelor", "Bachelor's Degree"
    POSTGRAD = "postgrad", "Master's / Postgraduate"


class Disease(models.Model):
    """Pre-seeded common disease reference list."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "diseases"
        verbose_name = "Disease"
        verbose_name_plural = "Diseases"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class FamilyRegistration(models.Model):
    """
    Complete family registration record submitted by a competent family member.
    Covers all four wizard steps.
    """

    # ── Ownership ─────────────────────────────────────────────────────────────
    submitted_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="family_registrations",
        null=True,
        blank=True,
    )

    # ── Step 1: Location & Personal Info ──────────────────────────────────────
    moh_area = models.ForeignKey(
        "areas.MOHArea",
        on_delete=models.PROTECT,
        related_name="family_registrations",
    )
    phm_area = models.ForeignKey(
        "areas.PHMArea",
        on_delete=models.PROTECT,
        related_name="family_registrations",
    )
    husband_name = models.CharField(max_length=150)
    wife_name = models.CharField(max_length=150)
    address = models.TextField()
    nic_number = models.CharField(max_length=20)

    # ── Step 2: DOB, Contact, Background ──────────────────────────────────────
    husband_dob = models.DateField()
    wife_dob = models.DateField()
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, default="")
    job = models.CharField(max_length=100)
    education_level = models.CharField(
        max_length=20,
        choices=EducationLevel.choices,
        default=EducationLevel.NO_FORMAL,
    )
    marriage_date = models.DateField()

    # ── Step 3: Diseases handled via FamilyDiseaseEntry (FK) ─────────────────

    # ── Step 4: Vitals & Special Info ─────────────────────────────────────────
    women_special_info = models.TextField(blank=True, default="")
    women_weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    women_height_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    men_weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    men_height_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    blood_type = models.CharField(
        max_length=3, choices=BloodType.choices, blank=True, default=""
    )

    # ── Audit ──────────────────────────────────────────────────────────────────
    is_complete = models.BooleanField(default=False)
    current_step = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "family_registrations"
        verbose_name = "Family Registration"
        verbose_name_plural = "Family Registrations"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.husband_name} & {self.wife_name} ({self.phm_area})"

    def mark_complete(self) -> None:
        """Mark registration as fully completed after step 4."""
        self.is_complete = True
        self.current_step = 4
        self.save(update_fields=["is_complete", "current_step", "updated_at"])


class PersonChoice(models.TextChoices):
    HUSBAND = "husband", "Husband"
    WIFE = "wife", "Wife"


class FamilyDiseaseEntry(models.Model):
    """
    Association between a family registration and a disease for either
    the husband or the wife.
    """

    registration = models.ForeignKey(
        FamilyRegistration,
        on_delete=models.CASCADE,
        related_name="disease_entries",
    )
    disease = models.ForeignKey(
        Disease,
        on_delete=models.PROTECT,
        related_name="family_entries",
    )
    person = models.CharField(max_length=10, choices=PersonChoice.choices)

    class Meta:
        db_table = "family_disease_entries"
        verbose_name = "Family Disease Entry"
        verbose_name_plural = "Family Disease Entries"
        unique_together = [("registration", "disease", "person")]

    def __str__(self) -> str:
        return f"{self.person}: {self.disease.name} ({self.registration})"
