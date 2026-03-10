from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class SearchAttribute(BaseModel):
    attribute_id: str = Field(..., alias="attributeId")
    operator: Optional[str] = None
    value: Optional[Any] = None

    class Config:
        populate_by_name = True


class SpaceAttributeValueRequest(BaseModel):
    attribute_id: str = Field(..., alias="attributeId")
    value: str

    class Config:
        populate_by_name = True


class CreateSpaceRequest(BaseModel):
    name: str = Field(..., alias="name")
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    rotation: int = 0
    require_subject: bool = Field(True, alias="requireSubject")

    attributes: list[SpaceAttributeValueRequest] = Field(default_factory=list, alias="attributes")
    approver_group_ids: list[str] = Field(default_factory=list, alias="approverGroupIds")
    allowed_booker_group_ids: list[str] = Field(default_factory=list, alias="allowedBookerGroupIds")

    class Config:
        populate_by_name = True


class UpdateSpaceRequest(CreateSpaceRequest):
    id: str


class SpaceBulkUpdateRequest(BaseModel):
    creates: list[CreateSpaceRequest] = []
    updates: list[UpdateSpaceRequest] = []
    delete_ids: list[str] = Field(default_factory=list, alias="deleteIds")

    class Config:
        populate_by_name = True


class BulkUpdateItemResponse(BaseModel):
    id: str
    success: bool


class BulkUpdateResponse(BaseModel):
    creates: list[BulkUpdateItemResponse]
    updates: list[BulkUpdateItemResponse]
    deletes: list[BulkUpdateItemResponse]


class GetSpaceResponse(CreateSpaceRequest):
    id: str
    available: bool = False
    location_id: str = Field(..., alias="locationId")

    class Config:
        populate_by_name = True


class GetSpaceAvailabilityBookingsResponse(BaseModel):
    id: str
    recurring_id: str = Field("", alias="recurringId")
    user_id: str = Field("", alias="userId")
    user_email: str = Field("", alias="userEmail")
    enter: datetime
    leave: datetime
    subject: str = ""

    class Config:
        populate_by_name = True


class GetSpaceAvailabilityResponse(GetSpaceResponse):
    bookings: list[GetSpaceAvailabilityBookingsResponse] = []
    allowed: bool = False
    approval_required: bool = Field(False, alias="approvalRequired")

    class Config:
        populate_by_name = True