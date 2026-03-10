import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Booking

router = APIRouter(prefix="/booking", tags=["ui-compat"])


class CreateBookingRequest(BaseModel):
    space_id: str | None = Field(default=None, alias="spaceId")
    enter: str
    leave: str
    subject: str | None = ""
    approved: bool | None = True

    class Config:
        populate_by_name = True


@router.get("/pendingapprovals/count")
def pending_approvals_count(current_user: User = Depends(get_current_user)):
    return 0


@router.get("/pendingapprovals")
def pending_approvals(current_user: User = Depends(get_current_user)):
    return []


@router.get("/report/presence")
def report_presence(
    start: str = Query(...),
    end: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {
        "users": [],
        "dates": [],
        "bookings": [],
    }


@router.get("/filter")
def filter_bookings(
    start: str = Query(...),
    end: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    bookings = db.execute(
        text("""
            SELECT id, space_id, enter_time, leave_time, subject, approved
            FROM bookings
            WHERE user_id = :user_id
            ORDER BY enter_time DESC
        """),
        {"user_id": str(current_user.id)}
    ).mappings().all()

    return [
        {
            "id": str(b["id"]),
            "spaceId": str(b["space_id"]),
            "enter": b["enter_time"].isoformat(),
            "leave": b["leave_time"].isoformat(),
            "subject": b["subject"] or "",
            "approved": bool(b["approved"]),
        }
        for b in bookings
    ]


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

    bookings = db.execute(
        text("""
            SELECT id, space_id, enter_time, leave_time, subject, approved
            FROM bookings
            WHERE user_id = :user_id
            ORDER BY enter_time DESC
        """),
        {"user_id": str(current_user.id)}
    ).mappings().all()

    return [
        {
            "id": str(b["id"]),
            "spaceId": str(b["space_id"]),
            "enter": b["enter_time"].isoformat(),
            "leave": b["leave_time"].isoformat(),
            "subject": b["subject"] or "",
            "approved": bool(b["approved"]),
        }
        for b in bookings
    ]


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
        enter_dt = datetime.fromisoformat(payload.enter.replace("Z", "+00:00"))
        leave_dt = datetime.fromisoformat(payload.leave.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid enter/leave format")

    booking_id = str(uuid.uuid4())

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
            "approved": bool(payload.approved if payload.approved is not None else True),
            "subject": payload.subject or "",
            "recurring_id": None,
            "created_at_utc": datetime.utcnow(),
        }
    )
    db.commit()

    return {
        "id": booking_id,
        "userId": str(current_user.id),
        "spaceId": payload.space_id,
        "enter": enter_dt.isoformat(),
        "leave": leave_dt.isoformat(),
        "subject": payload.subject or "",
        "approved": bool(payload.approved if payload.approved is not None else True),
    }