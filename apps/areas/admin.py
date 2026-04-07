from django.contrib import admin
from .models import MOHArea, PHMArea


@admin.register(MOHArea)
class MOHAreaAdmin(admin.ModelAdmin):
    list_display = ["name", "phm_area_count", "created_at"]
    search_fields = ["name"]

    def phm_area_count(self, obj):
        return obj.phm_areas.count()
    phm_area_count.short_description = "PHM Areas"


@admin.register(PHMArea)
class PHMAreaAdmin(admin.ModelAdmin):
    list_display = ["name", "moh_area", "assigned_midwife", "created_at"]
    list_filter = ["moh_area"]
    search_fields = ["name"]
    autocomplete_fields = ["assigned_midwife"]
