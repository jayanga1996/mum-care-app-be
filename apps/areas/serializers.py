"""Areas serializers."""
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
    phm_area_name = serializers.CharField(source="phm_area.name", read_only=True)

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
            # Set from phm_area in validate() / create(); clients send phm_area id only
            "location": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return attrs
        user = request.user
        if getattr(user, "role", None) != UserRole.MIDWIFE:
            return attrs

        if self.instance is None:
            phm = attrs.get("phm_area")
            loc = attrs.get("location", "") or ""
            if phm is None and loc:
                phm = PHMArea.objects.filter(name__iexact=str(loc).strip()).first()
                if phm:
                    attrs["phm_area"] = phm
            if attrs.get("phm_area") is None:
                raise serializers.ValidationError(
                    {"phm_area": "PHM area is required (send phm_area id or a matching location name)."}
                )
            phm = attrs["phm_area"]
            if phm.assigned_midwife_id != user.id:
                raise serializers.ValidationError(
                    {"phm_area": "You may only create schedules for PHM areas assigned to you."}
                )
            attrs["location"] = phm.name
            return attrs

        if attrs.get("phm_area") is not None:
            phm = attrs["phm_area"]
            if phm.assigned_midwife_id != user.id:
                raise serializers.ValidationError({"phm_area": "Invalid PHM area."})
            attrs["location"] = phm.name
        return attrs

    def create(self, validated_data):
        phm = validated_data.get("phm_area")
        if phm:
            validated_data["location"] = phm.name
        return super().create(validated_data)

    def update(self, instance, validated_data):
        phm = validated_data.get("phm_area")
        if phm:
            validated_data["location"] = phm.name
        return super().update(instance, validated_data)
