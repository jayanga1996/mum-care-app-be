from django.urls import path
from .views import FileUploadCreateView, FileUploadDetailView, FileUploadListView

app_name = "uploads"

urlpatterns = [
    path("", FileUploadListView.as_view(), name="list"),
    path("upload/", FileUploadCreateView.as_view(), name="upload"),
    path("<uuid:pk>/", FileUploadDetailView.as_view(), name="detail"),
]
