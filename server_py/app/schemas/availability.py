from pydantic import BaseModel
from datetime import datetime


class AvailabilityConflict(BaseModel):
    booking_id: int
    start_at: datetime
    end_at: datetime


class AvailabilityOut(BaseModel):
    space_id: int
    from_at: datetime
    to_at: datetime
    available: bool
    conflicts: list[AvailabilityConflict] = []