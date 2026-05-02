"""Areas serializers."""
from typing import Optional

from rest_framework import serializers
from apps.users.models import UserRole

from .models import MOHArea, PHMArea, MidwifeSchedule


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

    def get_assigned_midwife_name(self, obj):
        return obj.assigned_midwife.full_name if obj.assigned_midwife and hasattr(obj.assigned_midwife, 'full_name') else None


class PHMAreaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PHMArea
        fields = ["name", "moh_area", "assigned_midwife"]


# --- Midwife Schedule Serializer ---
class MidwifeScheduleSerializer(serializers.ModelSerializer):
    midwife_name = serializers.CharField(source="midwife.full_name", read_only=True)
    phm_area_name = serializers.SerializerMethodField()
    # Optional write: resolve PHM for validation when client sends an id (legacy / admin tools).
    phm_area = serializers.PrimaryKeyRelatedField(
        queryset=PHMArea.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = MidwifeSchedule
        fields = [
            "id",
            "midwife",
            "midwife_name",
            "type",
            "date",
            "time",
            "location",
            "phm_area",
            "phm_area_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "midwife_name", "midwife", "phm_area_name"]
        extra_kwargs = {
            "location": {"required": False, "allow_blank": True},
        }

    def get_phm_area_name(self, obj: MidwifeSchedule) -> Optional[str]:
        loc = (getattr(obj, "location", None) or "").strip()
        return loc or None

    @staticmethod
    def _default_phm_for_midwife(user) -> Optional[PHMArea]:
        """
        Resolve PHM for schedule creation (midwife has exactly one area):
        1) Reverse OneToOne managed_area from PHM.assigned_midwife
        2) PHMArea where assigned_midwife_id == user.id
        3) User.phm_area (often set in admin even when PHM.assigned_midwife was never synced)
        """
        managed = getattr(user, "managed_area", None)
        if managed is not None:
            return managed
        by_role = PHMArea.objects.filter(assigned_midwife_id=user.id).first()
        if by_role is not None:
            return by_role
        pa_id = getattr(user, "phm_area_id", None)
        if pa_id:
            return PHMArea.objects.filter(pk=pa_id).first()
        return None

    @staticmethod
    def _midwife_can_use_phm(user, phm: PHMArea) -> bool:
        """Midwife may schedule only for PHMs linked to them."""
        if phm.assigned_midwife_id is not None and phm.assigned_midwife_id == user.id:
            return True
        managed = getattr(user, "managed_area", None)
        if managed is not None and managed.pk == phm.pk:
            return True
        if getattr(user, "phm_area_id", None) == phm.pk:
            return True
        return False

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return attrs
        user = request.user
        if getattr(user, "role", None) != UserRole.MIDWIFE:
            return attrs

        if self.instance is None:
            phm = attrs.pop("phm_area", None)
            loc = attrs.get("location", "") or ""
            if phm is None and loc:
                phm = PHMArea.objects.filter(name__iexact=str(loc).strip()).first()
            if phm is None:
                auto = self._default_phm_for_midwife(user)
                if auto:
                    phm = auto
            if phm is None:
                raise serializers.ValidationError(
                    {
                        "phm_area": "No PHM area is linked to your midwife account. "
                        "Ask an admin to assign you to a PHM area."
                    }
                )
            if not self._midwife_can_use_phm(user, phm):
                raise serializers.ValidationError(
                    {"phm_area": "You may only create schedules for PHM areas assigned to you."}
                )
            attrs["location"] = phm.name
            return attrs

        phm = attrs.pop("phm_area", None)
        if phm is not None:
            if not self._midwife_can_use_phm(user, phm):
                raise serializers.ValidationError({"phm_area": "Invalid PHM area."})
            attrs["location"] = phm.name
        return attrs

    def create(self, validated_data):
        validated_data.pop("phm_area", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("phm_area", None)
        return super().update(instance, validated_data)
