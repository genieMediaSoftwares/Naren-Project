from datetime import date, datetime
import re
import smtplib
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.test import Client, TestCase, SimpleTestCase, override_settings
from django.core import mail
from django.urls import reverse

from .models import BlogPost, PatientBooking, ContactMessage
from .whatsapp import clean_phone_number, get_patient_booking_whatsapp_url
from .slots import (
    APPOINTMENT_SLOT_SPECS,
    APPOINTMENT_TIME_SLOTS,
    CLINIC_CLOSE_MINUTES,
    CLINIC_OPEN_MINUTES,
    CLINIC_TZ,
    LEGACY_SLOT_ALIASES,
    SLOT_INTERVAL_MINUTES,
    get_clinic_today,
    get_past_slots_for_date,
    get_slot_db_variants,
    normalize_booked_slots,
    validate_appointment_date_and_slot,
)


def _parse_12h_minutes(time_str: str) -> int:
    parsed = datetime.strptime(time_str.strip(), "%I:%M %p")
    return parsed.hour * 60 + parsed.minute


class AppointmentSlotDefinitionTests(TestCase):
    def test_slots_are_chronological_30min_intervals_within_clinic_hours(self):
        self.assertEqual(len(APPOINTMENT_TIME_SLOTS), 24)
        self.assertEqual(APPOINTMENT_TIME_SLOTS[0], "8:00 AM - 8:30 AM")
        self.assertEqual(APPOINTMENT_TIME_SLOTS[-1], "7:30 PM - 8:00 PM")

        prev_end = None
        for label, spec_start, spec_end in APPOINTMENT_SLOT_SPECS:
            start_str, end_str = [part.strip() for part in label.split("-")]
            start_min = _parse_12h_minutes(start_str)
            end_min = _parse_12h_minutes(end_str)

            self.assertEqual(start_min, spec_start)
            self.assertEqual(end_min, spec_end)
            self.assertLess(start_min, end_min)
            self.assertEqual(end_min - start_min, SLOT_INTERVAL_MINUTES)
            self.assertGreaterEqual(start_min, CLINIC_OPEN_MINUTES)
            self.assertLessEqual(end_min, CLINIC_CLOSE_MINUTES)

            if prev_end is not None:
                self.assertEqual(start_min, prev_end)
            prev_end = end_min

        # Confirm known broken legacy AM/PM strings are absent from canonical slots
        for legacy in LEGACY_SLOT_ALIASES:
            self.assertNotIn(legacy, APPOINTMENT_TIME_SLOTS)

    def test_ist_timezone_conversion_and_past_slot_cutoff(self):
        # 2026-11-12 19:00 UTC == 2026-11-13 00:30 IST (Friday)
        utc_evening = datetime(2026, 11, 12, 19, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(get_clinic_today(utc_evening), date(2026, 11, 13))
        self.assertEqual(get_past_slots_for_date(date(2026, 11, 13), now=utc_evening), [])

        # 2026-11-12 06:00 UTC == 2026-11-12 11:30 IST (Thursday)
        utc_morning = datetime(2026, 11, 12, 6, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(get_clinic_today(utc_morning), date(2026, 11, 12))
        past = get_past_slots_for_date(date(2026, 11, 12), now=utc_morning)
        self.assertEqual(
            past,
            [
                "8:00 AM - 8:30 AM",
                "8:30 AM - 9:00 AM",
                "9:00 AM - 9:30 AM",
                "9:30 AM - 10:00 AM",
                "10:00 AM - 10:30 AM",
                "10:30 AM - 11:00 AM",
                "11:00 AM - 11:30 AM",
                "11:30 AM - 12:00 PM",
            ],
        )

    def test_legacy_slot_normalization_and_variants(self):
        normalized = normalize_booked_slots(
            ["4:30 AM - 5:00 AM", "11:30 AM - 12:00 AM", "10:00 AM - 10:30 AM"]
        )
        self.assertEqual(
            normalized,
            [
                "10:00 AM - 10:30 AM",
                "11:30 AM - 12:00 PM",
                "4:30 PM - 5:00 PM",
            ],
        )
        self.assertEqual(
            set(get_slot_db_variants("11:30 AM - 12:00 PM")),
            {"11:30 AM - 12:00 PM", "11:30 AM - 12:00 AM"},
        )

    def test_schedule_validation_mon_sat_vs_sunday(self):
        fixed_now = datetime(2026, 11, 12, 7, 30, tzinfo=CLINIC_TZ)  # Thursday 7:30 AM IST
        for slot in APPOINTMENT_TIME_SLOTS:
            with self.subTest(slot=slot):
                self.assertIsNone(
                    validate_appointment_date_and_slot(
                        date(2026, 11, 14),  # Saturday
                        slot,
                        now=fixed_now,
                    )
                )
        self.assertIsNotNone(
            validate_appointment_date_and_slot(
                date(2026, 11, 14),
                "7:30 AM - 8:00 AM",
                now=fixed_now,
            )
        )
        self.assertIsNotNone(
            validate_appointment_date_and_slot(
                date(2026, 11, 14),
                "8:00 PM - 8:30 PM",
                now=fixed_now,
            )
        )
        sunday_err = validate_appointment_date_and_slot(
            date(2026, 11, 15),  # Sunday
            "8:00 AM - 8:30 AM",
            now=fixed_now,
        )
        self.assertIn("Sunday", sunday_err)


class PatientBookingFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.fixed_now = datetime(2026, 11, 12, 9, 0, tzinfo=CLINIC_TZ)  # Thursday 9:00 AM IST

    def _valid_post_payload(self, **overrides):
        data = {
            "full_name": "Test Patient",
            "age": "28",
            "gender": "Female",
            "phone": "9876543210",
            "preferred_date": "2026-11-16",  # Monday
            "preferred_time": "11:30 AM - 12:00 PM",
            "confirmation": "on",
            "scan_antenatal": ["NT Scan"],
        }
        data.update(overrides)
        return data

    def test_patient_info_get_renders_corrected_slots_only(self):
        with patch("website.views.get_clinic_now", return_value=self.fixed_now):
            response = self.client.get(reverse("patient_info"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('min="2026-11-12"', html)
        self.assertIn('id="dateSlotMessage"', html)
        rendered_slots = re.findall(
            r'<option\s+value="([^"]+)"[^>]*>([^<]+)</option>', html
        )
        self.assertEqual(len(rendered_slots), 24)
        self.assertEqual([val for val, _ in rendered_slots], list(APPOINTMENT_TIME_SLOTS))
        self.assertEqual([lbl for _, lbl in rendered_slots], list(APPOINTMENT_TIME_SLOTS))
        for legacy in LEGACY_SLOT_ALIASES:
            self.assertNotIn(legacy, html)

    def test_booked_slots_api_handles_sunday_past_dates_past_slots_and_legacy_rows(self):
        PatientBooking.objects.create(
            full_name="Legacy Booked",
            age=30,
            gender="Female",
            phone="9000000001",
            preferred_date=date(2026, 11, 16),
            preferred_time="11:30 AM - 12:00 AM",
            services="NT Scan",
            is_cancelled=False,
        )
        PatientBooking.objects.create(
            full_name="Cancelled Row",
            age=30,
            gender="Female",
            phone="9000000002",
            preferred_date=date(2026, 11, 16),
            preferred_time="10:00 AM - 10:30 AM",
            services="NT Scan",
            is_cancelled=True,
        )

        midday_now = datetime(2026, 11, 12, 12, 15, tzinfo=CLINIC_TZ)
        with patch("website.views.get_clinic_now", return_value=midday_now):
            sunday_resp = self.client.get(reverse("booked_slots_api"), {"date": "2026-11-15"})
            self.assertEqual(sunday_resp.status_code, 200)
            sunday_data = sunday_resp.json()
            self.assertTrue(sunday_data["is_closed"])
            self.assertIn("Sunday", sunday_data["closed_reason"])
            self.assertEqual(len(sunday_data["unavailable_slots"]), 24)

            past_resp = self.client.get(reverse("booked_slots_api"), {"date": "2026-11-11"})
            self.assertEqual(past_resp.status_code, 200)
            self.assertTrue(past_resp.json()["is_past_date"])

            today_resp = self.client.get(reverse("booked_slots_api"), {"date": "2026-11-12"})
            today_data = today_resp.json()
            self.assertEqual(
                today_data["past_slots"],
                [
                    "8:00 AM - 8:30 AM",
                    "8:30 AM - 9:00 AM",
                    "9:00 AM - 9:30 AM",
                    "9:30 AM - 10:00 AM",
                    "10:00 AM - 10:30 AM",
                    "10:30 AM - 11:00 AM",
                    "11:00 AM - 11:30 AM",
                    "11:30 AM - 12:00 PM",
                    "12:00 PM - 12:30 PM",
                ],
            )

            mon_resp = self.client.get(reverse("booked_slots_api"), {"date": "2026-11-16"})
            mon_data = mon_resp.json()
            self.assertFalse(mon_data["is_closed"])
            self.assertEqual(mon_data["booked_slots"], ["11:30 AM - 12:00 PM"])

    @patch("requests.sessions.Session.request")
    @patch("website.views.send_mail")
    def test_booking_post_rejects_sunday_past_invalid_and_duplicate_slots(
        self, mock_send_mail, mock_network
    ):
        PatientBooking.objects.create(
            full_name="Existing Legacy Booking",
            age=27,
            gender="Female",
            phone="9000000003",
            preferred_date=date(2026, 11, 16),
            preferred_time="4:30 AM - 5:00 AM",
            services="Growth Scan",
            is_cancelled=False,
        )

        noon_now = datetime(2026, 11, 12, 12, 5, tzinfo=CLINIC_TZ)
        with patch("website.views.get_clinic_now", return_value=noon_now):
            bad_cases = [
                ("Sunday rejected", {"preferred_date": "2026-11-15", "preferred_time": "8:00 AM - 8:30 AM"}),
                ("Past date rejected", {"preferred_date": "2026-11-11", "preferred_time": "8:00 AM - 8:30 AM"}),
                ("Before opening slot rejected", {"preferred_date": "2026-11-16", "preferred_time": "7:30 AM - 8:00 AM"}),
                ("After closing slot rejected", {"preferred_date": "2026-11-16", "preferred_time": "8:00 PM - 8:30 PM"}),
                ("Legacy broken slot rejected", {"preferred_date": "2026-11-16", "preferred_time": "11:00 AM - 11:30 PM"}),
                ("Passed morning slot today rejected", {"preferred_date": "2026-11-12", "preferred_time": "8:00 AM - 8:30 AM"}),
                ("Passed today slot rejected", {"preferred_date": "2026-11-12", "preferred_time": "11:30 AM - 12:00 PM"}),
                ("Duplicate against legacy variant rejected", {"preferred_date": "2026-11-16", "preferred_time": "4:30 PM - 5:00 PM"}),
            ]
            for label, overrides in bad_cases:
                with self.subTest(label=label):
                    resp = self.client.post(
                        reverse("patient_info"),
                        self._valid_post_payload(**overrides),
                    )
                    self.assertEqual(resp.status_code, 200)
                    self.assertIn("error", resp.context)

        self.assertEqual(PatientBooking.objects.count(), 1)
        mock_send_mail.assert_not_called()
        mock_network.assert_not_called()

    @patch("requests.sessions.Session.request")
    @patch("website.views.send_mail")
    def test_booking_post_succeeds_and_stores_exact_canonical_slot(
        self, mock_send_mail, mock_network
    ):
        with patch("website.views.get_clinic_now", return_value=self.fixed_now):
            resp = self.client.post(
                reverse("patient_info"),
                self._valid_post_payload(
                    preferred_date="2026-11-16",
                    preferred_time="11:30 AM - 12:00 PM",
                ),
            )

        self.assertRedirects(resp, reverse("appointment_success"))
        booking = PatientBooking.objects.get(phone="9876543210")
        self.assertEqual(booking.preferred_date, date(2026, 11, 16))
        self.assertEqual(booking.preferred_time, "11:30 AM - 12:00 PM")
        mock_send_mail.assert_called_once()
        mock_network.assert_not_called()

    @patch("requests.sessions.Session.request")
    @patch("website.views.send_mail")
    def test_restored_morning_and_closing_slots_book_and_block_duplicates(
        self, mock_send_mail, mock_network
    ):
        target_slots = (
            "8:00 AM - 8:30 AM",
            "8:30 AM - 9:00 AM",
            "9:00 AM - 9:30 AM",
            "9:30 AM - 10:00 AM",
            "7:30 PM - 8:00 PM",
        )
        early_now = datetime(2026, 11, 12, 7, 45, tzinfo=CLINIC_TZ)
        with patch("website.views.get_clinic_now", return_value=early_now):
            for idx, slot in enumerate(target_slots):
                with self.subTest(slot=slot):
                    resp = self.client.post(
                        reverse("patient_info"),
                        self._valid_post_payload(
                            phone=f"987650000{idx}",
                            preferred_date="2026-11-16",
                            preferred_time=slot,
                        ),
                    )
                    self.assertRedirects(resp, reverse("appointment_success"))

                    dup_resp = self.client.post(
                        reverse("patient_info"),
                        self._valid_post_payload(
                            phone=f"987659999{idx}",
                            preferred_date="2026-11-16",
                            preferred_time=slot,
                        ),
                    )
                    self.assertEqual(dup_resp.status_code, 200)
                    self.assertIn("error", dup_resp.context)

        api_data = self.client.get(reverse("booked_slots_api"), {"date": "2026-11-16"}).json()
        self.assertEqual(api_data["booked_slots"], list(target_slots))
        self.assertEqual(mock_send_mail.call_count, len(target_slots))
        mock_network.assert_not_called()

    def test_model_clean_validates_new_rows_without_breaking_legacy_edits(self):
        legacy = PatientBooking.objects.create(
            full_name="Historical",
            age=31,
            gender="Female",
            phone="9000000004",
            preferred_date=date(2026, 12, 13),  # Historical Sunday row
            preferred_time="4:30 AM - 5:00 AM",
            services="Routine",
            is_cancelled=False,
        )
        # Updating existing historical row (e.g. cancelling in Admin) must succeed
        legacy.is_cancelled = True
        legacy.full_clean()

        invalid_new = PatientBooking(
            full_name="Invalid New",
            age=25,
            gender="Female",
            phone="9000000005",
            preferred_date=date(2099, 1, 4),  # Sunday in future
            preferred_time="10:00 AM - 10:30 AM",
            services="NT Scan",
            is_cancelled=False,
        )
        with self.assertRaises(ValidationError):
            invalid_new.full_clean()


class SeoAndTemplateTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_blog_metadata_without_changing_visible_headings(self):
        long_meta = (
            "A comprehensive guide to first-trimester NT ultrasound screening at Naren Ultrasound "
            "in Visakhapatnam for expectant parents seeking timely and accurate fetal evaluation."
        )
        self.assertGreater(len(long_meta), 160)

        post_with_meta = BlogPost.objects.create(
            title="Understanding NT Scan",
            slug="understanding-nt-scan",
            featured_image="blog/sample-nt.png",
            meta_description=long_meta,
            content="<h3>First Section</h3><p>Intro</p><h4>Nested Point</h4><p>Details</p>",
            is_published=True,
        )
        BlogPost.objects.create(
            title="Doppler Study Basics",
            slug="doppler-study-basics",
            featured_image="blog/sample-doppler.png",
            meta_description="",
            content="<p>Color Doppler ultrasound evaluates blood flow in maternal and fetal vessels.</p>",
            is_published=True,
        )

        list_resp = self.client.get(reverse("blog_list"))
        self.assertEqual(list_resp.status_code, 200)
        list_html = list_resp.content.decode("utf-8")
        self.assertIn("Understanding NT Scan", list_html)

        detail_resp = self.client.get(reverse("blog_detail", args=[post_with_meta.slug]))
        self.assertEqual(detail_resp.status_code, 200)
        detail_html = detail_resp.content.decode("utf-8")
        self.assertIn("<title>Understanding NT Scan | Naren Ultrasound</title>", detail_html)
        self.assertIn(f'content="{post_with_meta.meta_description}"', detail_html)
        self.assertIn("https://www.narenultrasound.in/media/blog/sample-nt.png", detail_html)
        self.assertIn('<h3>First Section</h3>', detail_html)
        self.assertIn('<h4>Nested Point</h4>', detail_html)

    def test_public_pages_status_unique_titles_and_contact_fixes(self):
        routes = [
            reverse("home"),
            reverse("about"),
            reverse("services"),
            reverse("doctors"),
            reverse("gallery"),
            reverse("patient_info"),
            reverse("contact"),
            reverse("contact_success"),
            reverse("appointment_success"),
            reverse("blog_list"),
        ]
        titles = []
        for url in routes:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                html = resp.content.decode("utf-8")
                match = re.search(r"<title>\s*(.*?)\s*</title>", html, re.DOTALL)
                self.assertIsNotNone(match)
                titles.append(match.group(1))

        self.assertEqual(len(titles), len(set(titles)))

        contact_html = self.client.get(reverse("contact")).content.decode("utf-8")
        self.assertIn('href="/patient-info/"', contact_html)
        self.assertIn("Expert Radiologists", contact_html)
        self.assertIn('title="Map location of Naren Ultrasound and Fetal Medicine Center, Visakhapatnam"', contact_html)



@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ManualWhatsAppReleaseTests(TestCase):
    def payload(self, slot="8:00 AM - 8:30 AM"):
        return {
            "full_name": "Audit & Test", "age": "28", "gender": "Male",
            "phone": "9000000000", "preferred_date": "2026-11-16",
            "preferred_time": slot, "confirmation": "on",
            "referred_doctor": "Audit Doctor", "hospital_name": "Test Clinic",
            "scan_antenatal": ["NT Scan"], "scan_routine": ["Whole Abdomen"],
        }

    @patch("requests.sessions.Session.request", side_effect=AssertionError("No outbound API allowed"))
    def test_all_slots_save_email_and_manual_links_without_api(self, network):
        fixed = datetime(2026, 11, 12, 7, 0, tzinfo=CLINIC_TZ)
        for slot in APPOINTMENT_TIME_SLOTS:
            with self.subTest(slot=slot), patch("website.views.get_clinic_now", return_value=fixed):
                response = self.client.post(reverse("patient_info"), self.payload(slot))
                self.assertEqual(response.status_code, 302)
                parsed = urlparse(self.client.session["whatsapp_url"])
                self.assertEqual((parsed.scheme, parsed.netloc, parsed.path),
                                 ("https", "wa.me", "/919848204278"))
                message = parse_qs(parsed.query)["text"][0]
                for value in ("Audit & Test", "28", "Male", "9000000000", "Audit Doctor",
                              "Test Clinic", "2026-11-16", slot, "NT Scan", "Whole Abdomen", "IST"):
                    self.assertIn(value, message)
                page = self.client.get(response.url)
                self.assertContains(page, "Send via WhatsApp (+91 9848204278)")
                self.assertContains(page, 'target="_blank"')
        self.assertEqual(PatientBooking.objects.count(), 24)
        self.assertEqual(len(mail.outbox), 24)
        for message in mail.outbox:
            self.assertEqual(message.to, ["narenultrasound@gmail.com"])
            self.assertEqual(message.subject, "New Patient Appointment Booking")
            self.assertIn("Audit & Test", message.body)
            self.assertIn("Whole Abdomen", message.body)
        network.assert_not_called()

    @patch("requests.sessions.Session.request", side_effect=AssertionError("No outbound API allowed"))
    def test_contact_preserves_email_and_manual_fallback(self, network):
        response = self.client.post(reverse("contact"), {
            "name": "Audit Contact", "phone": "9000000000", "email": "audit@example.invalid",
            "subject": "Test enquiry", "message": "Test details",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["narenultrasound@gmail.com"])
        parsed = urlparse(self.client.session["whatsapp_url"])
        self.assertEqual(parsed.path, "/919848204278")
        self.assertIn("Test details", parse_qs(parsed.query)["text"][0])
        self.assertContains(self.client.get(response.url), "wa.me/919848204278")
        network.assert_not_called()

    @patch("website.views.send_mail", side_effect=smtplib.SMTPException("Test SMTP failure"))
    def test_original_email_failure_behavior_is_preserved(self, send_mail):
        with patch("website.views.get_clinic_now", return_value=datetime(2026, 11, 12, 7, 0, tzinfo=CLINIC_TZ)):
            with self.assertRaises(smtplib.SMTPException):
                self.client.post(reverse("patient_info"), self.payload())
        self.assertEqual(PatientBooking.objects.count(), 1)
        send_mail.assert_called_once()

    def test_manual_message_does_not_truncate_services(self):
        booking = PatientBooking(full_name="Audit", age=28, gender="Female", phone="9000000000",
                                 preferred_date=date(2026, 11, 16), preferred_time=APPOINTMENT_TIME_SLOTS[0],
                                 services="Long service selection " * 30)
        message = parse_qs(urlparse(get_patient_booking_whatsapp_url(booking)).query)["text"][0]
        self.assertIn(booking.services.strip(), message)
        for number in ("9848204278", "+91 98482 04278", "09848204278"):
            self.assertEqual(clean_phone_number(number), "919848204278")


class BookingBrowserRegressionTests(SimpleTestCase):
    def test_availability_races_and_manual_whatsapp(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js required for browser-script regression checks")
        result = subprocess.run([node, str(Path(__file__).with_name("tests_booking_browser.js"))],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
