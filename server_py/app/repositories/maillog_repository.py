from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import MailLog


@dataclass
class MailLogBySubject:
    subject: str
    count: int


@dataclass
class MailLogByOrganization:
    organization_id: str
    count: int


class MailLogRepository:
    def create(self, db: Session, e: MailLog) -> MailLog:
        """
        Go: INSERT ... RETURNING id
        SQLAlchemy: add/commit/refresh
        """
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def log_email(self, db: Session, subject: str, recipient: str, organization_id: str = "") -> MailLog:
        """
        Go: LogEmail(subject, recipient, organizationID)
        """
        org_id = organization_id or None
        e = MailLog(
            timestamp=datetime.now(),
            subject=subject,
            recipient=recipient,
            organization_id=org_id,
        )
        return self.create(db, e)

    def get_count_by_date(self, db: Session, date: datetime) -> int:
        """
        Go: count emails between startOfDay and endOfDay (24h)
        """
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0, 0, tzinfo=date.tzinfo)
        end_of_day = start_of_day + timedelta(days=1)

        return int(
            db.query(func.count(MailLog.id))
            .filter(MailLog.timestamp >= start_of_day)
            .filter(MailLog.timestamp < end_of_day)
            .scalar()
            or 0
        )

    def get_count_by_subject_and_date(self, db: Session, date: datetime) -> list[MailLogBySubject]:
        """
        Go: SELECT subject, COUNT(id) ... GROUP BY subject ORDER BY count DESC, subject ASC
        """
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0, 0, tzinfo=date.tzinfo)
        end_of_day = start_of_day + timedelta(days=1)

        rows = (
            db.query(MailLog.subject, func.count(MailLog.id).label("count"))
            .filter(MailLog.timestamp >= start_of_day)
            .filter(MailLog.timestamp < end_of_day)
            .group_by(MailLog.subject)
            .order_by(func.count(MailLog.id).desc(), MailLog.subject.asc())
            .all()
        )
        return [MailLogBySubject(subject=r[0], count=int(r[1])) for r in rows]

    def get_count_by_organization_and_date(self, db: Session, date: datetime) -> list[MailLogByOrganization]:
        """
        Go: organization_id IS NOT NULL
        """
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0, 0, tzinfo=date.tzinfo)
        end_of_day = start_of_day + timedelta(days=1)

        rows = (
            db.query(MailLog.organization_id, func.count(MailLog.id).label("count"))
            .filter(MailLog.timestamp >= start_of_day)
            .filter(MailLog.timestamp < end_of_day)
            .filter(MailLog.organization_id.isnot(None))
            .group_by(MailLog.organization_id)
            .order_by(func.count(MailLog.id).desc(), MailLog.organization_id.asc())
            .all()
        )
        return [
            MailLogByOrganization(organization_id=str(r[0]), count=int(r[1]))
            for r in rows
        ]

    def anonymize_all(self, db: Session, organization_id: str) -> None:
        """
        Go: UPDATE mail_logs SET recipient = '' WHERE organization_id = $1
        """
        db.query(MailLog).filter(MailLog.organization_id == organization_id).update(
            {"recipient": ""},
            synchronize_session=False,
        )
        db.commit()


_mail_log_repository: MailLogRepository | None = None


def get_mail_log_repository() -> MailLogRepository:
    global _mail_log_repository
    if _mail_log_repository is None:
        _mail_log_repository = MailLogRepository()
    return _mail_log_repository