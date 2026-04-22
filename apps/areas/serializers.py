"""Areas serializers."""
from rest_framework import serializers
from .models import MOHArea, PHMArea

from .models import MidwifeSchedule


class MOHAreaSerializer(serializers.ModelSerializer):
    phm_area_count = serializers.SerializerMethodField()

    class Meta:
        model = MOHArea
        fields = ["id", "name", "phm_area_count", "created_at"]
        read_only_fields = ["id", "created_at", "phm_area_count"]

    def get_phm_area_count(self, obj: MOHArea) -> int:
        return obj.phm_areas.count()


class PHMAreaSerializer(serializers.ModelSerializer):
    moh_area_name = serializers.CharField(source="moh_area.name", read_only=True)
    assigned_midwife_name = serializers.SerializerMethodField()

    class Meta:
        model = PHMArea
        fields = [
            "id", "name",
            "moh_area", "moh_area_name",
            "assigned_midwife", "assigned_midwife_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "moh_area_name", "assigned_midwife_name"]

    def get_assigned_midwife_name(self, obj: PHMArea) -> str | None:
        return obj.assigned_midwife.full_name if obj.assigned_midwife else None


class PHMAreaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PHMArea
        fields = ["name", "moh_area", "assigned_midwife"]


# --- Midwife Schedule Serializer ---
class MidwifeScheduleSerializer(serializers.ModelSerializer):
    midwife_name = serializers.CharField(source="midwife.full_name", read_only=True)

    class Meta:
        model = MidwifeSchedule
        fields = ["id", "midwife", "midwife_name", "type", "date", "time", "location", "created_at"]
        read_only_fields = ["id", "created_at", "midwife_name"]
