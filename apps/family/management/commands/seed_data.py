"""
Management command: seed_data
Idempotently seeds the database with reference data
(MOH areas, PHM areas, diseases).
Run once after first deployment or migrations.
"""
from django.core.management.base import BaseCommand

from apps.areas.models import MOHArea, PHMArea
from apps.family.models import Disease

MOH_AREAS = [
    "Galle MOH",
    "Karapitiya MOH",
    "Hikkaduwa MOH",
    "Elpitiya MOH",
    "Balapitiya MOH",
]

PHM_AREA_MAP = {
    "Galle MOH": ["Unawatuna PHM", "Galle Fort PHM"],
    "Karapitiya MOH": ["Karapitiya PHM", "Habaraduwa PHM"],
    "Hikkaduwa MOH": ["Hikkaduwa PHM", "Dodanduwa PHM"],
    "Elpitiya MOH": ["Elpitiya PHM", "Pitigala PHM"],
    "Balapitiya MOH": ["Balapitiya PHM", "Ambalangoda PHM"],
}

DISEASES = [
    "Diabetes",
    "Hypertension",
    "Heart Disease",
    "Asthma",
    "Thyroid Disorder",
    "Kidney Disease",
    "HIV/AIDS",
    "Epilepsy",
    "Anaemia",
    "Tuberculosis",
]


class Command(BaseCommand):
    help = "Seed reference data: MOH areas, PHM areas, diseases."

    def handle(self, *args, **options) -> None:
        self._seed_areas()
        self._seed_diseases()
        self.stdout.write(self.style.SUCCESS("✅  Reference data seeded successfully."))

    def _seed_areas(self) -> None:
        for moh_name in MOH_AREAS:
            moh, created = MOHArea.objects.get_or_create(name=moh_name)
            if created:
                self.stdout.write(f"  Created MOH area: {moh_name}")

            for phm_name in PHM_AREA_MAP.get(moh_name, []):
                _, c = PHMArea.objects.get_or_create(name=phm_name, defaults={"moh_area": moh})
                if c:
                    self.stdout.write(f"    Created PHM area: {phm_name}")

    def _seed_diseases(self) -> None:
        for name in DISEASES:
            _, created = Disease.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f"  Created disease: {name}")
