from sqlalchemy.orm import Session
from app.models import DebugTimeIssueItem


class DebugTimeIssuesRepository:

    def create(self, db: Session, e: DebugTimeIssueItem) -> DebugTimeIssueItem:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def get_one(self, db: Session, id: str) -> DebugTimeIssueItem | None:
        return (
            db.query(DebugTimeIssueItem)
            .filter(DebugTimeIssueItem.id == id)
            .first()
        )

    def delete(self, db: Session, e: DebugTimeIssueItem) -> None:
        db.delete(e)
        db.commit()


_debug_time_issues_repository = None


def get_debug_time_issues_repository() -> DebugTimeIssuesRepository:
    global _debug_time_issues_repository
    if _debug_time_issues_repository is None:
        _debug_time_issues_repository = DebugTimeIssuesRepository()
    return _debug_time_issues_repository