from django.urls import path
from .views import (
    MOHAreaListView,
    PHMAreaDetailView,
    PHMAreaListView,
    MidwifeScheduleViewSet,
    MidwifeScheduleByMidwifeListView,
    MyScheduleListView,
)

from rest_framework.routers import DefaultRouter

app_name = "areas"


# Router for ViewSets
router = DefaultRouter()
router.register(r"midwife-schedules", MidwifeScheduleViewSet, basename="midwife-schedule")

urlpatterns = [
    path("moh/", MOHAreaListView.as_view(), name="moh-list"),
    path("phm/", PHMAreaListView.as_view(), name="phm-list"),
    path("phm/<int:pk>/", PHMAreaDetailView.as_view(), name="phm-detail"),
    path("midwife/<str:midwife>/schedules/", MidwifeScheduleByMidwifeListView.as_view(), name="midwife-schedules"),
    path("schedules/me/", MyScheduleListView.as_view(), name="my-schedules"),
]

# Add ViewSet URLs
urlpatterns += router.urls
