"""
Family registration views.
OOP: each step is a dedicated endpoint; DRF generic views keep code DRY.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import UserRole
from .models import Disease, FamilyRegistration
from .serializers import (
    DiseaseSerializer,
    FamilyRegistrationDetailSerializer,
    Step1Serializer,
    Step2Serializer,
    Step3Serializer,
    Step4Serializer,
)


class IsFamilyOrMidwifeOrSister(permissions.BasePermission):
    """Allow family members, midwives, and sisters."""

    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and request.user.role in [
            UserRole.FAMILY, UserRole.MIDWIFE, UserRole.SISTER
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Disease reference
# ─────────────────────────────────────────────────────────────────────────────

class DiseaseListView(generics.ListAPIView):
    """GET /api/family/diseases/ – public disease reference list."""

    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer
    permission_classes = [permissions.AllowAny]


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 – Start / create registration
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationStep1View(APIView):
    """
    POST /api/family/register/step1/
    Creates a new family registration record with step-1 data.
    Returns the registration ID to continue with subsequent steps.
    """

    permission_classes = [IsFamilyOrMidwifeOrSister]

    def post(self, request):
        serializer = Step1Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration: FamilyRegistration = serializer.save(
            submitted_by=request.user, current_step=1
        )
        return Response(
            {"registration_id": registration.id, "current_step": 1},
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 – Contact & background
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationStep2View(APIView):
    """PATCH /api/family/register/<pk>/step2/"""

    permission_classes = [IsFamilyOrMidwifeOrSister]

    def patch(self, request, pk):
        registration = self._get_registration(pk, request.user)
        serializer = Step2Serializer(registration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(current_step=2)
        return Response({"registration_id": registration.id, "current_step": 2})

    @staticmethod
    def _get_registration(pk, user) -> FamilyRegistration:
        try:
            return FamilyRegistration.objects.get(pk=pk, submitted_by=user)
        except FamilyRegistration.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Registration not found.")


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 – Diseases
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationStep3View(APIView):
    """PATCH /api/family/register/<pk>/step3/"""

    permission_classes = [IsFamilyOrMidwifeOrSister]

    def patch(self, request, pk):
        try:
            registration = FamilyRegistration.objects.get(pk=pk, submitted_by=request.user)
        except FamilyRegistration.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Registration not found.")

        serializer = Step3Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(registration, serializer.validated_data)
        return Response({"registration_id": registration.id, "current_step": 3})


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 – Vitals (completes the registration)
# ─────────────────────────────────────────────────────────────────────────────

class RegistrationStep4View(APIView):
    """PATCH /api/family/register/<pk>/step4/  – final step, marks complete."""

    permission_classes = [IsFamilyOrMidwifeOrSister]

    def patch(self, request, pk):
        try:
            registration = FamilyRegistration.objects.get(pk=pk, submitted_by=request.user)
        except FamilyRegistration.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Registration not found.")

        serializer = Step4Serializer(registration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        registration.mark_complete()

        return Response(
            FamilyRegistrationDetailSerializer(registration).data,
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Detail & List views
# ─────────────────────────────────────────────────────────────────────────────

class FamilyRegistrationDetailView(generics.RetrieveAPIView):
    """GET /api/family/register/<pk>/"""

    serializer_class = FamilyRegistrationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in [UserRole.MIDWIFE, UserRole.SISTER]:
            return FamilyRegistration.objects.select_related(
                "moh_area", "phm_area", "submitted_by"
            ).prefetch_related("disease_entries__disease")
        return FamilyRegistration.objects.filter(submitted_by=user).prefetch_related(
            "disease_entries__disease"
        )


class FamilyRegistrationListView(generics.ListAPIView):
    """GET /api/family/register/ – list registrations visible to the requester."""

    serializer_class = FamilyRegistrationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["phm_area", "moh_area", "is_complete"]
    search_fields = ["husband_name", "wife_name", "nic_number"]

    def get_queryset(self):
        user = self.request.user
        qs = FamilyRegistration.objects.select_related(
            "moh_area", "phm_area"
        ).prefetch_related("disease_entries__disease")

        if user.role == UserRole.FAMILY:
            return qs.filter(submitted_by=user)
        if user.role == UserRole.MIDWIFE:
            return qs.filter(phm_area=user.phm_area)
        # Sister sees all
        return qs.all()
