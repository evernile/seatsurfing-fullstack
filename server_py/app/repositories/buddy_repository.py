# app/repositories/buddy_repository.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import threading

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class Buddy:
    ID: str = ""
    OwnerID: str = ""
    BuddyID: str = ""


@dataclass
class BuddyDetails:
    BuddyEmail: str = ""
    ID: str = ""
    OwnerID: str = ""
    BuddyID: str = ""


class BuddyRepository:
    """
    Porting diretto di buddy-repository.go
    """

    def ensure_table(self, db: Session) -> None:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS buddies ("
                "id uuid DEFAULT uuid_generate_v4(), "
                "owner_id uuid NOT NULL, "
                "buddy_id uuid NOT NULL, "
                "PRIMARY KEY (id))"
            )
        )
        db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_buddies_owner_id ON buddies(owner_id)")
        )
        db.commit()

    def run_schema_upgrade(self, cur_version: int, target_version: int) -> None:
        # Go: No updates yet
        return

    def create(self, db: Session, e: Buddy) -> Buddy:
        row = db.execute(
            text(
                "INSERT INTO buddies (owner_id, buddy_id) "
                "VALUES (:owner_id, :buddy_id) "
                "RETURNING id"
            ),
            {"owner_id": e.OwnerID, "buddy_id": e.BuddyID},
        ).fetchone()

        db.commit()

        if row:
            e.ID = str(row[0])

        return e

    def get_one(self, db: Session, buddy_id: str) -> Optional[BuddyDetails]:
        row = db.execute(
            text(
                "SELECT buddies.id, buddies.owner_id, buddies.buddy_id, "
                "users.email "
                "FROM buddies "
                "INNER JOIN users ON buddies.buddy_id = users.id "
                "WHERE buddies.id = :id"
            ),
            {"id": buddy_id},
        ).fetchone()

        if not row:
            return None

        e = BuddyDetails()
        e.ID = str(row[0])
        e.OwnerID = str(row[1])
        e.BuddyID = str(row[2])
        e.BuddyEmail = str(row[3])
        return e

    def get_all_by_owner(self, db: Session, owner_id: str) -> List[BuddyDetails]:
        rows = db.execute(
            text(
                "SELECT buddies.id, buddies.owner_id, buddies.buddy_id, "
                "users.email "
                "FROM buddies "
                "INNER JOIN users ON buddies.buddy_id = users.id "
                "WHERE owner_id = :owner_id "
                "ORDER BY id DESC"
            ),
            {"owner_id": owner_id},
        ).fetchall()

        result: List[BuddyDetails] = []

        for r in rows:
            e = BuddyDetails()
            e.ID = str(r[0])
            e.OwnerID = str(r[1])
            e.BuddyID = str(r[2])
            e.BuddyEmail = str(r[3])
            result.append(e)

        return result

    def delete(self, db: Session, e: BuddyDetails) -> None:
        db.execute(text("DELETE FROM buddies WHERE id = :id"), {"id": e.ID})
        db.commit()


_buddy_repository: Optional[BuddyRepository] = None
_lock = threading.Lock()


def get_buddy_repository() -> BuddyRepository:
    global _buddy_repository
    if _buddy_repository is None:
        with _lock:
            if _buddy_repository is None:
                _buddy_repository = BuddyRepository()
    return _buddy_repository