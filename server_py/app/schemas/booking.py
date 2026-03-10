from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID



class BookingCreate(BaseModel):
    space_id: int = Field(..., description="ID dello spazio")
    start_at: datetime
    end_at: datetime
    subject: str | None = None
    recurring_id: str | None = None


class BookingOut(BaseModel):
    id: int
    organization_id: str
    space_id: int
    user_id: int
    start_at: datetime
    end_at: datetime
    enter_time: datetime | None = None
    leave_time: datetime | None = None
    subject: str | None = None
    recurring_id: str | None = None
    status: str
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True