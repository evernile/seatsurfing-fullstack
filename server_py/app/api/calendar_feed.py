from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.calendar_feed_service import (
    build_user_calendar_feed,
    generate_calendar_feed_token,
    validate_calendar_feed_token,
)

router = APIRouter(prefix="/calendar", tags=["calendar-feed"])


@router.get("/feed-link")
def get_calendar_feed_link(
    current_user: User = Depends(get_current_user),
):
    token = generate_calendar_feed_token(str(current_user.id))

    # In locale lasciamo localhost:8000.
    # Più avanti, se vuoi, si può rendere dinamico da env.
    return {
        "url": f"http://localhost:8000/calendar/feed.ics?token={token}"
    }


@router.get("/feed.ics")
def get_calendar_feed(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    user_id = validate_calendar_feed_token(token)
    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid calendar token")

    ics_content = build_user_calendar_feed(db, user_id)

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'inline; filename="seatsurfing-calendar.ics"',
            "Cache-Control": "no-cache",
        },
    )