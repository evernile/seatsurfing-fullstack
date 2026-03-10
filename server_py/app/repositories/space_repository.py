import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_, asc
from sqlalchemy.orm import Session, joinedload

from app.models import Space, Booking, User, Location, SpaceApprover, SpaceAllowedBooker


@dataclass
class SpaceAvailabilityBookingEntry:
    booking_id: str
    recurring_id: str
    user_id: str
    user_email: str
    enter: datetime
    leave: datetime
    subject: str


@dataclass
class SpaceAvailability:
    space: Space
    available: bool
    bookings: list[SpaceAvailabilityBookingEntry]


@dataclass
class SpaceGroup:
    space_id: str
    group_id: str


class SpaceRepository:
    def create(self, db: Session, e: Space) -> Space:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    # ✅ Go: GetOne(id string) -> spaces.id
    def get_one(self, db: Session, space_id: str) -> Optional[Space]:
        try:
            sid = uuid.UUID(space_id)
        except Exception:
            return None

        return (
            db.query(Space)
            .options(joinedload(Space.location_rel))
            .filter(Space.id == sid)
            .first()
        )

    # ✅ Go: GetAll(locationID string) -> location_id
    def get_all(self, db: Session, location_id: str) -> list[Space]:
        lid = uuid.UUID(location_id)
        return (
            db.query(Space)
            .filter(Space.location_id == lid)
            .order_by(asc(Space.name))
            .all()
        )

    def update(self, db: Session, e: Space) -> Space:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    # ✅ Go: Delete elimina anche approvers/allowedbookers (space_id = spaces.id)
    def delete(self, db: Session, space: Space) -> None:
        db.query(SpaceApprover).filter(SpaceApprover.space_id == space.id).delete(synchronize_session=False)
        db.query(SpaceAllowedBooker).filter(SpaceAllowedBooker.space_id == space.id).delete(synchronize_session=False)
        db.delete(space)
        db.commit()

    # ✅ Go: GetByKeyword(organizationID, keyword) join locations
    def get_by_keyword(self, db: Session, organization_id: str, keyword: str) -> list[Space]:
        kw = f"%{keyword.lower()}%"
        return (
            db.query(Space)
            .join(Location, Location.id == Space.location_id)
            .filter(Location.organization_id == organization_id)
            .filter(Space.name.ilike(kw))
            .order_by(asc(Space.name))
            .all()
        )

    # ✅ Go: GetAllInTime(locationID, enter, leave)
    def get_all_in_time(self, db: Session, location_id: str, enter: datetime, leave: datetime) -> list[SpaceAvailability]:
        lid = uuid.UUID(location_id)

        spaces = (
            db.query(Space)
            .filter(Space.location_id == lid)
            .order_by(asc(Space.name))
            .all()
        )

        res: list[SpaceAvailability] = []

        for sp in spaces:
            # Go overlap logic (equivalente): booking overlaps [enter, leave]
            q = (
                db.query(Booking, User)
                .join(User, User.id == Booking.user_id)
                .filter(Booking.space_id == sp.id)
            )

            # Se nel DB hai is_active / status, tienili; altrimenti toglili.
            if hasattr(Booking, "is_active"):
                q = q.filter(Booking.is_active == True)

            # Preferisci campi Go-like enter_time/leave_time se esistono
            if hasattr(Booking, "enter_time") and hasattr(Booking, "leave_time"):
                q = q.filter(
                    and_(
                        Booking.enter_time < leave,
                        Booking.leave_time > enter,
                    )
                ).order_by(asc(Booking.enter_time))
            else:
                # fallback: start_at/end_at
                q = q.filter(
                    and_(
                        Booking.start_at < leave,
                        Booking.end_at > enter,
                    )
                ).order_by(asc(Booking.start_at))

            rows = q.all()

            bookings: list[SpaceAvailabilityBookingEntry] = []
            for b, u in rows:
                b_enter = getattr(b, "enter_time", None) or getattr(b, "start_at")
                b_leave = getattr(b, "leave_time", None) or getattr(b, "end_at")
                bookings.append(
                    SpaceAvailabilityBookingEntry(
                        booking_id=str(b.id),  # ✅ Go: bookings.id
                        recurring_id=str(getattr(b, "recurring_id", "") or ""),
                        user_id=str(u.id),     # ✅ Go: users.id
                        user_email=str(u.email),
                        enter=b_enter,
                        leave=b_leave,
                        subject=str(getattr(b, "subject", "") or ""),
                    )
                )

            res.append(
                SpaceAvailability(
                    space=sp,
                    available=(len(bookings) == 0),
                    bookings=bookings,
                )
            )

        return res

    # ✅ Go: GetApproverGroupIDs(spaceID)
    def get_approver_group_ids(self, db: Session, space_id: str) -> list[str]:
        try:
            sid = uuid.UUID(space_id)
        except Exception:
            return []
        rows = (
            db.query(SpaceApprover.group_id)
            .filter(SpaceApprover.space_id == sid)
            .order_by(asc(SpaceApprover.group_id))
            .all()
        )
        return [str(r[0]) for r in rows]

    def add_approvers(self, db: Session, space_id: str, group_ids: list[str]) -> None:
        if not group_ids:
            return
        sid = uuid.UUID(space_id)
        for gid in group_ids:
            db.merge(SpaceApprover(space_id=sid, group_id=uuid.UUID(gid)))
        db.commit()

    def remove_approvers(self, db: Session, space_id: str, group_ids: list[str]) -> None:
        if not group_ids:
            return
        sid = uuid.UUID(space_id)
        gids = [uuid.UUID(g) for g in group_ids]
        (
            db.query(SpaceApprover)
            .filter(SpaceApprover.space_id == sid, SpaceApprover.group_id.in_(gids))
            .delete(synchronize_session=False)
        )
        db.commit()

    def get_all_approvers_for_space_list(self, db: Session, space_ids: list[str]) -> list[SpaceGroup]:
        if not space_ids:
            return []
        sids = [uuid.UUID(s) for s in space_ids]
        rows = (
            db.query(SpaceApprover.space_id, SpaceApprover.group_id)
            .filter(SpaceApprover.space_id.in_(sids))
            .all()
        )
        return [SpaceGroup(space_id=str(a), group_id=str(b)) for a, b in rows]

    # ✅ Go: Allowed bookers mirror approvers
    def get_allowed_bookers_group_ids(self, db: Session, space_id: str) -> list[str]:
        sid = uuid.UUID(space_id)
        rows = (
            db.query(SpaceAllowedBooker.group_id)
            .filter(SpaceAllowedBooker.space_id == sid)
            .order_by(asc(SpaceAllowedBooker.group_id))
            .all()
        )
        return [str(r[0]) for r in rows]

    def add_allowed_bookers(self, db: Session, space_id: str, group_ids: list[str]) -> None:
        if not group_ids:
            return
        sid = uuid.UUID(space_id)
        for gid in group_ids:
            db.merge(SpaceAllowedBooker(space_id=sid, group_id=uuid.UUID(gid)))
        db.commit()

    def remove_allowed_bookers(self, db: Session, space_id: str, group_ids: list[str]) -> None:
        if not group_ids:
            return
        sid = uuid.UUID(space_id)
        gids = [uuid.UUID(g) for g in group_ids]
        (
            db.query(SpaceAllowedBooker)
            .filter(SpaceAllowedBooker.space_id == sid, SpaceAllowedBooker.group_id.in_(gids))
            .delete(synchronize_session=False)
        )
        db.commit()

    def get_all_allowed_bookers_for_space_list(self, db: Session, space_ids: list[str]) -> list[SpaceGroup]:
        if not space_ids:
            return []
        sids = [uuid.UUID(s) for s in space_ids]
        rows = (
            db.query(SpaceAllowedBooker.space_id, SpaceAllowedBooker.group_id)
            .filter(SpaceAllowedBooker.space_id.in_(sids))
            .all()
        )
        return [SpaceGroup(space_id=str(a), group_id=str(b)) for a, b in rows]