from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, Union, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Booking, RecurringBooking  
from app.repositories.space_repository import SpaceRepository


# -------------------------
# Types (Go-like)
# -------------------------

class Cadence:
    CadenceDaily: int = 1
    CadenceWeekly: int = 2


@dataclass
class CadenceDailyDetails:
    cycle: int


@dataclass
class CadenceWeeklyDetails:
    cycle: int
    weekdays: List[int]  


def _null_uuid(value: str) -> Optional[str]:
    # In Go: NullUUID(e.ID) -> tipo NullString/uuid nullable.
    # In Python: usiamo None per "NULL" DB.
    if not value:
        return None
    return value


def _go_weekday(dt: datetime) -> int:
    """
    Converte Python datetime.weekday() (Mon=0..Sun=6)
    in Go time.Weekday (Sun=0..Sat=6)
    """
    return (dt.weekday() + 1) % 7


def _add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=int(days))


# -------------------------
# Repository 
# -------------------------

class RecurringBookingRepository:
    def __init__(self) -> None:
        self._space_repo = SpaceRepository()

    def ensure_table(self, db: Session) -> None:
        
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS recurring_bookings ("
                "id uuid DEFAULT uuid_generate_v4(), "
                "user_id uuid NOT NULL, "
                "space_id uuid NOT NULL, "
                "enter_time TIMESTAMP NOT NULL, "
                "leave_time TIMESTAMP NOT NULL, "
                "subject VARCHAR NOT NULL DEFAULT '', "
                "cadence INT NOT NULL, "
                "details VARCHAR, "
                "end_date TIMESTAMP NOT NULL, "
                "PRIMARY KEY (id))"
            )
        )
        db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_recurring_bookings_user_id "
                "ON recurring_bookings(user_id)"
            )
        )
        db.commit()

    def run_schema_upgrade(self, cur_version: int, target_version: int) -> None:
        
        return

    # -------------------------
    # CRUD
    # -------------------------

    def create(self, db: Session, e: RecurringBooking) -> RecurringBooking:
        
        details_json = json.dumps(e.details) if getattr(e, "details", None) is not None else None

        # ORM insert
        e.details = details_json
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def get_one(self, db: Session, booking_id: str) -> RecurringBooking | None:
        e = db.query(RecurringBooking).filter(RecurringBooking.id == booking_id).first()
        if not e:
            return None

        raw_details = getattr(e, "details", None)
        cadence = int(getattr(e, "cadence", 0) or 0)

        
        details_bytes = (raw_details or "").encode("utf-8") if raw_details is not None else b""
        parsed = self._get_cadence_details(cadence, details_bytes)

        
        setattr(e, "details_obj", parsed)
        return e

    def delete(self, db: Session, e: RecurringBooking) -> None:
        # enter, err := GetSpaceRepository().GetNowInSpaceTimezone(e.SpaceID)
        enter = self._space_repo.get_now_in_space_timezone(db, str(e.space_id))

        # DELETE FROM bookings WHERE recurring_id = $1 AND enter_time > $2
        db.execute(
            text(
                "DELETE FROM bookings "
                "WHERE recurring_id = :rid AND enter_time > :enter_time"
            ),
            {"rid": str(e.id), "enter_time": enter},
        )

        # UPDATE bookings SET recurring_id = NULL WHERE recurring_id = $1
        db.execute(
            text("UPDATE bookings SET recurring_id = NULL WHERE recurring_id = :rid"),
            {"rid": str(e.id)},
        )

        # DELETE FROM recurring_bookings WHERE id = $1
        db.query(RecurringBooking).filter(RecurringBooking.id == e.id).delete(
            synchronize_session=False
        )
        db.commit()

    # -------------------------
    # Booking generation (Go-like)
    # -------------------------

    def create_bookings(self, e: RecurringBooking) -> list[Booking]:
        res: list[Booking] = []
        cur: datetime = e.enter_time

        cadence = int(e.cadence)

        # Recupera details (come Go: e.Details)
        details_obj = getattr(e, "details_obj", None)
        if details_obj is None:
            raw_details = getattr(e, "details", None)
            details_bytes = (raw_details or "").encode("utf-8") if raw_details is not None else b""
            details_obj = self._get_cadence_details(cadence, details_bytes)

        # for weekly cadence, ensure start is on a weekday
        if cadence == Cadence.CadenceWeekly:
            if not isinstance(details_obj, CadenceWeeklyDetails):
                # se arriva dict invece di dataclass (per sicurezza)
                details_obj = CadenceWeeklyDetails(
                    cycle=int(details_obj.get("cycle", 1)),
                    weekdays=list(details_obj.get("weekdays", [])),
                )

            weekdays = details_obj.weekdays
            if len(weekdays) == 0:
                return res

            while True:
                found = _go_weekday(cur) in weekdays
                if found:
                    break
                cur = _add_days(cur, 1)

        duration = e.leave_time - e.enter_time

        while cur < e.end_date:
            booking = Booking(
                user_id=e.user_id,
                space_id=e.space_id,
                enter_time=cur,
                leave_time=cur + duration,
                subject=e.subject,
                recurring_id=_null_uuid(str(e.id)),
            )
            res.append(booking)
            cur = self._get_next_booking_time(e, cur, details_obj)

        return res

    def _get_next_booking_time(
        self,
        e: RecurringBooking,
        current: datetime,
        details_obj: Any,
    ) -> datetime:
        cadence = int(e.cadence)

        if cadence == Cadence.CadenceDaily:
            if not isinstance(details_obj, CadenceDailyDetails):
                details_obj = CadenceDailyDetails(cycle=int(getattr(details_obj, "cycle", 1) or 1))
            return _add_days(current, details_obj.cycle)

        if cadence == Cadence.CadenceWeekly:
            if not isinstance(details_obj, CadenceWeeklyDetails):
                details_obj = CadenceWeeklyDetails(
                    cycle=int(details_obj.get("cycle", 1)),
                    weekdays=list(details_obj.get("weekdays", [])),
                )

            weekdays = details_obj.weekdays  # Go weekday ints
            cur_wd = _go_weekday(current)

            try:
                idx = weekdays.index(cur_wd)
            except ValueError:
                # Se current non è un weekday previsto, vai al prossimo giorno valido
                tmp = current
                for _ in range(14):  # safeguard
                    tmp = _add_days(tmp, 1)
                    if _go_weekday(tmp) in weekdays:
                        return tmp
                return current

            if idx == len(weekdays) - 1:
                diff = 7 - weekdays[idx] + weekdays[0]
                extra_weeks = 7 * (int(details_obj.cycle) - 1)
                return _add_days(current, int(diff) + extra_weeks)

            diff = weekdays[idx + 1] - weekdays[idx]
            return _add_days(current, int(diff))

        return datetime.min

    def _get_cadence_details(self, cadence: int, details: bytes) -> Union[CadenceDailyDetails, CadenceWeeklyDetails]:
        if cadence == Cadence.CadenceDaily:
            payload = json.loads(details.decode("utf-8") or "{}")
            return CadenceDailyDetails(cycle=int(payload.get("cycle", 1)))

        if cadence == Cadence.CadenceWeekly:
            payload = json.loads(details.decode("utf-8") or "{}")
            # weekdays devono essere Go-style ints (0..6)
            weekdays = payload.get("weekdays", [])
            if weekdays is None:
                weekdays = []
            return CadenceWeeklyDetails(
                cycle=int(payload.get("cycle", 1)),
                weekdays=[int(x) for x in list(weekdays)],
            )

        raise ValueError("unknown cadence type")


# singleton helper (Go-like GetRecurringBookingRepository)
_recurring_booking_repo: RecurringBookingRepository | None = None


def get_recurring_booking_repository() -> RecurringBookingRepository:
    global _recurring_booking_repo
    if _recurring_booking_repo is None:
        _recurring_booking_repo = RecurringBookingRepository()
    return _recurring_booking_repo