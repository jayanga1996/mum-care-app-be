from django.urls import path
from .views import MOHAreaListView, PHMAreaDetailView, PHMAreaListView, MidwifeScheduleViewSet

from rest_framework.routers import DefaultRouter

app_name = "areas"


# Router for ViewSets
router = DefaultRouter()
router.register(r"midwife-schedules", MidwifeScheduleViewSet, basename="midwife-schedule")

urlpatterns = [
    path("moh/", MOHAreaListView.as_view(), name="moh-list"),
    path("phm/", PHMAreaListView.as_view(), name="phm-list"),
    path("phm/<int:pk>/", PHMAreaDetailView.as_view(), name="phm-detail"),
]

# Add ViewSet URLs
urlpatterns += router.urls
