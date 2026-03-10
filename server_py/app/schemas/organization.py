from pydantic import BaseModel, Field
from uuid import UUID

class OrganizationCreate(BaseModel):
    id: str = Field(..., description="Organization ID, es: seatsurfing")
    name: str


class OrganizationOut(BaseModel):
    id: UUID
    name: str
