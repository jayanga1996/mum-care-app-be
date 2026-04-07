from django.urls import path
from .views import (
    DiseaseListView,
    FamilyRegistrationDetailView,
    FamilyRegistrationListView,
    RegistrationStep1View,
    RegistrationStep2View,
    RegistrationStep3View,
    RegistrationStep4View,
)

app_name = "family"

urlpatterns = [
    # Reference
    path("diseases/", DiseaseListView.as_view(), name="diseases"),

    # 4-step registration wizard
    path("register/step1/", RegistrationStep1View.as_view(), name="step1"),
    path("register/<int:pk>/step2/", RegistrationStep2View.as_view(), name="step2"),
    path("register/<int:pk>/step3/", RegistrationStep3View.as_view(), name="step3"),
    path("register/<int:pk>/step4/", RegistrationStep4View.as_view(), name="step4"),

    # Detail & list
    path("register/<int:pk>/", FamilyRegistrationDetailView.as_view(), name="detail"),
    path("register/", FamilyRegistrationListView.as_view(), name="list"),
]
