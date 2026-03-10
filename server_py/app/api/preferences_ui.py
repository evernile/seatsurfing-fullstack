from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/preference", tags=["ui-compat"])


class ApprovalNotificationsPayload(BaseModel):
    email: bool = False
    browser: bool = False


@router.get("")
@router.get("/")
def list_preferences(current_user: User = Depends(get_current_user)):
    return [{
        "id": "default",
        "userId": str(current_user.id),
        "organizationId": str(current_user.organization_id) if current_user.organization_id else "",
        "recurrence": {
            "weekdays": []
        }
    }]


@router.get("/approval_notifications")
def approval_notifications(current_user: User = Depends(get_current_user)):
    return {
        "email": False,
        "browser": False,
    }


@router.put("/approval_notifications")
def update_approval_notifications(
    payload: ApprovalNotificationsPayload,
    current_user: User = Depends(get_current_user),
):
    return {
        "email": payload.email,
        "browser": payload.browser,
    }