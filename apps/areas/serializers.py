"""Areas serializers."""
from typing import Any, Dict, Optional

from django.utils import timezone
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
    cancelled_by_name = serializers.SerializerMethodField()
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
            "response_status",
            "confirmed_at",
            "cancelled_at",
            "cancelled_by",
            "cancelled_by_name",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "midwife_name",
            "midwife",
            "phm_area_name",
            "cancelled_by_name",
            "confirmed_at",
            "cancelled_at",
            "cancelled_by",
        ]
        extra_kwargs = {
            "location": {"required": False, "allow_blank": True},
        }

    def get_phm_area_name(self, obj: MidwifeSchedule) -> Optional[str]:
        loc = (getattr(obj, "location", None) or "").strip()
        return loc or None

    def get_cancelled_by_name(self, obj: MidwifeSchedule) -> Optional[str]:
        cb = getattr(obj, "cancelled_by", None)
        if cb is None:
            return None
        try:
            return cb.full_name
        except Exception:
            return None

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
        inst = self.instance

        if inst is not None and inst.response_status == MidwifeSchedule.ResponseStatus.CANCELLED:
            raise serializers.ValidationError(
                {"detail": "This schedule is cancelled and cannot be edited."}
            )

        if getattr(user, "role", None) == UserRole.MOTHER and inst is not None:
            bad = set(attrs.keys()) - {"response_status", "cancellation_reason"}
            if bad:
                raise serializers.ValidationError(
                    {k: "Mothers can only confirm or cancel (response_status / cancellation_reason)." for k in bad}
                )

        new_status = attrs.get("response_status", getattr(inst, "response_status", None))
        if inst is not None and new_status is not None:
            self._validate_response_transition(inst.response_status, new_status)

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

    @staticmethod
    def _validate_response_transition(old: str, new: str) -> None:
        allowed = {
            MidwifeSchedule.ResponseStatus.SCHEDULED: {
                MidwifeSchedule.ResponseStatus.CONFIRMED,
                MidwifeSchedule.ResponseStatus.CANCELLED,
            },
            MidwifeSchedule.ResponseStatus.CONFIRMED: {
                MidwifeSchedule.ResponseStatus.CANCELLED,
            },
            MidwifeSchedule.ResponseStatus.CANCELLED: set(),
        }
        if new == old:
            return
        if old not in allowed or new not in allowed.get(old, set()):
            raise serializers.ValidationError(
                {"response_status": f"Cannot change status from {old!r} to {new!r}."}
            )

    def create(self, validated_data):
        validated_data.pop("phm_area", None)
        return super().create(validated_data)

    def update(self, instance: MidwifeSchedule, validated_data: Dict[str, Any]):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        role = getattr(user, "role", None)

        validated_data.pop("phm_area", None)

        if role == UserRole.MOTHER:
            validated_data = {
                k: v for k, v in validated_data.items() if k in ("response_status", "cancellation_reason")
            }

        old_status = instance.response_status
        new_status = validated_data.get("response_status", old_status)

        instance = super().update(instance, validated_data)

        now = timezone.now()
        save_fields: list[str] = []
        if (
            new_status == MidwifeSchedule.ResponseStatus.CONFIRMED
            and old_status != MidwifeSchedule.ResponseStatus.CONFIRMED
        ):
            instance.confirmed_at = now
            save_fields.append("confirmed_at")
        if (
            new_status == MidwifeSchedule.ResponseStatus.CANCELLED
            and old_status != MidwifeSchedule.ResponseStatus.CANCELLED
        ):
            instance.cancelled_at = now
            instance.cancelled_by = user
            save_fields.extend(["cancelled_at", "cancelled_by"])
        if save_fields:
            instance.save(update_fields=save_fields)

        return instance
