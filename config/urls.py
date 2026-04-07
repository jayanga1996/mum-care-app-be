"""Root URL configuration for Mum Care App backend."""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

# ── Swagger / ReDoc schema ─────────────────────────────────────────────────
schema_view = get_schema_view(
    openapi.Info(
        title="Mum Care App API",
        default_version="v1",
        description="REST API for Mum Care maternal health application",
        contact=openapi.Contact(email="admin@mumcare.lk"),
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # JWT Auth
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # App APIs
    path("api/users/", include("apps.users.urls")),
    path("api/areas/", include("apps.areas.urls")),
    path("api/family/", include("apps.family.urls")),
    path("api/uploads/", include("apps.uploads.urls")),

    # Docs
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
