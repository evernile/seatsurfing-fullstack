from datetime import datetime, timezone
from email.utils import format_datetime


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _fmt_ics_dt(dt: datetime) -> str:
    dt_utc = _to_utc(dt)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


def _escape_ics(value: str) -> str:
    if not value:
        return ""
    return (
        value.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\n", r"\n")
    )


def build_booking_invite_ics(
    booking_id: str,
    start_dt: datetime,
    end_dt: datetime,
    attendee_email: str,
    summary: str,
    description: str = "",
    location: str = "",
    organizer_email: str = "",
    organizer_name: str = "SeatSurfing",
) -> str:
    now_utc = datetime.now(timezone.utc)
    uid = f"seatsurfing-booking-{booking_id}@local"

    organizer_line = ""
    if organizer_email:
        organizer_line = (
            f"ORGANIZER;CN={_escape_ics(organizer_name)}:mailto:{organizer_email}\r\n"
        )

    attendee_line = ""
    if attendee_email:
        attendee_line = (
            "ATTENDEE;CN="
            f"{_escape_ics(attendee_email)}"
            ";ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:"
            f"mailto:{attendee_email}\r\n"
        )

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "PRODID:-//SeatSurfing Python//EN\r\n"
        "VERSION:2.0\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:REQUEST\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{_fmt_ics_dt(now_utc)}\r\n"
        f"DTSTART:{_fmt_ics_dt(start_dt)}\r\n"
        f"DTEND:{_fmt_ics_dt(end_dt)}\r\n"
        f"SUMMARY:{_escape_ics(summary)}\r\n"
        f"DESCRIPTION:{_escape_ics(description)}\r\n"
        f"LOCATION:{_escape_ics(location)}\r\n"
        "STATUS:CONFIRMED\r\n"
        "SEQUENCE:0\r\n"
        f"CREATED:{_fmt_ics_dt(now_utc)}\r\n"
        f"LAST-MODIFIED:{_fmt_ics_dt(now_utc)}\r\n"
        f"{organizer_line}"
        f"{attendee_line}"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return ics


def build_booking_cancel_ics(
    booking_id: str,
    start_dt: datetime,
    end_dt: datetime,
    attendee_email: str,
    summary: str,
    description: str = "",
    location: str = "",
    organizer_email: str = "",
    organizer_name: str = "SeatSurfing",
) -> str:
    now_utc = datetime.now(timezone.utc)
    uid = f"seatsurfing-booking-{booking_id}@local"

    organizer_line = ""
    if organizer_email:
        organizer_line = (
            f"ORGANIZER;CN={_escape_ics(organizer_name)}:mailto:{organizer_email}\r\n"
        )

    attendee_line = ""
    if attendee_email:
        attendee_line = (
            "ATTENDEE;CN="
            f"{_escape_ics(attendee_email)}"
            ";ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION:"
            f"mailto:{attendee_email}\r\n"
        )

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "PRODID:-//SeatSurfing Python//EN\r\n"
        "VERSION:2.0\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:CANCEL\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{_fmt_ics_dt(now_utc)}\r\n"
        f"DTSTART:{_fmt_ics_dt(start_dt)}\r\n"
        f"DTEND:{_fmt_ics_dt(end_dt)}\r\n"
        f"SUMMARY:{_escape_ics(summary)}\r\n"
        f"DESCRIPTION:{_escape_ics(description)}\r\n"
        f"LOCATION:{_escape_ics(location)}\r\n"
        "STATUS:CANCELLED\r\n"
        "SEQUENCE:1\r\n"
        f"{organizer_line}"
        f"{attendee_line}"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return ics