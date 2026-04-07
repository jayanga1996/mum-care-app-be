from django.contrib import admin
from .models import Disease, FamilyDiseaseEntry, FamilyRegistration


class FamilyDiseaseEntryInline(admin.TabularInline):
    model = FamilyDiseaseEntry
    extra = 0
    autocomplete_fields = ["disease"]


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(FamilyRegistration)
class FamilyRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        "husband_name", "wife_name", "phm_area",
        "blood_type", "is_complete", "current_step", "created_at",
    ]
    list_filter = ["is_complete", "blood_type", "phm_area", "education_level"]
    search_fields = ["husband_name", "wife_name", "nic_number", "contact_number"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [FamilyDiseaseEntryInline]

    fieldsets = (
        ("Step 1 – Location & Personal Info", {
            "fields": (
                "submitted_by", "moh_area", "phm_area",
                "husband_name", "wife_name", "address", "nic_number",
            )
        }),
        ("Step 2 – Contact & Background", {
            "fields": (
                "husband_dob", "wife_dob", "contact_number",
                "email", "job", "education_level", "marriage_date",
            )
        }),
        ("Step 4 – Vitals", {
            "fields": (
                "women_special_info",
                "women_weight_kg", "women_height_cm",
                "men_weight_kg", "men_height_cm",
                "blood_type",
            )
        }),
        ("Status", {"fields": ("is_complete", "current_step", "created_at", "updated_at")}),
    )
