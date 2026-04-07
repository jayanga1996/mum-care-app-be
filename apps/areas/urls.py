from django.urls import path
from .views import MOHAreaListView, PHMAreaDetailView, PHMAreaListView

app_name = "areas"

urlpatterns = [
    path("moh/", MOHAreaListView.as_view(), name="moh-list"),
    path("phm/", PHMAreaListView.as_view(), name="phm-list"),
    path("phm/<int:pk>/", PHMAreaDetailView.as_view(), name="phm-detail"),
]
