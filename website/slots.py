from datetime import date, datetime
from zoneinfo import ZoneInfo

CLINIC_TZ = ZoneInfo("Asia/Kolkata")
CLINIC_OPEN_MINUTES = 8 * 60   # 8:00 AM
CLINIC_CLOSE_MINUTES = 20 * 60  # 8:00 PM
SLOT_INTERVAL_MINUTES = 30

# Canonical 30-minute appointment slots (Monday to Saturday, 8:00 AM - 8:00 PM clinic hours).
APPOINTMENT_SLOT_SPECS = (
    ("8:00 AM - 8:30 AM", 8 * 60, 8 * 60 + 30),
    ("8:30 AM - 9:00 AM", 8 * 60 + 30, 9 * 60),
    ("9:00 AM - 9:30 AM", 9 * 60, 9 * 60 + 30),
    ("9:30 AM - 10:00 AM", 9 * 60 + 30, 10 * 60),
    ("10:00 AM - 10:30 AM", 10 * 60, 10 * 60 + 30),
    ("10:30 AM - 11:00 AM", 10 * 60 + 30, 11 * 60),
    ("11:00 AM - 11:30 AM", 11 * 60, 11 * 60 + 30),
    ("11:30 AM - 12:00 PM", 11 * 60 + 30, 12 * 60),
    ("12:00 PM - 12:30 PM", 12 * 60, 12 * 60 + 30),
    ("12:30 PM - 1:00 PM", 12 * 60 + 30, 13 * 60),
    ("1:00 PM - 1:30 PM", 13 * 60, 13 * 60 + 30),
    ("1:30 PM - 2:00 PM", 13 * 60 + 30, 14 * 60),
    ("2:00 PM - 2:30 PM", 14 * 60, 14 * 60 + 30),
    ("2:30 PM - 3:00 PM", 14 * 60 + 30, 15 * 60),
    ("3:00 PM - 3:30 PM", 15 * 60, 15 * 60 + 30),
    ("3:30 PM - 4:00 PM", 15 * 60 + 30, 16 * 60),
    ("4:00 PM - 4:30 PM", 16 * 60, 16 * 60 + 30),
    ("4:30 PM - 5:00 PM", 16 * 60 + 30, 17 * 60),
    ("5:00 PM - 5:30 PM", 17 * 60, 17 * 60 + 30),
    ("5:30 PM - 6:00 PM", 17 * 60 + 30, 18 * 60),
    ("6:00 PM - 6:30 PM", 18 * 60, 18 * 60 + 30),
    ("6:30 PM - 7:00 PM", 18 * 60 + 30, 19 * 60),
    ("7:00 PM - 7:30 PM", 19 * 60, 19 * 60 + 30),
    ("7:30 PM - 8:00 PM", 19 * 60 + 30, 20 * 60),
)

APPOINTMENT_TIME_SLOTS = tuple(label for label, _, _ in APPOINTMENT_SLOT_SPECS)
VALID_APPOINTMENT_SLOTS = frozenset(APPOINTMENT_TIME_SLOTS)
SLOT_START_MINUTES = {label: start for label, start, _ in APPOINTMENT_SLOT_SPECS}

# Maps historical mistyped AM/PM strings stored in existing PatientBooking rows
# to their canonical corrected labels so legacy rows continue blocking the right slot.
LEGACY_SLOT_ALIASES = {
    "11:00 AM - 11:30 PM": "11:00 AM - 11:30 AM",
    "11:30 AM - 12:00 AM": "11:30 AM - 12:00 PM",
    "12:30 AM - 1:00 AM": "12:30 PM - 1:00 PM",
    "1:30 AM - 2:00 AM": "1:30 PM - 2:00 PM",
    "2:30 AM - 3:00 AM": "2:30 PM - 3:00 PM",
    "3:30 AM - 4:00 AM": "3:30 PM - 4:00 PM",
    "4:30 AM - 5:00 AM": "4:30 PM - 5:00 PM",
    "5:30 AM - 6:00 AM": "5:30 PM - 6:00 PM",
    "6:30 AM - 7:00 AM": "6:30 PM - 7:00 PM",
}

_CANONICAL_TO_VARIANTS = {label: [label] for label in APPOINTMENT_TIME_SLOTS}
for _legacy_label, _canonical_label in LEGACY_SLOT_ALIASES.items():
    _CANONICAL_TO_VARIANTS[_canonical_label].append(_legacy_label)


def get_clinic_now(now: datetime | None = None) -> datetime:
    """Return current timezone-aware datetime in clinic IST (Asia/Kolkata)."""
    if now is None:
        return datetime.now(CLINIC_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=CLINIC_TZ)
    return now.astimezone(CLINIC_TZ)


def get_clinic_today(now: datetime | None = None) -> date:
    """Return today's calendar date in clinic IST (Asia/Kolkata)."""
    return get_clinic_now(now).date()


def is_clinic_closed_day(target_date: date) -> bool:
    """Return True when the clinic is closed (Sundays)."""
    return target_date.weekday() == 6


def get_past_slots_for_date(target_date: date, now: datetime | None = None) -> list[str]:
    """Return canonical slots that have already started/passed for target_date in IST."""
    clinic_now = get_clinic_now(now)
    clinic_today = clinic_now.date()

    if target_date < clinic_today:
        return list(APPOINTMENT_TIME_SLOTS)

    if target_date > clinic_today:
        return []

    now_minutes = clinic_now.hour * 60 + clinic_now.minute
    return [
        label
        for label, start_minutes, _ in APPOINTMENT_SLOT_SPECS
        if start_minutes <= now_minutes
    ]


def get_slot_db_variants(slot_label: str) -> list[str]:
    """Return canonical slot plus any legacy DB variants for duplicate checking."""
    canonical = LEGACY_SLOT_ALIASES.get(slot_label, slot_label)
    if canonical in _CANONICAL_TO_VARIANTS:
        return list(_CANONICAL_TO_VARIANTS[canonical])
    return [slot_label]


def normalize_booked_slots(raw_slots) -> list[str]:
    """Normalize raw DB slot strings into canonical slot labels preserving chronological order."""
    mapped = {LEGACY_SLOT_ALIASES.get(s, s) for s in raw_slots if s}
    ordered = [slot for slot in APPOINTMENT_TIME_SLOTS if slot in mapped]
    extras = sorted(slot for slot in mapped if slot not in VALID_APPOINTMENT_SLOTS)
    return ordered + extras


def validate_appointment_date_and_slot(
    preferred_date: date,
    preferred_time: str,
    now: datetime | None = None,
) -> str | None:
    """Validate appointment date and slot against clinic IST schedule; return error text or None."""
    clinic_now = get_clinic_now(now)
    clinic_today = clinic_now.date()

    if preferred_date < clinic_today:
        return "Please select today or a future date for your appointment."

    if is_clinic_closed_day(preferred_date):
        return (
            "The clinic is closed on Sundays (Holiday). "
            "Please select a date from Monday to Saturday (8:00 AM to 8:00 PM)."
        )

    if preferred_time not in VALID_APPOINTMENT_SLOTS:
        return "Please select a valid appointment time slot within clinic hours (Monday to Saturday)."

    if preferred_time in get_past_slots_for_date(preferred_date, now=clinic_now):
        return (
            f'The time slot "{preferred_time}" has already passed for today. '
            "Please select an upcoming time slot."
        )

    return None

