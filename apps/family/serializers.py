"""
Family registration serializers.
Step-aware: each step has its own serializer + a combined detail serializer.
OOP: base class + per-step subclasses for clean validation separation.
"""
from rest_framework import serializers

from .models import Disease, FamilyDiseaseEntry, FamilyRegistration, PersonChoice


# ─────────────────────────────────────────────────────────────────────────────
# Disease serializers
# ─────────────────────────────────────────────────────────────────────────────

class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = ["id", "name"]


class FamilyDiseaseEntrySerializer(serializers.ModelSerializer):
    disease_name = serializers.CharField(source="disease.name", read_only=True)

    class Meta:
        model = FamilyDiseaseEntry
        fields = ["id", "disease", "disease_name", "person"]


# ─────────────────────────────────────────────────────────────────────────────
# Step serializers (base → concrete per step)
# ─────────────────────────────────────────────────────────────────────────────

class _BaseRegistrationSerializer(serializers.ModelSerializer):
    """Shared configuration for all step serializers."""

    class Meta:
        model = FamilyRegistration
        fields: list = []


class Step1Serializer(_BaseRegistrationSerializer):
    """Step 1 – MOH/PHM area + personal info."""

    class Meta(_BaseRegistrationSerializer.Meta):
        fields = [
            "moh_area", "phm_area",
            "husband_name", "wife_name",
            "address", "nic_number",
        ]

    def validate_nic_number(self, value: str) -> str:
        value = value.strip().upper()
        if len(value) not in (10, 12):
            raise serializers.ValidationError(
                "NIC must be 10 characters (old) or 12 digits (new)."
            )
        return value


class Step2Serializer(_BaseRegistrationSerializer):
    """Step 2 – DOB, contact, education, marriage date."""

    class Meta(_BaseRegistrationSerializer.Meta):
        fields = [
            "husband_dob", "wife_dob",
            "contact_number", "email",
            "job", "education_level",
            "marriage_date",
        ]

    def validate(self, attrs: dict) -> dict:
        if attrs.get("husband_dob") and attrs.get("marriage_date"):
            if attrs["marriage_date"] <= attrs["husband_dob"]:
                raise serializers.ValidationError(
                    {"marriage_date": "Marriage date must be after husband's date of birth."}
                )
        return attrs


class Step3Serializer(serializers.Serializer):
    """
    Step 3 – Disease entries for husband and wife.
    Accepts lists of disease IDs per person.
    """

    husband_disease_ids = serializers.PrimaryKeyRelatedField(
        queryset=Disease.objects.all(), many=True, required=False
    )
    wife_disease_ids = serializers.PrimaryKeyRelatedField(
        queryset=Disease.objects.all(), many=True, required=False
    )

    def update(self, registration: FamilyRegistration, validated_data: dict) -> FamilyRegistration:
        # Clear existing entries for this registration and recreate
        registration.disease_entries.all().delete()

        entries = []
        for disease in validated_data.get("husband_disease_ids", []):
            entries.append(
                FamilyDiseaseEntry(registration=registration, disease=disease, person=PersonChoice.HUSBAND)
            )
        for disease in validated_data.get("wife_disease_ids", []):
            entries.append(
                FamilyDiseaseEntry(registration=registration, disease=disease, person=PersonChoice.WIFE)
            )
        FamilyDiseaseEntry.objects.bulk_create(entries, ignore_conflicts=True)
        registration.current_step = 3
        registration.save(update_fields=["current_step", "updated_at"])
        return registration


class Step4Serializer(_BaseRegistrationSerializer):
    """Step 4 – Vitals + special women info."""

    class Meta(_BaseRegistrationSerializer.Meta):
        fields = [
            "women_special_info",
            "women_weight_kg", "women_height_cm",
            "men_weight_kg", "men_height_cm",
            "blood_type",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Full detail serializer (read)
# ─────────────────────────────────────────────────────────────────────────────

class FamilyRegistrationDetailSerializer(serializers.ModelSerializer):
    """Full read serializer with nested disease entries."""

    disease_entries = FamilyDiseaseEntrySerializer(many=True, read_only=True)
    moh_area_name = serializers.CharField(source="moh_area.name", read_only=True)
    phm_area_name = serializers.CharField(source="phm_area.name", read_only=True)
    husband_diseases = serializers.SerializerMethodField()
    wife_diseases = serializers.SerializerMethodField()

    class Meta:
        model = FamilyRegistration
        fields = [
            "id",
            "submitted_by",
            "moh_area", "moh_area_name",
            "phm_area", "phm_area_name",
            "husband_name", "wife_name",
            "address", "nic_number",
            "husband_dob", "wife_dob",
            "contact_number", "email",
            "job", "education_level",
            "marriage_date",
            "husband_diseases", "wife_diseases",
            "disease_entries",
            "women_special_info",
            "women_weight_kg", "women_height_cm",
            "men_weight_kg", "men_height_cm",
            "blood_type",
            "is_complete", "current_step",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_husband_diseases(self, obj: FamilyRegistration) -> list[str]:
        return list(
            obj.disease_entries.filter(person=PersonChoice.HUSBAND)
            .values_list("disease__name", flat=True)
        )

    def get_wife_diseases(self, obj: FamilyRegistration) -> list[str]:
        return list(
            obj.disease_entries.filter(person=PersonChoice.WIFE)
            .values_list("disease__name", flat=True)
        )
