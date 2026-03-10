# server_py/app/repositories/user_repository.py

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import User


# -----------------------------
# ROLE (identici al backend Go)
# -----------------------------

USER_ROLE_USER = 0
USER_ROLE_SPACE_ADMIN = 10
USER_ROLE_ORG_ADMIN = 20
USER_ROLE_SERVICE_RO = 21
USER_ROLE_SERVICE_RW = 22
USER_ROLE_SUPER_ADMIN = 90


DEFAULT_USER_LIMIT = 10


class UserRepository:

    # -------------------------
    # CREATE
    # -------------------------

    def create(self, db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # -------------------------
    # GET ONE
    # -------------------------

    def get_one(self, db: Session, user_id: str) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    # -------------------------
    # GET BY EMAIL
    # -------------------------

    def get_by_email(self, db: Session, organization_id: str, email: str) -> User | None:
        return (
            db.query(User)
            .filter(func.lower(User.email) == (email or "").lower())
            .filter(User.organization_id == organization_id)
            .first()
        )

    # -------------------------
    # GET USERS WITH EMAIL
    # -------------------------

    def get_users_with_email(self, db: Session, email: str) -> List[User]:
        return (
            db.query(User)
            .filter(func.lower(User.email) == (email or "").lower())
            .all()
        )

    # -------------------------
    # GET ALL USERS IN ORG
    # -------------------------

    def get_all(self, db: Session, organization_id: str, limit: int = 100, offset: int = 0) -> List[User]:
        return (
            db.query(User)
            .filter(User.organization_id == organization_id)
            .order_by(User.email.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    # -------------------------
    # COUNT USERS
    # -------------------------

    def get_count(self, db: Session, organization_id: str) -> int:
        return int(
            db.query(func.count(User.id))
            .filter(User.organization_id == organization_id)
            .scalar()
            or 0
        )

    # -------------------------
    # GET ALL IDS
    # -------------------------

    def get_all_ids(self, db: Session) -> list[str]:
        rows = db.query(User.id).all()
        return [str(r[0]) for r in rows]

    # -------------------------
    # UPDATE USER
    # -------------------------

    def update(self, db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # -------------------------
    # DELETE USER
    # -------------------------

    def delete(self, db: Session, user_id: str) -> None:
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        db.commit()

    # -------------------------
    # DELETE ALL USERS IN ORG
    # -------------------------

    def delete_all(self, db: Session, organization_id: str) -> None:
        db.query(User).filter(
            User.organization_id == organization_id
        ).delete(synchronize_session=False)

        db.commit()

    # -------------------------
    # PERMISSION HELPERS
    # -------------------------

    def is_space_admin(self, user: User) -> bool:
        return int(user.role or 0) >= USER_ROLE_SPACE_ADMIN

    def is_org_admin(self, user: User) -> bool:
        return int(user.role or 0) >= USER_ROLE_ORG_ADMIN

    def is_super_admin(self, user: User) -> bool:
        return int(user.role or 0) >= USER_ROLE_SUPER_ADMIN