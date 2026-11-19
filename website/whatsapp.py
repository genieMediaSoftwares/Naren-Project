import re
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings



def clean_phone_number(number: str) -> str:
    """Format Indian phone number to international E.164 without plus sign (e.g., 919848204278)."""
    if not number:
        return "919848204278"
    digits = re.sub(r'\D', '', str(number))
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return f"91{digits[1:]}"
    return digits or "919848204278"


def get_formatted_submission_time(dt=None) -> str:
    """Return formatted submission timestamp in IST (Indian Standard Time)."""
    try:
        ist = ZoneInfo("Asia/Kolkata")
        if dt is None:
            now = datetime.now(ist)
        elif dt.tzinfo is None:
            now = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ist)
        else:
            now = dt.astimezone(ist)
        return now.strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return datetime.now().strftime("%d %b %Y, %I:%M %p")


def build_contact_whatsapp_message(contact, subject: str = None) -> str:
    """Compose plain-text formatted WhatsApp enquiry message."""
    submission_time = get_formatted_submission_time(getattr(contact, 'created_at', None))
    subj = subject or getattr(contact, 'subject', '') or 'Appointment Booking / Enquiry'
    msg_body = getattr(contact, 'message', '') or 'N/A'

    return (
        "🔔 *NEW APPOINTMENT / CONTACT ENQUIRY*\n\n"
        "👤 *PATIENT INFORMATION*\n"
        f"• *Name:* {contact.name}\n"
        f"• *Phone Number:* {contact.phone}\n"
        f"• *Email:* {contact.email or 'N/A'}\n\n"
        "📝 *ENQUIRY DETAILS*\n"
        f"• *Subject:* {subj}\n"
        f"• *Message:* {msg_body}\n\n"
        f"🕒 *SUBMISSION TIME*\n{submission_time}\n\n"
        "📍 *Naren Ultrasound & Fetal Medicine Center*"
    )


def build_patient_booking_whatsapp_message(booking) -> str:
    """Compose plain-text formatted WhatsApp patient booking appointment message."""
    submission_time = get_formatted_submission_time(getattr(booking, 'created_at', None))
    services_text = (getattr(booking, 'services', '') or '').strip()
    services_display = services_text if services_text else "None selected"

    return (
        "🔔 *NEW PATIENT APPOINTMENT*\n\n"
        "👤 *PATIENT INFORMATION*\n"
        f"• *Full Name:* {booking.full_name}\n"
        f"• *Age:* {booking.age}\n"
        f"• *Gender:* {booking.gender}\n"
        f"• *Mobile Number:* {booking.phone}\n\n"
        "🏥 *MEDICAL INFORMATION*\n"
        f"• *Referred Doctor:* {booking.referred_doctor or 'N/A'}\n"
        f"• *Hospital / Clinic:* {booking.hospital_name or 'N/A'}\n\n"
        "📅 *APPOINTMENT PREFERENCE*\n"
        f"• *Preferred Date:* {booking.preferred_date}\n"
        f"• *Preferred Time:* {booking.preferred_time}\n\n"
        "🔬 *SELECTED SERVICES / SCANS*\n"
        f"{services_display}\n\n"
        f"🕒 *SUBMISSION TIME*\n{submission_time}\n\n"
        "📍 *Naren Ultrasound & Fetal Medicine Center*"
    )


def get_contact_whatsapp_url(contact, subject: str = None, recipient: str = None) -> str:
    """Generate universal WhatsApp deep-link URL (wa.me) for contact enquiry."""
    target_number = clean_phone_number(
        recipient or getattr(settings, 'WHATSAPP_RECIPIENT_NUMBER', '919848204278')
    )
    message_text = build_contact_whatsapp_message(contact, subject)
    return f"https://wa.me/{target_number}?text={urllib.parse.quote(message_text)}"


def get_patient_booking_whatsapp_url(booking, recipient: str = None) -> str:
    """Generate universal WhatsApp deep-link URL (wa.me) for patient appointment booking."""
    target_number = clean_phone_number(
        recipient or getattr(settings, 'WHATSAPP_RECIPIENT_NUMBER', '919848204278')
    )
    message_text = build_patient_booking_whatsapp_message(booking)
    return f"https://wa.me/{target_number}?text={urllib.parse.quote(message_text)}"
