from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter(prefix="/db", tags=["db"])


@router.get("/write-read")
def write_read(db: Session = Depends(get_db)):
    # WRITE
    db.execute(
        text("INSERT INTO users (email) VALUES ('test@example.com') ON CONFLICT DO NOTHING")
    )
    db.commit()

    # READ
    result = db.execute(text("SELECT COUNT(*) FROM users"))
    count = result.scalar()

    return {
        "status": "ok",
        "users_count": count
    }
