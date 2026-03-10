from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import text
from sqlalchemy.orm import Session



@dataclass
class BookingRow:
    id: str
    user_id: str
    space_id: str
    enter_time: datetime
    leave_time: datetime
    caldav_id: str
    approved: bool
    subject: str
    recurring_id: Optional[str]
    created_at_utc: Optional[datetime]


class BookingRepository:
    # ---------- CREATE ----------
    def create(
        self,
        db: Session,
        user_id: str,
        space_id: str,
        enter_time: datetime,
        leave_time: datetime,
        caldav_id: str = "",
        approved: bool = True,
        subject: str = "",
        recurring_id: Optional[str] = None,
    ) -> str:
        """
        Replica BookingRepository.Create del Go.
        Ritorna booking_id (uuid).
        """
        now_utc = datetime.now(timezone.utc)

        booking_id = db.execute(
            text("""
                INSERT INTO bookings
                    (user_id, space_id, enter_time, leave_time, caldav_id, approved, subject, recurring_id, created_at_utc)
                VALUES
                    (:user_id, :space_id, :enter_time, :leave_time, :caldav_id, :approved, :subject, :recurring_id, :created_at_utc)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "space_id": space_id,
                "enter_time": enter_time,
                "leave_time": leave_time,
                "caldav_id": caldav_id or "",
                "approved": approved,
                "subject": subject or "",
                "recurring_id": recurring_id,
                "created_at_utc": now_utc,
            }
        ).scalar_one()

        db.commit()
        return str(booking_id)

    # ---------- GET ONE (BookingDetails) ----------
    def get_one_details(self, db: Session, booking_id: str) -> dict[str, Any] | None:
        """
        Replica BookingRepository.GetOne del Go: ritorna booking + space + location + user email.
        """
        row = db.execute(
            text("""
                SELECT
                    b.id, b.user_id, b.space_id, b.enter_time, b.leave_time, b.caldav_id, b.approved, b.subject, b.recurring_id, b.created_at_utc,
                    s.id as space_id2, s.location_id as space_location_id, s.name as space_name,
                    l.id as location_id, l.organization_id as location_org_id, l.name as location_name, l.description as location_description,
                    COALESCE(l.tz, l.timezone, '') as location_tz,
                    u.email as user_email
                FROM bookings b
                INNER JOIN spaces s ON b.space_id = s.id
                INNER JOIN locations l ON s.location_id = l.id
                INNER JOIN users u ON b.user_id = u.id
                WHERE b.id = :booking_id
            """),
            {"booking_id": booking_id}
        ).mappings().first()

        return dict(row) if row else None

    # ---------- LIST BY ORG (date range) ----------
    def list_by_org_date_range(
        self,
        db: Session,
        organization_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """
        Replica BookingRepository.GetAllByOrg del Go.
        """
        rows = db.execute(
            text("""
                SELECT
                    b.id, b.user_id, b.space_id, b.enter_time, b.leave_time, b.caldav_id, b.approved, b.subject, b.recurring_id, b.created_at_utc,
                    s.id as space_id2, s.location_id as space_location_id, s.name as space_name,
                    l.id as location_id, l.organization_id as location_org_id, l.name as location_name, l.description as location_description,
                    COALESCE(l.tz, l.timezone, '') as location_tz,
                    u.email as user_email
                FROM bookings b
                INNER JOIN spaces s ON b.space_id = s.id
                INNER JOIN locations l ON s.location_id = l.id
                INNER JOIN users u ON b.user_id = u.id
                WHERE l.organization_id = :org_id
                  AND b.enter_time >= :start_time
                  AND b.leave_time <= :end_time
                ORDER BY b.enter_time
            """),
            {"org_id": organization_id, "start_time": start_time, "end_time": end_time}
        ).mappings().all()

        return [dict(r) for r in rows]

    # ---------- LIST CURRENT BY ORG ----------
    def list_current_by_org(self, db: Session, organization_id: str) -> list[dict[str, Any]]:
        """
        Replica BookingRepository.GetAllCurrentByOrg del Go.
        """
        rows = db.execute(
            text("""
                SELECT
                    b.id, b.user_id, b.space_id, b.enter_time, b.leave_time, b.caldav_id, b.approved, b.subject, b.recurring_id, b.created_at_utc,
                    s.id as space_id2, s.location_id as space_location_id, s.name as space_name,
                    l.id as location_id, l.organization_id as location_org_id, l.name as location_name, l.description as location_description,
                    COALESCE(l.tz, l.timezone, '') as location_tz,
                    u.email as user_email
                FROM bookings b
                INNER JOIN spaces s ON b.space_id = s.id
                INNER JOIN locations l ON s.location_id = l.id
                INNER JOIN users u ON b.user_id = u.id
                WHERE l.organization_id = :org_id
                  AND b.enter_time <= NOW()
                  AND b.leave_time >= NOW()
                ORDER BY b.enter_time
            """),
            {"org_id": organization_id}
        ).mappings().all()
        return [dict(r) for r in rows]

    # ---------- FIRST UPCOMING/CURRENT BY USER ----------
    def first_upcoming_or_current_by_user(self, db: Session, user_id: str) -> dict[str, Any] | None:
        """
        Replica GetFirstUpcomingOrCurrentBookingByUserID del Go.
        """
        row = db.execute(
            text("""
                SELECT
                    b.id, b.user_id, b.space_id, b.enter_time, b.leave_time, b.caldav_id, b.approved, b.subject, b.recurring_id, b.created_at_utc,
                    s.id as space_id2, s.location_id as space_location_id, s.name as space_name,
                    l.id as location_id, l.organization_id as location_org_id, l.name as location_name, l.description as location_description,
                    COALESCE(l.tz, l.timezone, '') as location_tz,
                    u.email as user_email
                FROM bookings b
                INNER JOIN spaces s ON b.space_id = s.id
                INNER JOIN locations l ON s.location_id = l.id
                INNER JOIN users u ON b.user_id = u.id
                WHERE b.user_id = :user_id
                  AND b.leave_time > NOW()
                ORDER BY b.enter_time ASC
                LIMIT 1
            """),
            {"user_id": user_id}
        ).mappings().first()
        return dict(row) if row else None

    # ---------- CONFLICTS (space overlap) ----------
    def list_conflicts_for_space(
        self,
        db: Session,
        space_id: str,
        enter: datetime,
        leave: datetime,
        exclude_booking_id: str = "",
    ) -> list[BookingRow]:
        """
        Replica BookingRepository.GetConflicts del Go (stessa logica).
        """
        rows = db.execute(
            text("""
                SELECT id, user_id, space_id, enter_time, leave_time, caldav_id, approved, subject, recurring_id, created_at_utc
                FROM bookings
                WHERE id::text != :exclude_id
                  AND space_id = :space_id
                  AND (
                    (:enter >= enter_time AND :enter <= leave_time) OR
                    (:leave >= enter_time AND :leave <= leave_time) OR
                    (enter_time >= :enter AND enter_time <= :leave) OR
                    (leave_time >= :enter AND leave_time <= :leave)
                  )
                ORDER BY enter_time
            """),
            {"exclude_id": exclude_booking_id, "space_id": space_id, "enter": enter, "leave": leave}
        ).mappings().all()

        return [
            BookingRow(
                id=str(r["id"]),
                user_id=str(r["user_id"]),
                space_id=str(r["space_id"]),
                enter_time=r["enter_time"],
                leave_time=r["leave_time"],
                caldav_id=r["caldav_id"],
                approved=r["approved"],
                subject=r["subject"],
                recurring_id=str(r["recurring_id"]) if r["recurring_id"] else None,
                created_at_utc=r["created_at_utc"],
            )
            for r in rows
        ]

    # ---------- PENDING REQUIRING APPROVAL (approver user) ----------
    def list_requiring_approval(
        self,
        db: Session,
        approver_user_id_or_public_id: str,
    ) -> list[dict[str, Any]]:
        """
        Replica BookingRepository.GetBookingsRequiringApproval del Go.

        NOTA IMPORTANTE:
        - Nel Go: users_groups.user_id punta a users.id
        - Nel porting Python potresti avere users_groups.user_id che punta a users.public_id
        Questa query gestisce entrambi i casi:
        - se matcha users.id OK
        - se matcha users.public_id OK
        """

        rows = db.execute(
            text("""
                SELECT
                    b.id, b.user_id, b.space_id, b.enter_time, b.leave_time, b.caldav_id, b.approved, b.subject, b.recurring_id,
                    s.id as space_id2, s.location_id as space_location_id, s.name as space_name,
                    l.id as location_id, l.organization_id as location_org_id, l.name as location_name, l.description as location_description,
                    COALESCE(l.tz, l.timezone, '') as location_tz,
                    u.email as user_email
                FROM bookings b
                INNER JOIN spaces s ON b.space_id = s.id
                INNER JOIN locations l ON s.location_id = l.id
                INNER JOIN users u ON b.user_id = u.id
                WHERE b.approved = false
                  AND b.space_id IN (
                    SELECT sa.space_id
                    FROM spaces_approvers sa
                    WHERE sa.space_id = b.space_id
                      AND sa.group_id IN (
                        SELECT ug.group_id
                        FROM users_groups ug
                        WHERE ug.user_id::text = :approver_any_id
                      )
                  )
                ORDER BY b.enter_time ASC
            """),
            {"approver_any_id": str(approver_user_id_or_public_id)}
        ).mappings().all()

        return [dict(r) for r in rows]