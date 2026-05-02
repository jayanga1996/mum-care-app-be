"""
Smoke tests for critical JWT + profile + schedule APIs (SQLite test DB).
Run: python manage.py test apps.users.tests.test_api_smoke -v 2
"""
from datetime import date, time as dtime

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.areas.models import MOHArea, PHMArea, MidwifeSchedule
from apps.users.models import User, UserRole


class ApiSmokeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.moh = MOHArea.objects.create(name="Smoke MOH")
        self.phm = PHMArea.objects.create(name="Smoke PHM", moh_area=self.moh)

        self.midwife = User.objects.create_user(
            email="midwife_smoke@test.local",
            password="pass12345!",
            full_name="Smoke MW",
            role=UserRole.MIDWIFE,
        )
        self.midwife.is_active = True
        self.midwife.is_approved = True
        self.midwife.phm_area = self.phm
        self.midwife.save(update_fields=["is_active", "is_approved", "phm_area"])

        self.phm.assigned_midwife = self.midwife
        self.phm.save(update_fields=["assigned_midwife"])

        self.mother = User.objects.create_user(
            email="mother_smoke@test.local",
            password="pass12345!",
            full_name="Smoke Mom",
            role=UserRole.MOTHER,
        )
        self.mother.is_active = True
        self.mother.is_approved = True
        self.mother.phm_area = self.phm
        self.mother.save(update_fields=["is_active", "is_approved", "phm_area"])

    def _token(self, email: str, password: str) -> str:
        url = reverse("token_obtain_pair")
        r = self.client.post(url, {"email": email, "password": password}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.content)
        self.assertIn("access", r.data)
        return r.data["access"]

    def test_midwife_me_and_schedule_json_errors_not_html(self):
        token = self._token(self.midwife.email, "pass12345!")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        me_url = reverse("users:me")
        r = self.client.get(me_url)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("managed_phm_area", r.data)
        self.assertEqual(r.data["email"], self.midwife.email)

        create_url = "/api/areas/midwife-schedules/"
        r = self.client.post(
            create_url,
            {"type": "Clinic", "date": str(date.today()), "time": "14:30:00"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIn("id", r.data)

        list_url = "/api/areas/schedules/me/"
        r = self.client.get(list_url)
        self.assertEqual(r.status_code, 200, r.content)
        body = r.data
        results = body if isinstance(body, list) else body.get("results", body)
        self.assertTrue(len(results) >= 1)

        # SerializerMethodField phm_area_name must not crash when serializing
        sched = MidwifeSchedule.objects.filter(midwife=self.midwife).first()
        self.assertIsNotNone(sched)

    def test_mother_schedules_me_lists_ok(self):
        MidwifeSchedule.objects.create(
            midwife=self.midwife,
            type="Home Visit",
            date=date.today(),
            time=dtime(9, 0),
            location=self.phm.name,
        )
        token = self._token(self.mother.email, "pass12345!")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = self.client.get("/api/areas/schedules/me/")
        self.assertEqual(r.status_code, 200, r.content)

    def test_mother_sees_schedules_when_phm_row_has_no_assigned_midwife(self):
        """
        Production often sets User.phm_area but never PHMArea.assigned_midwife.
        Mothers must still see schedules from midwives linked via User.phm_area.
        """
        self.phm.assigned_midwife = None
        self.phm.save(update_fields=["assigned_midwife"])

        MidwifeSchedule.objects.create(
            midwife=self.midwife,
            type="Clinic",
            date=date.today(),
            time=dtime(11, 0, 0),
            location=self.phm.name,
        )
        token = self._token(self.mother.email, "pass12345!")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = self.client.get("/api/areas/schedules/me/")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.data
        results = body if isinstance(body, list) else body.get("results", body)
        self.assertEqual(len(results), 1)
