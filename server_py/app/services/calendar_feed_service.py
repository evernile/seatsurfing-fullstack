import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session

load_dotenv()

CALENDAR_FEED_SECRET = os.getenv("CALENDAR_FEED_SECRET", "")


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _fmt_ics_dt(dt: datetime) -> str:
    return _to_utc(dt).strftime("%Y%m%dT%H%M%SZ")


def _escape_ics(value: str) -> str:
    if not value:
        return ""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\n", r"\n")
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(data: bytes) -> str:
    if not CALENDAR_FEED_SECRET:
        raise RuntimeError("CALENDAR_FEED_SECRET non configurato")
    signature = hmac.new(
        CALENDAR_FEED_SECRET.encode("utf-8"),
        data,
        hashlib.sha256,
    ).digest()
    return _b64url_encode(signature)


def generate_calendar_feed_token(user_id: str) -> str:
    """
    Genera un token firmato che contiene solo user_id.
    Non richiede modifiche DB.
    """
    payload = {
        "user_id": str(user_id),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url_encode(payload_bytes)
    signature_part = _sign(payload_bytes)
    return f"{payload_part}.{signature_part}"


def validate_calendar_feed_token(token: str) -> str | None:
    """
    Ritorna user_id se il token è valido, altrimenti None.
    """
    try:
        payload_part, signature_part = token.split(".", 1)
        payload_bytes = _b64url_decode(payload_part)
        expected_signature = _sign(payload_bytes)

        if not hmac.compare_digest(signature_part, expected_signature):
            return None

        payload = json.loads(payload_bytes.decode("utf-8"))
        user_id = payload.get("user_id")
        if not user_id:
            return None

        return str(user_id)
    except Exception:
        return None


def build_user_calendar_feed(db: Session, user_id: str) -> str:
    """
    Costruisce un feed ICS con tutte le prenotazioni future/non terminate dell'utente.
    """
    rows = db.execute(
        text("""
            SELECT
                b.id,
                b.enter_time,
                b.leave_time,
                b.subject,
                s.name AS space_name,
                l.name AS location_name
            FROM bookings b
            INNER JOIN spaces s ON b.space_id = s.id
            INNER JOIN locations l ON s.location_id = l.id
            WHERE b.user_id = :user_id
              AND b.leave_time >= NOW()
            ORDER BY b.enter_time ASC
        """),
        {"user_id": str(user_id)},
    ).mappings().all()

    now_utc = datetime.now(timezone.utc)

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//SeatSurfing Python//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ics('SeatSurfing Bookings')}",
        f"X-WR-CALDESC:{_escape_ics('Prenotazioni SeatSurfing')}",
    ]

    for row in rows:
        booking_id = str(row["id"])
        start_dt = row["enter_time"]
        end_dt = row["leave_time"]
        subject = row["subject"] or ""
        space_name = row["space_name"] or "Spazio"
        location_name = row["location_name"] or "Sede"

        summary = f"{space_name}"
        if subject:
            summary = f"{space_name} - {subject}"

        description = (
            f"Prenotazione SeatSurfing\\n"
            f"Sede: {location_name}\\n"
            f"Spazio: {space_name}\\n"
            f"Oggetto: {subject or '-'}"
        )

        location = f"{location_name}, {space_name}"
        uid = f"seatsurfing-booking-{booking_id}@local"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{_fmt_ics_dt(now_utc)}",
            f"DTSTART:{_fmt_ics_dt(start_dt)}",
            f"DTEND:{_fmt_ics_dt(end_dt)}",
            f"SUMMARY:{_escape_ics(summary)}",
            f"DESCRIPTION:{_escape_ics(description)}",
            f"LOCATION:{_escape_ics(location)}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    return "\r\n".join(lines) + "\r\n"