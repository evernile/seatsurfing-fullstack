import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from icalendar import Calendar, Event

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.mail_service import send_calendar_invite
from app.services.calendar_invite_service import build_booking_invite_ics

router = APIRouter(prefix="/booking", tags=["ui-compat"])


class CreateBookingRequest(BaseModel):
    space_id: str | None = Field(default=None, alias="spaceId")
    enter: str
    leave: str
    subject: str | None = ""
    approved: bool | None = True

    class Config:
        populate_by_name = True


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _dt_to_ui(value: datetime | None) -> str | None:
    if not value:
        return None
    if getattr(value, "tzinfo", None) is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat()


def _booking_row_to_ui(row) -> dict:
    user_id = str(row["user_id"]) if row.get("user_id") is not None else ""
    user_email = row["user_email"] or ""

    location_id = str(row["location_id"]) if row.get("location_id") is not None else ""
    location_name = row["location_name"] or ""

    space_id = str(row["space_id"]) if row.get("space_id") is not None else ""
    space_name = row["space_name"] or ""

    recurring_id = ""
    if row.get("recurring_id") is not None:
        recurring_id = str(row["recurring_id"])

    return {
        "id": str(row["id"]),
        "user": {
            "id": user_id,
            "email": user_email,
        },
        "location": {
            "id": location_id,
            "name": location_name,
        },
        "space": {
            "id": space_id,
            "name": space_name,
            "locationId": location_id,
            "locationName": location_name,
            "location": {
                "id": location_id,
                "name": location_name,
            },
        },
        "userId": user_id,
        "userEmail": user_email,
        "userName": user_email,
        "locationId": location_id,
        "locationName": location_name,
        "locationLabel": location_name,
        "locationTitle": location_name,
        "locationText": location_name,
        "locationDisplay": location_name,
        "location_value": location_name,
        "area": location_name,
        "spaceId": space_id,
        "spaceName": space_name,
        "spaceLabel": space_name,
        "spaceTitle": space_name,
        "spaceText": space_name,
        "spaceDisplay": space_name,
        "space_value": space_name,
        "enter": _dt_to_ui(row["enter_time"]),
        "leave": _dt_to_ui(row["leave_time"]),
        "subject": row["subject"] or "",
        "approved": bool(row["approved"]),
        "recurringId": recurring_id,
    }


@router.get("/pendingapprovals/count")
def pending_approvals_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        return {"count": 0}

    row = db.execute(
        text("""
            SELECT COUNT(b.id) AS cnt
            FROM bookings b
            INNER JOIN spaces s ON b.space_id = s.id
            INNER JOIN locations l ON s.location_id = l.id
            WHERE l.organization_id = :org_id
              AND b.approved = false
        """),
        {"org_id": str(current_user.organization_id)},
    ).mappings().first()

    return {"count": int(row["cnt"] or 0)}


@router.get("/pendingapprovals")
@router.get("/pendingapprovals/")
def pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        return []

    rows = db.execute(
        text("""
            SELECT
                b.id,
                b.user_id,
                b.space_id,
                b.enter_time,
                b.leave_time,
                b.subject,
                b.approved,
                b.recurring_id,
                u.email AS user_email,
                s.name AS space_name,
                l.id AS location_id,
                l.name AS location_name
            FROM bookings b
            INNER JOIN users u ON b.user_id = u.id
            INNER JOIN spaces s ON b.space_id = s.id
            INNER JOIN locations l ON s.location_id = l.id
            WHERE l.organization_id = :org_id
              AND b.approved = false
            ORDER BY b.enter_time DESC
        """),
        {"org_id": str(current_user.organization_id)},
    ).mappings().all()

    return [_booking_row_to_ui(r) for r in rows]


@router.get("/report/presence")
@router.get("/report/presence/")
def report_presence(
    start: str = Query(...),
    end: str = Query(...),
    locationId: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        return {"users": [], "dates": [], "presences": []}

    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)

    if not start_dt or not end_dt:
        raise HTTPException(status_code=400, detail="Invalid start/end format")

    if end_dt < start_dt:
        raise HTTPException(status_code=400, detail="Invalid date range")

    users_rows = db.execute(
        text("""
            SELECT id, email
            FROM users
            WHERE organization_id = :org_id
            ORDER BY email
        """),
        {"org_id": str(current_user.organization_id)},
    ).mappings().all()

    start_day = datetime(start_dt.year, start_dt.month, start_dt.day)
    end_day = datetime(end_dt.year, end_dt.month, end_dt.day)

    dates: list[str] = []
    cur = start_day
    while cur < end_day:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)

    if not dates:
        return {"users": [], "dates": [], "presences": []}

    users = []
    user_ids: list[str] = []
    for row in users_rows:
        uid = str(row["id"])
        user_ids.append(uid)
        users.append(
            {
                "userId": uid,
                "email": row["email"] or "",
            }
        )

    if not user_ids:
        return {"users": [], "dates": dates, "presences": []}

    presence_map: dict[str, dict[str, int]] = {
        uid: {d: 0 for d in dates} for uid in user_ids
    }

    sql = """
        SELECT
            b.user_id,
            DATE(gs.day) AS day,
            COUNT(*)::int AS cnt
        FROM bookings b
        INNER JOIN spaces s ON b.space_id = s.id
        INNER JOIN locations l ON s.location_id = l.id
        INNER JOIN generate_series(
            DATE(:start_dt),
            DATE(:end_dt) - INTERVAL '1 day',
            INTERVAL '1 day'
        ) AS gs(day)
            ON DATE(gs.day) BETWEEN DATE(b.enter_time) AND DATE(b.leave_time)
        WHERE l.organization_id = :org_id
    """

    params = {
        "start_dt": start_dt,
        "end_dt": end_dt,
        "org_id": str(current_user.organization_id),
    }

    if locationId:
        sql += " AND l.id::text = :location_id"
        params["location_id"] = locationId

    sql += """
        GROUP BY b.user_id, DATE(gs.day)
        ORDER BY b.user_id, DATE(gs.day)
    """

    rows = db.execute(text(sql), params).mappings().all()

    valid_user_ids = set(user_ids)

    for row in rows:
        uid = str(row["user_id"])
        if uid not in valid_user_ids:
            continue

        day_val = row["day"]
        day_str = day_val.strftime("%Y-%m-%d") if hasattr(day_val, "strftime") else str(day_val)

        if day_str in presence_map[uid]:
            presence_map[uid][day_str] = int(row["cnt"] or 0)

    presences = []
    for uid in user_ids:
        presences.append([presence_map[uid][d] for d in dates])

    return {
        "users": users,
        "dates": dates,
        "presences": presences,
    }


@router.get("/filter")
@router.get("/filter/")
def filter_bookings(
    start: str = Query(...),
    end: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        return []

    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)

    if not start_dt or not end_dt:
        raise HTTPException(status_code=400, detail="Invalid start/end format")

    rows = db.execute(
        text("""
            SELECT
                b.id,
                b.user_id,
                b.space_id,
                b.enter_time,
                b.leave_time,
                b.subject,
                b.approved,
                b.recurring_id,
                u.email AS user_email,
                s.name AS space_name,
                l.id AS location_id,
                l.name AS location_name
            FROM bookings b
            INNER JOIN users u ON b.user_id = u.id
            INNER JOIN spaces s ON b.space_id = s.id
            INNER JOIN locations l ON s.location_id = l.id
            WHERE l.organization_id = :org_id
              AND b.enter_time >= :start_dt
              AND b.leave_time <= :end_dt
            ORDER BY b.enter_time DESC
        """),
        {
            "org_id": str(current_user.organization_id),
            "start_dt": start_dt,
            "end_dt": end_dt,
        },
    ).mappings().all()

    return [_booking_row_to_ui(r) for r in rows]


@router.get("/current")
@router.get("/current/")
def list_current_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        return []

    rows = db.execute(
        text("""
            SELECT
                b.id,
                b.user_id,
                b.space_id,
                b.enter_time,
                b.leave_time,
                b.subject,
                b.approved,
                b.recurring_id,
                u.email AS user_email,
                s.name AS space_name,
                l.id AS location_id,
                l.name AS location_name
            FROM bookings b
            INNER JOIN users u ON b.user_id = u.id
            INNER JOIN spaces s ON b.space_id = s.id
            INNER JOIN locations l ON s.location_id = l.id
            WHERE l.organization_id = :org_id
              AND b.enter_time <= NOW()
              AND b.leave_time >= NOW()
            ORDER BY b.enter_time DESC
        """),
        {"org_id": str(current_user.organization_id)},
    ).mappings().all()

    return [_booking_row_to_ui(r) for r in rows]


@router.get("/")
@router.get("")
def list_bookings(
    current_user: User = Depends(get_current_user),
    enter: str | None = Query(default=None),
    leave: str | None = Query(default=None),
    location: str | None = Query(default=None),
    space: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not current_user.organization_id:
        return []

    enter_dt = _parse_dt(enter)
    leave_dt = _parse_dt(leave)

    sql = """
        SELECT
            b.id,
            b.user_id,
            b.space_id,
            b.enter_time,
            b.leave_time,
            b.subject,
            b.approved,
            b.recurring_id,
            u.email AS user_email,
            s.name AS space_name,
            l.id AS location_id,
            l.name AS location_name
        FROM bookings b
        INNER JOIN users u ON b.user_id = u.id
        INNER JOIN spaces s ON b.space_id = s.id
        INNER JOIN locations l ON s.location_id = l.id
        WHERE l.organization_id = :org_id
          AND b.user_id = :user_id
    """

    params = {
        "org_id": str(current_user.organization_id),
        "user_id": str(current_user.id),
    }

    if enter_dt and leave_dt:
        sql += """
          AND b.enter_time >= :enter_dt
          AND b.leave_time <= :leave_dt
        """
        params["enter_dt"] = enter_dt
        params["leave_dt"] = leave_dt
    else:
        sql += """
          AND b.leave_time >= NOW()
        """

    if location:
        sql += " AND l.id::text = :location_id"
        params["location_id"] = location

    if space:
        sql += " AND s.id::text = :space_id"
        params["space_id"] = space

    sql += " ORDER BY b.enter_time DESC"

    rows = db.execute(text(sql), params).mappings().all()
    return [_booking_row_to_ui(r) for r in rows]


@router.get("/{booking_id}/ical")
def get_booking_ical(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.execute(
        text("""
            SELECT id, user_id, space_id, enter_time, leave_time, subject
            FROM bookings
            WHERE id = :booking_id
            LIMIT 1
        """),
        {"booking_id": booking_id},
    ).mappings().first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if str(booking["user_id"]) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    cal = Calendar()
    cal.add("prodid", "-//SeatSurfing Python//")
    cal.add("version", "2.0")

    event = Event()
    event.add("summary", "Seat Reservation")
    event.add("dtstart", booking["enter_time"])
    event.add("dtend", booking["leave_time"])
    event.add("description", booking["subject"] or "")
    event.add("uid", str(booking["id"]))

    cal.add_component(event)

    filename = f"seatsurfing-{booking['enter_time'].strftime('%Y%m%d-%H%M')}.ics"

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/{booking_id}")
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.execute(
        text("""
            SELECT
                b.id,
                b.user_id,
                b.space_id,
                b.enter_time,
                b.leave_time,
                b.subject,
                b.approved,
                b.recurring_id,
                u.email AS user_email,
                s.name AS space_name,
                l.id AS location_id,
                l.name AS location_name
            FROM bookings b
            INNER JOIN users u ON b.user_id = u.id
            INNER JOIN spaces s ON b.space_id = s.id
            INNER JOIN locations l ON s.location_id = l.id
            WHERE b.id = :booking_id
            LIMIT 1
        """),
        {"booking_id": booking_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")

    return _booking_row_to_ui(row)


@router.post("/")
@router.post("")
def create_booking(
    payload: CreateBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.space_id:
        raise HTTPException(status_code=400, detail="spaceId is required")

    try:
        enter_dt = _parse_dt(payload.enter)
        leave_dt = _parse_dt(payload.leave)

        if leave_dt and leave_dt.second == 59:
            leave_dt = leave_dt + timedelta(seconds=1)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid enter/leave format")

    if not enter_dt or not leave_dt:
        raise HTTPException(status_code=400, detail="Invalid enter/leave format")

    booking_id = str(uuid.uuid4())
    approved_value = bool(payload.approved if payload.approved is not None else True)

    db.execute(
        text("""
            INSERT INTO bookings
            (id, user_id, space_id, enter_time, leave_time, caldav_id, approved, subject, recurring_id, created_at_utc)
            VALUES
            (:id, :user_id, :space_id, :enter_time, :leave_time, :caldav_id, :approved, :subject, :recurring_id, :created_at_utc)
        """),
        {
            "id": booking_id,
            "user_id": str(current_user.id),
            "space_id": payload.space_id,
            "enter_time": enter_dt,
            "leave_time": leave_dt,
            "caldav_id": "",
            "approved": approved_value,
            "subject": payload.subject or "",
            "recurring_id": None,
            "created_at_utc": datetime.utcnow(),
        },
    )
    db.commit()

    try:
        booking_row = db.execute(
            text("""
                SELECT
                    b.id,
                    b.enter_time,
                    b.leave_time,
                    b.subject,
                    u.email AS user_email,
                    s.name AS space_name,
                    l.name AS location_name
                FROM bookings b
                INNER JOIN users u ON b.user_id = u.id
                INNER JOIN spaces s ON b.space_id = s.id
                INNER JOIN locations l ON s.location_id = l.id
                WHERE b.id = :booking_id
                LIMIT 1
            """),
            {"booking_id": booking_id},
        ).mappings().first()

        if booking_row and booking_row["user_email"]:
            subject_value = booking_row["subject"] or ""
            space_name = booking_row["space_name"] or "Spazio"
            location_name = booking_row["location_name"] or "Sede"

            mail_subject = f"Prenotazione confermata - {space_name}"
            event_summary = f"Seat reservation - {space_name}"
            event_description = (
                f"Prenotazione SeatSurfing\n"
                f"Sede: {location_name}\n"
                f"Spazio: {space_name}\n"
                f"Oggetto: {subject_value or '-'}"
            )
            event_location = f"{location_name}, {space_name}"

            ics_content = build_booking_invite_ics(
                booking_id=str(booking_row["id"]),
                start_dt=booking_row["enter_time"],
                end_dt=booking_row["leave_time"],
                attendee_email=booking_row["user_email"],
                summary=event_summary,
                description=event_description,
                location=event_location,
            )

            send_calendar_invite(
                to_email=booking_row["user_email"],
                subject=mail_subject,
                body_text=(
                    f"La tua prenotazione è stata registrata.\n\n"
                    f"Sede: {location_name}\n"
                    f"Spazio: {space_name}\n"
                    f"Inizio: {booking_row['enter_time']}\n"
                    f"Fine: {booking_row['leave_time']}\n"
                    f"Oggetto: {subject_value or '-'}\n\n"
                    f"Apri l'invito per aggiungerlo al calendario."
                ),
                ics_content=ics_content,
                filename=f"booking-{booking_id}.ics",
            )
    except Exception as e:
        print(f"Errore invio invito calendario booking {booking_id}: {e}")

    return {
        "id": booking_id,
        "userId": str(current_user.id),
        "spaceId": payload.space_id,
        "enter": _dt_to_ui(enter_dt),
        "leave": _dt_to_ui(leave_dt),
        "subject": payload.subject or "",
        "approved": approved_value,
        "recurringId": "",
    }

@router.delete("/{booking_id}")
def delete_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # verifica booking
    booking = db.execute(
        text("""
            SELECT id, user_id, enter_time
            FROM bookings
            WHERE id = :booking_id
            LIMIT 1
        """),
        {"booking_id": booking_id},
    ).mappings().first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # sicurezza: puoi cancellare solo le tue booking
    if str(booking["user_id"]) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # blocco annullamento nel passato
    if booking["enter_time"] < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete past bookings"
        )

    # DELETE
    db.execute(
        text("""
            DELETE FROM bookings
            WHERE id = :booking_id
        """),
        {"booking_id": booking_id},
    )
    db.commit()

    return {"status": "deleted"}