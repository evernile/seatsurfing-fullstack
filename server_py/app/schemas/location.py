from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from uuid import UUID


# === Requests ===

class CreateLocationRequest(BaseModel):
    name: str = Field(..., alias="name")
    description: str = Field("", alias="description")
    max_concurrent_bookings: int = Field(0, alias="maxConcurrentBookings")
    timezone: str = Field("", alias="timezone")
    enabled: bool = Field(True, alias="enabled")
    map_scale: float = Field(1.0, alias="mapScale")

    class Config:
        populate_by_name = True


class SetSpaceAttributeValueRequest(BaseModel):
    value: str = Field(..., alias="value")

    class Config:
        populate_by_name = True


class SearchAttribute(BaseModel):
    attribute_id: str = Field(..., alias="attributeId")
    operator: Optional[str] = Field(None, alias="operator")
    value: Optional[Any] = Field(None, alias="value")

    class Config:
        populate_by_name = True


class SearchLocationRequest(BaseModel):
    enter: datetime = Field(..., alias="enter")
    leave: datetime = Field(..., alias="leave")
    attributes: list[SearchAttribute] = Field(default_factory=list, alias="attributes")

    class Config:
        populate_by_name = True


# === Responses ===

class GetLocationResponse(BaseModel):
    id: UUID
    organization_id: str = Field(..., alias="organizationId")

    map_width: int = Field(0, alias="mapWidth")
    map_height: int = Field(0, alias="mapHeight")
    map_mime_type: str = Field("", alias="mapMimeType")

    name: str
    description: str = Field("", alias="description")
    max_concurrent_bookings: int = Field(0, alias="maxConcurrentBookings")
    timezone: str = Field("", alias="timezone")
    enabled: bool = Field(True, alias="enabled")
    map_scale: float = Field(1.0, alias="mapScale")

    class Config:
        populate_by_name = True
        from_attributes = True


class GetMapResponse(BaseModel):
    width: int
    height: int
    scale: float
    mime_type: str = Field(..., alias="mimeType")
    data: str = Field(..., alias="data")  # base64

    class Config:
        populate_by_name = True


class GetSpaceAttributeValueResponse(BaseModel):
    attribute_id: str = Field(..., alias="attributeId")
    value: str = Field(..., alias="value")

    class Config:
        populate_by_name = True