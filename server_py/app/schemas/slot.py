from pydantic import BaseModel
from datetime import datetime


class SlotOut(BaseModel):
    start_at: datetime
    end_at: datetime


class SuggestSlotsOut(BaseModel):
    space_id: int
    from_at: datetime
    to_at: datetime
    duration_minutes: int
    slots: list[SlotOut]