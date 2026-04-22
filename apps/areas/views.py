"""Areas views."""
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


class PHMAreaListView(generics.ListCreateAPIView):
    """
    GET  /api/areas/phm/         – list all PHM areas
    GET  /api/areas/phm/?moh=1   – filter by MOH area
    POST /api/areas/phm/         – create (admin only)
    """

    serializer_class = PHMAreaSerializer
    filterset_fields = ["moh_area"]
    search_fields = ["name"]

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        return PHMArea.objects.select_related("moh_area", "assigned_midwife").all()

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

class MidwifeScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = MidwifeScheduleSerializer
    permission_classes = [drf_permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = MidwifeSchedule.objects.select_related("midwife").all()
        midwife_id = self.request.query_params.get("midwife")
        if midwife_id:
            queryset = queryset.filter(midwife_id=midwife_id)
        return queryset
