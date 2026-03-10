from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.models import Group, UserGroup


class GroupRepository:
    # ---------- CRUD ----------

    def create(self, db: Session, e: Group) -> Group:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def get_one(self, db: Session, group_id: str) -> Optional[Group]:
        try:
            gid = uuid.UUID(group_id)
        except Exception:
            return None
        return db.query(Group).filter(Group.id == gid).first()

    def get_all(self, db: Session, organization_id: str) -> list[Group]:
        return (
            db.query(Group)
            .filter(Group.organization_id == organization_id)
            .order_by(asc(Group.name))
            .all()
        )

    def get_all_by_ids(self, db: Session, group_ids: list[str]) -> list[Group]:
        if not group_ids:
            return []
        gids = [uuid.UUID(x) for x in group_ids]
        return (
            db.query(Group)
            .filter(Group.id.in_(gids))
            .order_by(asc(Group.name))
            .all()
        )

    def get_groups_where_user_is_member(self, db: Session, user_public_id: str) -> list[Group]:
        try:
            uid = uuid.UUID(user_public_id)
        except Exception:
            return []
        return (
            db.query(Group)
            .filter(
                Group.id.in_(
                    db.query(UserGroup.group_id).filter(UserGroup.user_id == uid)
                )
            )
            .order_by(asc(Group.name))
            .all()
        )

    def get_by_keyword(self, db: Session, organization_id: str, keyword: str) -> list[Group]:
        kw = f"%{keyword.lower()}%"
        return (
            db.query(Group)
            .filter(Group.organization_id == organization_id)
            .filter(Group.name.ilike(kw))
            .order_by(asc(Group.name))
            .all()
        )

    def groups_exist_and_belong_to_org(self, db: Session, organization_id: str, group_ids: list[str]) -> bool:
        if not group_ids:
            return True
        gids = [uuid.UUID(x) for x in group_ids]
        count = (
            db.query(Group)
            .filter(Group.id.in_(gids))
            .filter(Group.organization_id == organization_id)
            .count()
        )
        return count == len(gids)

    def update(self, db: Session, e: Group) -> Group:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def delete(self, db: Session, e: Group) -> None:
        
        db.query(UserGroup).filter(UserGroup.group_id == e.id).delete(synchronize_session=False)
        db.delete(e)
        db.commit()

    def delete_all(self, db: Session, organization_id: str) -> None:
        
        db.query(UserGroup).filter(
            UserGroup.group_id.in_(
                db.query(Group.id).filter(Group.organization_id == organization_id)
            )
        ).delete(synchronize_session=False)

        db.query(Group).filter(Group.organization_id == organization_id).delete(synchronize_session=False)
        db.commit()

    # ---------- Membership ----------

    def get_member_user_ids(self, db: Session, group_id: str) -> list[str]:
        try:
            gid = uuid.UUID(group_id)
        except Exception:
            return []
        rows = (
            db.query(UserGroup.user_id)
            .filter(UserGroup.group_id == gid)
            .order_by(asc(UserGroup.user_id))
            .all()
        )
        return [str(r[0]) for r in rows]

    def add_members(self, db: Session, group_id: str, user_public_ids: list[str]) -> None:
        gid = uuid.UUID(group_id)

        
        for uid in user_public_ids:
            db.merge(UserGroup(group_id=gid, user_id=uuid.UUID(uid)))

        db.commit()

    def remove_members(self, db: Session, group_id: str, user_public_ids: list[str]) -> None:
        gid = uuid.UUID(group_id)
        uids = [uuid.UUID(x) for x in user_public_ids]

        db.query(UserGroup).filter(
            UserGroup.group_id == gid,
            UserGroup.user_id.in_(uids),
        ).delete(synchronize_session=False)

        db.commit()

    # Utility 
    def get_user_group_ids(self, db: Session, user_public_id: str) -> set[str]:
        try:
            uid = uuid.UUID(user_public_id)
        except Exception:
            return set()
        rows = db.query(UserGroup.group_id).filter(UserGroup.user_id == uid).all()
        return {str(r[0]) for r in rows}