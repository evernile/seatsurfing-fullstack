from fastapi import APIRouter, Depends
from zoneinfo import available_timezones

from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/setting", tags=["ui-compat"])


@router.get("/timezones")
def get_timezones(current_user: User = Depends(get_current_user)):
    return sorted(list(available_timezones()))