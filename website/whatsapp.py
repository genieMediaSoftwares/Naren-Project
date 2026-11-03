import json
import logging
import re
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
import requests

logger = logging.getLogger(__name__)


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


def _send_whatsapp_payload(message_text: str, recipient: str = None) -> bool:
    """Send WhatsApp message using Meta WhatsApp Business Cloud API or generic Webhook."""
    target_number = clean_phone_number(
        recipient or getattr(settings, 'WHATSAPP_RECIPIENT_NUMBER', '919848204278')
    )
    access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '').strip()
    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '').strip()
    webhook_url = getattr(settings, 'WHATSAPP_WEBHOOK_URL', '').strip()

    # 1. Meta WhatsApp Business Cloud API
    if access_token and phone_number_id:
        url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": target_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text,
            },
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code in (200, 201):
                logger.info("WhatsApp Cloud API notification sent successfully to %s: %s", target_number, response.text)
                return True
            else:
                logger.error("WhatsApp Cloud API failed (%s): %s", response.status_code, response.text)
        except Exception as e:
            logger.error("Error connecting to WhatsApp Cloud API: %s", e)

    # 2. Generic WhatsApp Webhook / Integration Gateway (e.g. WATI, UltraMsg, Zapier, Make)
    if webhook_url:
        payload = {
            "to": target_number,
            "message": message_text,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code in (200, 201, 202):
                logger.info("WhatsApp Webhook notification sent successfully to %s", target_number)
                return True
            else:
                logger.error("WhatsApp Webhook failed (%s): %s", response.status_code, response.text)
        except Exception as e:
            logger.error("Error posting to WhatsApp Webhook: %s", e)

    if not (access_token and phone_number_id) and not webhook_url:
        logger.info(
            "WhatsApp notification queued for %s (Awaiting WHATSAPP_ACCESS_TOKEN & WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_WEBHOOK_URL):\n%s",
            target_number,
            message_text,
        )
    return False


def send_whatsapp_async(message_text: str, recipient: str = None):
    """Run notification in background thread so HTTP response to user is never delayed."""
    try:
        thread = threading.Thread(
            target=_send_whatsapp_payload,
            args=(message_text, recipient),
            daemon=True,
        )
        thread.start()
    except Exception as e:
        logger.error("Failed to start WhatsApp notification thread: %s", e)


def send_patient_booking_whatsapp(booking, recipient: str = None):
    """Generate and dispatch instant WhatsApp notification for Patient Information / Book Appointment form."""
    try:
        submission_time = get_formatted_submission_time(getattr(booking, 'created_at', None))
        services_text = (getattr(booking, 'services', '') or '').strip()
        services_display = services_text if services_text else "None selected"

        message = (
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
        send_whatsapp_async(message, recipient)
    except Exception as e:
        logger.error("Error creating patient booking WhatsApp notification: %s", e)


def send_contact_message_whatsapp(contact, subject: str = None, recipient: str = None):
    """Generate and dispatch instant WhatsApp notification for Contact / Appointment Enquiry form."""
    try:
        submission_time = get_formatted_submission_time(getattr(contact, 'created_at', None))
        subj = subject or getattr(contact, 'subject', '') or 'Appointment Booking / Enquiry'
        msg_body = getattr(contact, 'message', '') or 'N/A'

        message = (
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
        send_whatsapp_async(message, recipient)
    except Exception as e:
        logger.error("Error creating contact message WhatsApp notification: %s", e)

