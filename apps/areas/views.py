"""Areas views."""
from django.db.models import Q
from rest_framework import generics, permissions
from .models import MOHArea, PHMArea
from .serializers import MOHAreaSerializer, PHMAreaCreateSerializer, PHMAreaSerializer, MidwifeScheduleSerializer


class MOHAreaListView(generics.ListCreateAPIView):
    """GET /api/areas/moh/  – list all MOH areas (public read)."""

    queryset = MOHArea.objects.prefetch_related("phm_areas").all()
    serializer_class = MOHAreaSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


from rest_framework.response import Response

from rest_framework import status

class PHMAreaListView(generics.ListCreateAPIView):
    """
    GET  /api/areas/phm/         – list all PHM areas
    GET  /api/areas/phm/?moh=1   – filter by MOH area
    POST /api/areas/phm/         – create (admin only)
    """

    serializer_class = PHMAreaSerializer
    filterset_fields = ["moh_area"]
    search_fields = ["name"]

    pagination_class = None  # Disable pagination to return all PHM areas

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        return PHMArea.objects.select_related("moh_area", "assigned_midwife").all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        })

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PHMAreaCreateSerializer
        return PHMAreaSerializer


class PHMAreaDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/areas/phm/<pk>/"""

    queryset = PHMArea.objects.select_related("moh_area", "assigned_midwife").all()
    serializer_class = PHMAreaSerializer
    permission_classes = [permissions.IsAuthenticated]


# --- Midwife Schedule ViewSet ---
from rest_framework import viewsets, permissions as drf_permissions
from .models import MidwifeSchedule
from apps.users.models import UserRole

class MidwifeScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = MidwifeScheduleSerializer
    permission_classes = [drf_permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Role rules:
        - Midwife: can access only own schedules (CRUD via this ViewSet)
        - Mother: can read schedules for her PHM area from her assigned midwife
        - Sister: can read schedules (optionally filter by ?midwife=<uuid>) but cannot create/update/delete
        """
        user = self.request.user
        base = MidwifeSchedule.objects.select_related("midwife", "phm_area")

        if user.role == UserRole.MIDWIFE:
            return base.filter(midwife=user)

        if user.role == UserRole.MOTHER:
            midwife = getattr(user, "assigned_midwife", None)
            phm = user.phm_area
            if not midwife or not phm:
                return base.none()
            return base.filter(midwife=midwife).filter(
                Q(phm_area=phm) | Q(phm_area__isnull=True, location__iexact=phm.name)
            )

        if user.role == UserRole.SISTER:
            midwife_id = self.request.query_params.get("midwife")
            if midwife_id:
                return base.filter(midwife_id=midwife_id)
            return base.all()

        return base.none()

    def get_permissions(self):
        user = self.request.user
        # Read endpoints
        if self.action in ["list", "retrieve"]:
            return [drf_permissions.IsAuthenticated()]

        # Write endpoints (create/update/delete) only for midwives
        if user.role == UserRole.MIDWIFE:
            return [drf_permissions.IsAuthenticated()]

        return [drf_permissions.IsAdminUser()]

    def perform_create(self, serializer):
        """
        Midwife creates schedule for herself only (ignore any midwife id in payload).
        """
        serializer.save(midwife=self.request.user)



# --- List all schedules for a midwife by midwife_id ---
class MidwifeScheduleByMidwifeListView(generics.ListAPIView):
    serializer_class = MidwifeScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, midwife, *args, **kwargs):
        user = request.user
        # Midwife can only see own schedules via this endpoint
        if user.role == UserRole.MIDWIFE and str(user.id) != str(midwife):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        # Mother can only see schedules of her assigned midwife
        if user.role == UserRole.MOTHER:
            assigned = getattr(user, "assigned_midwife", None)
            if not assigned or str(assigned.id) != str(midwife):
                return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        schedules = MidwifeSchedule.objects.filter(midwife_id=midwife).select_related(
            "midwife", "phm_area"
        )
        if user.role == UserRole.MOTHER:
            phm = user.phm_area
            if not phm:
                schedules = schedules.none()
            else:
                schedules = schedules.filter(
                    Q(phm_area=phm) | Q(phm_area__isnull=True, location__iexact=phm.name)
                )
        serializer = self.get_serializer(schedules, many=True)
        return Response({"count": schedules.count(), "results": serializer.data})


class MyScheduleListView(generics.ListAPIView):
    """
    GET /api/areas/schedules/me/
    - Midwife: list own schedules
    - Mother: list schedules of assigned midwife
    """
    serializer_class = MidwifeScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Return {count, results} from list() override; avoid page wrapper issues

    def get_queryset(self):
        user = self.request.user
        base = MidwifeSchedule.objects.select_related("midwife", "phm_area")

        if user.role == UserRole.MIDWIFE:
            return base.filter(midwife=user)

        if user.role == UserRole.MOTHER:
            midwife = getattr(user, "assigned_midwife", None)
            phm = user.phm_area
            if not midwife or not phm:
                return base.none()
            return base.filter(midwife=midwife).filter(
                Q(phm_area=phm) | Q(phm_area__isnull=True, location__iexact=phm.name)
            )

        return base.none()
