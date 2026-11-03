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


def _send_whatsapp_payload(message_text: str, recipient: str = None, template_data: dict = None) -> dict:
    """
    Send WhatsApp message using Meta WhatsApp Business Cloud API or generic Webhook.
    Returns dict with status details: {"success": bool, "status_code": int, "response": str, "error": str}
    """
    if not getattr(settings, 'WHATSAPP_NOTIFICATION_ENABLED', True):
        logger.info("WhatsApp notifications are disabled via WHATSAPP_NOTIFICATION_ENABLED.")
        return {"success": False, "status_code": 0, "response": "", "error": "Disabled"}

    target_number = clean_phone_number(
        recipient or getattr(settings, 'WHATSAPP_RECIPIENT_NUMBER', '919848204278')
    )
    access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '').strip()
    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '').strip()
    template_name = getattr(settings, 'WHATSAPP_TEMPLATE_NAME', '').strip()
    template_language = getattr(settings, 'WHATSAPP_TEMPLATE_LANGUAGE', 'en_US').strip() or 'en_US'
    webhook_url = getattr(settings, 'WHATSAPP_WEBHOOK_URL', '').strip()

    result = {
        "success": False,
        "status_code": 0,
        "response": "",
        "error": "",
        "provider": None,
    }

    # 1. Meta WhatsApp Business Cloud API
    if access_token and phone_number_id:
        result["provider"] = "Meta Cloud API"
        url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Use pre-approved template if configured, otherwise text payload
        if template_name:
            components = []
            if template_data and "body_params" in template_data:
                components.append({
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in template_data["body_params"]]
                })
            payload = {
                "messaging_product": "whatsapp",
                "to": target_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": template_language},
                    "components": components,
                },
            }
        else:
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
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            result["status_code"] = response.status_code
            result["response"] = response.text
            if response.status_code in (200, 201):
                logger.info("WhatsApp Cloud API notification sent successfully to %s: %s", target_number, response.text)
                result["success"] = True
                return result
            else:
                logger.error("WhatsApp Cloud API error (%s) to %s: %s", response.status_code, target_number, response.text)
                result["error"] = response.text
                return result
        except Exception as e:
            logger.error("Connection error to WhatsApp Cloud API: %s", e)
            result["error"] = str(e)
            return result

    # 2. Generic WhatsApp Webhook / Gateway (e.g., WATI, UltraMsg, Zapier, Make)
    if webhook_url:
        result["provider"] = "Webhook Gateway"
        payload = {
            "to": target_number,
            "recipient": target_number,
            "message": message_text,
            "text": message_text,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            response = requests.post(webhook_url, json=payload, timeout=5)
            result["status_code"] = response.status_code
            result["response"] = response.text
            if response.status_code in (200, 201, 202):
                logger.info("WhatsApp Webhook notification sent successfully to %s: %s", target_number, response.text)
                result["success"] = True
                return result
            else:
                logger.error("WhatsApp Webhook error (%s) to %s: %s", response.status_code, target_number, response.text)
                result["error"] = response.text
                return result
        except Exception as e:
            logger.error("Connection error to WhatsApp Webhook: %s", e)
            result["error"] = str(e)
            return result

    # 3. Neither credentials nor webhook configured
    result["error"] = "No WhatsApp credentials configured (WHATSAPP_ACCESS_TOKEN/WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_WEBHOOK_URL missing)"
    logger.warning(
        "WhatsApp notification skipped for %s: %s",
        target_number,
        result["error"],
    )
    return result


def dispatch_whatsapp_notification(message_text: str, recipient: str = None, template_data: dict = None) -> dict:
    """
    Dispatch WhatsApp notification synchronously with resilient short timeout.
    Synchronous execution is required on serverless platforms (e.g., Vercel / AWS Lambda)
    because background daemon threads are frozen/terminated immediately when the HTTP response returns.
    """
    try:
        return _send_whatsapp_payload(message_text, recipient, template_data)
    except Exception as e:
        logger.error("Unexpected error in dispatch_whatsapp_notification: %s", e)
        return {"success": False, "status_code": 0, "response": "", "error": str(e)}


# Backward-compatible alias for existing imports
def send_whatsapp_async(message_text: str, recipient: str = None):
    return dispatch_whatsapp_notification(message_text, recipient)


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
        template_data = {
            "body_params": [
                booking.full_name,
                booking.phone,
                f"{booking.preferred_date} ({booking.preferred_time})",
                services_display[:200],  # Meta template body params limit
                submission_time
            ]
        }
        return dispatch_whatsapp_notification(message, recipient, template_data)
    except Exception as e:
        logger.error("Error creating patient booking WhatsApp notification: %s", e)
        return {"success": False, "status_code": 0, "response": "", "error": str(e)}


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
        template_data = {
            "body_params": [
                contact.name,
                contact.phone,
                subj,
                msg_body[:200],
                submission_time
            ]
        }
        return dispatch_whatsapp_notification(message, recipient, template_data)
    except Exception as e:
        logger.error("Error creating contact message WhatsApp notification: %s", e)
        return {"success": False, "status_code": 0, "response": "", "error": str(e)}

