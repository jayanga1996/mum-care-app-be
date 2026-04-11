"""
Management command: seed_data
Idempotently seeds the database with reference data
(MOH areas, PHM areas, diseases) and approves all users.
Run once after first deployment or migrations.

Usage:
    python manage.py seed_data
"""
from django.core.management.base import BaseCommand

from apps.areas.models import MOHArea, PHMArea
from apps.family.models import Disease
from apps.users.models import User

MOH_AREA_MAP = {
    "Colombo MOH": [
        "Colombo 1 PHM", "Colombo 2 PHM", "Colombo 3 PHM",
        "Colombo 5 PHM", "Maradana PHM", "Dematagoda PHM",
        "Borella PHM", "Narahenpita PHM", "Kirulapone PHM",
        "Dehiwala PHM", "Mount Lavinia PHM",
    ],
    "Gampaha MOH": [
        "Negombo PHM", "Wattala PHM", "Ragama PHM",
        "Ja-Ela PHM", "Kelaniya PHM", "Mahara PHM", "Kadawatha PHM",
    ],
    "Kalutara MOH": [
        "Panadura PHM", "Horana PHM", "Beruwala PHM",
        "Aluthgama PHM", "Matugama PHM",
    ],
    "Kandy MOH": [
        "Kandy Central PHM", "Peradeniya PHM", "Katugastota PHM",
        "Gampola PHM", "Nawalapitiya PHM", "Kundasale PHM",
    ],
    "Matale MOH": [
        "Matale PHM", "Dambulla PHM", "Galewela PHM", "Sigiriya PHM",
    ],
    "Nuwara Eliya MOH": [
        "Nuwara Eliya PHM", "Hatton PHM", "Talawakele PHM", "Ginigathena PHM",
    ],
    "Galle MOH": [
        "Galle Fort PHM", "Unawatuna PHM", "Karapitiya PHM",
        "Baddegama PHM", "Elpitiya PHM", "Hikkaduwa PHM", "Ambalangoda PHM",
    ],
    "Matara MOH": [
        "Matara PHM", "Weligama PHM", "Akuressa PHM",
        "Kamburupitiya PHM", "Mulatiyana PHM", "Mirissa PHM",
    ],
    "Hambantota MOH": [
        "Hambantota PHM", "Tangalle PHM", "Tissamaharama PHM", "Ambalantota PHM",
    ],
    "Jaffna MOH": [
        "Jaffna Central PHM", "Nallur PHM", "Chavakachcheri PHM", "Point Pedro PHM",
    ],
    "Kurunegala MOH": [
        "Kurunegala PHM", "Kuliyapitiya PHM", "Maho PHM",
        "Giriulla PHM", "Ibbagamuwa PHM", "Nikaweratiya PHM",
    ],
    "Puttalam MOH": [
        "Puttalam PHM", "Chilaw PHM", "Wennappuwa PHM", "Dankotuwa PHM",
    ],
    "Anuradhapura MOH": [
        "Anuradhapura PHM", "Kekirawa PHM", "Medawachchiya PHM", "Mihintale PHM",
    ],
    "Polonnaruwa MOH": [
        "Polonnaruwa PHM", "Kaduruwela PHM", "Hingurakgoda PHM",
    ],
    "Badulla MOH": [
        "Badulla PHM", "Bandarawela PHM", "Haputale PHM", "Welimada PHM",
    ],
    "Monaragala MOH": [
        "Monaragala PHM", "Bibile PHM", "Wellawaya PHM",
    ],
    "Ratnapura MOH": [
        "Ratnapura PHM", "Embilipitiya PHM", "Balangoda PHM", "Eheliyagoda PHM",
    ],
    "Kegalle MOH": [
        "Kegalle PHM", "Mawanella PHM", "Warakapola PHM", "Rambukkana PHM",
    ],
    "Trincomalee MOH": [
        "Trincomalee PHM", "Kinniya PHM", "Muttur PHM",
    ],
    "Batticaloa MOH": [
        "Batticaloa PHM", "Eravur PHM", "Kattankudy PHM",
    ],
    "Ampara MOH": [
        "Ampara PHM", "Kalmunai PHM", "Sammanthurai PHM",
    ],
}

DISEASES = [
    "Diabetes",
    "Hypertension",
    "Anaemia",
    "Asthma",
    "Heart Disease",
    "Kidney Disease",
    "Thyroid Disorder",
    "Epilepsy",
    "Hepatitis B",
    "Tuberculosis",
    "Malaria",
    "Dengue",
    "Thalassemia",
    "HIV/AIDS",
    "STI (Sexually Transmitted Infection)",
    "Mental Health Disorder",
    "Gestational Diabetes",
    "Pre-eclampsia",
    "Rheumatoid Arthritis",
    "Liver Disease",
]


class Command(BaseCommand):
    help = "Seed reference data: MOH areas, PHM areas, diseases, and approve all users."

    def handle(self, *args, **options) -> None:
        self._seed_areas()
        self._seed_diseases()
        self._approve_users()
        self.stdout.write(self.style.SUCCESS("\n✅  Seeding complete!"))
        self.stdout.write("\nTest Credentials (password: MumCare@123):")
        self.stdout.write("  sister@mumcare.lk  |  midwife@mumcare.lk  |  mother@mumcare.lk  |  family@mumcare.lk")

    def _seed_areas(self) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- MOH & PHM Areas ---"))
        moh_count = phm_count = 0
        for moh_name, phm_names in MOH_AREA_MAP.items():
            moh, created = MOHArea.objects.get_or_create(name=moh_name)
            if created:
                moh_count += 1
                self.stdout.write(f"  + MOH  {moh_name}")
            for phm_name in phm_names:
                _, c = PHMArea.objects.get_or_create(name=phm_name, defaults={"moh_area": moh})
                if c:
                    phm_count += 1
                    self.stdout.write(f"      + PHM  {phm_name}")
        self.stdout.write(self.style.SUCCESS(
            f"  {moh_count} MOH area(s) and {phm_count} PHM area(s) added."
        ))

    def _seed_diseases(self) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Diseases ---"))
        count = 0
        for name in DISEASES:
            _, created = Disease.objects.get_or_create(name=name)
            if created:
                count += 1
                self.stdout.write(f"  + {name}")
        self.stdout.write(self.style.SUCCESS(f"  {count} disease(s) added."))

    def _approve_users(self) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Approving Users ---"))
        updated = User.objects.filter(is_approved=False).update(is_approved=True)
        for u in User.objects.all():
            self.stdout.write(f"  ✓ {u.email}  ({u.role})")
        self.stdout.write(self.style.SUCCESS(f"  {updated} user(s) newly approved."))
