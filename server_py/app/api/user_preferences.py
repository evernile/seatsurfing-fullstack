from __future__ import annotations

import os
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, AnyUrl
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User


try:
    from app.models import UserPreference  # type: ignore
    HAS_PREF_MODEL = True
except Exception:
    UserPreference = None
    HAS_PREF_MODEL = False


router = APIRouter(prefix="/userpreferences", tags=["ui-compat"])


# Schemas 

class ListCaldavCalendarsRequest(BaseModel):
    url: AnyUrl = Field(..., alias="url")
    username: str = Field(..., min_length=1, alias="username")
    password: str = Field(..., min_length=1, alias="password")


class ListCaldavCalendarsResponse(BaseModel):
    path: str
    name: str


class SetSettingsRequest(BaseModel):
    value: str


class GetSettingsResponse(BaseModel):
    name: str
    value: str


# "Crypto" compat 

def _can_crypt() -> bool:
    return bool(os.getenv("CRYPT_KEY"))


def _encrypt_string(s: str) -> str:
    if not _can_crypt():
        raise RuntimeError("CRYPT_KEY missing")
    
    key = os.getenv("CRYPT_KEY", "")
    return f"enc::{key[:4]}::{s}"


def _decrypt_string(s: str) -> str:
    if not _can_crypt():
        raise RuntimeError("CRYPT_KEY missing")
    if s.startswith("enc::"):
        parts = s.split("::", 2)
        if len(parts) == 3:
            return parts[2]
    return s


# Preference definitions 
SETTING_TYPE_STRING = 1
SETTING_TYPE_ENCRYPTED_STRING = 2
SETTING_TYPE_BOOL = 3
SETTING_TYPE_INT = 4
SETTING_TYPE_INT_ARRAY = 5

PREF_ENTER_TIME = "enterTime"
PREF_WORKDAY_START = "workdayStart"
PREF_WORKDAY_END = "workdayEnd"
PREF_WORKDAYS = "workdays"
PREF_BOOKED_COLOR = "bookedColor"
PREF_BUDDY_BOOKED_COLOR = "buddyBookedColor"
PREF_DISALLOWED_COLOR = "disallowedColor"
PREF_SELF_BOOKED_COLOR = "selfBookedColor"
PREF_PARTIALLY_BOOKED_COLOR = "partiallyBookedColor"
PREF_NOT_BOOKED_COLOR = "notBookedColor"
PREF_LOCATION = "location"
PREF_CALDAV_URL = "caldavUrl"
PREF_CALDAV_USER = "caldavUser"
PREF_CALDAV_PASS = "caldavPass"
PREF_CALDAV_PATH = "caldavPath"
PREF_MAIL_NOTIFICATIONS = "mailNotifications"
PREF_APPROVAL_NOTIFICATIONS = "approvalNotifications"
PREF_24H_TIME = "hourTime24"
PREF_DATE_FORMAT = "dateFormat"
PREF_ENTER_TIME_NOW = 0
PREF_ENTER_TIME_NEXT_DAY = 1
PREF_ENTER_TIME_NEXT_WORKDAY = 2


_VALID_PREF_NAMES = {
    PREF_ENTER_TIME,
    PREF_WORKDAY_START,
    PREF_WORKDAY_END,
    PREF_WORKDAYS,
    PREF_BOOKED_COLOR,
    PREF_BUDDY_BOOKED_COLOR,
    PREF_DISALLOWED_COLOR,
    PREF_SELF_BOOKED_COLOR,
    PREF_PARTIALLY_BOOKED_COLOR,
    PREF_NOT_BOOKED_COLOR,
    PREF_LOCATION,
    PREF_CALDAV_URL,
    PREF_CALDAV_USER,
    PREF_CALDAV_PASS,
    PREF_CALDAV_PATH,
    PREF_MAIL_NOTIFICATIONS,
    PREF_APPROVAL_NOTIFICATIONS,
    PREF_24H_TIME,
    PREF_DATE_FORMAT,
}


def _get_pref_type(name: str) -> int:
    
    if name in {
        PREF_BOOKED_COLOR,
        PREF_BUDDY_BOOKED_COLOR,
        PREF_DISALLOWED_COLOR,
        PREF_SELF_BOOKED_COLOR,
        PREF_PARTIALLY_BOOKED_COLOR,
        PREF_NOT_BOOKED_COLOR,
        PREF_LOCATION,
        PREF_CALDAV_URL,
        PREF_CALDAV_USER,
        PREF_CALDAV_PATH,
        PREF_DATE_FORMAT,
    }:
        return SETTING_TYPE_STRING

    if name == PREF_CALDAV_PASS:
        return SETTING_TYPE_ENCRYPTED_STRING

    if name in {PREF_MAIL_NOTIFICATIONS, PREF_APPROVAL_NOTIFICATIONS, PREF_24H_TIME}:
        return SETTING_TYPE_BOOL

    if name in {PREF_ENTER_TIME, PREF_WORKDAY_START, PREF_WORKDAY_END}:
        return SETTING_TYPE_INT

    if name == PREF_WORKDAYS:
        return SETTING_TYPE_INT_ARRAY

    return 0


def _is_valid_pref_name(name: str) -> bool:
    return name in _VALID_PREF_NAMES


def _is_valid_pref_type(name: str, value: str) -> bool:
    t = _get_pref_type(name)
    if t == 0:
        return False

    if t in (SETTING_TYPE_STRING, SETTING_TYPE_ENCRYPTED_STRING):
        return True

    if t == SETTING_TYPE_BOOL:
        return value in ("1", "0")

    if t == SETTING_TYPE_INT:
        try:
            int(value)
            return True
        except Exception:
            return False

    if t == SETTING_TYPE_INT_ARRAY:
        
        if value.strip() == "":
            return True
        tokens = value.split(",")
        for token in tokens:
            token = token.strip()
            try:
                int(token)
            except Exception:
                return False
        return True

    return False


def _is_valid_pref_value(name: str, value: str) -> bool:
    
    if name == PREF_ENTER_TIME:
        try:
            i = int(value)
        except Exception:
            return False
        return i in (PREF_ENTER_TIME_NOW, PREF_ENTER_TIME_NEXT_DAY, PREF_ENTER_TIME_NEXT_WORKDAY)

    if name in (PREF_WORKDAY_START, PREF_WORKDAY_END):
        try:
            i = int(value)
        except Exception:
            return False
        return 0 <= i <= 24

    if name == PREF_WORKDAYS:
        if value.strip() == "":
            return True
        tokens = value.split(",")
        for token in tokens:
            token = token.strip()
            try:
                w = int(token)
            except Exception:
                return False
            if w < 0 or w > 6:
                return False
        return True

    if name == PREF_DATE_FORMAT:
        return value in ("Y-m-d", "d.m.Y", "m/d/Y", "d/m/Y")

    return True


_IN_MEMORY_PREFS: dict[tuple[int, str], str] = {}


def _repo_get(db: Session, user_id: int, name: str) -> str:
    if HAS_PREF_MODEL:
        row = db.query(UserPreference).filter(UserPreference.user_id == user_id, UserPreference.name == name).first()
        if not row:
            raise KeyError("not found")
        return row.value
    key = (user_id, name)
    if key not in _IN_MEMORY_PREFS:
        raise KeyError("not found")
    return _IN_MEMORY_PREFS[key]


def _repo_set(db: Session, user_id: int, name: str, value: str) -> None:
    if HAS_PREF_MODEL:
        row = db.query(UserPreference).filter(UserPreference.user_id == user_id, UserPreference.name == name).first()
        if row:
            row.value = value
        else:
            row = UserPreference(user_id=user_id, name=name, value=value)  
            db.add(row)
        db.commit()
        return
    _IN_MEMORY_PREFS[(user_id, name)] = value


def _repo_get_all(db: Session, user_id: int) -> List[GetSettingsResponse]:
    if HAS_PREF_MODEL:
        rows = db.query(UserPreference).filter(UserPreference.user_id == user_id).all()
        return [GetSettingsResponse(name=r.name, value=r.value) for r in rows]
    out: List[GetSettingsResponse] = []
    for (uid, name), value in _IN_MEMORY_PREFS.items():
        if uid == user_id:
            out.append(GetSettingsResponse(name=name, value=value))
    return out


def _copy_to_rest(name: str, value: str) -> GetSettingsResponse:
    if _get_pref_type(name) == SETTING_TYPE_ENCRYPTED_STRING:
        # decrypt for response
        try:
            return GetSettingsResponse(name=name, value=_decrypt_string(value))
        except Exception:
            
            raise HTTPException(status_code=500, detail="Crypt key missing")
    return GetSettingsResponse(name=name, value=value)


def _do_set_one(db: Session, user_id: int, name: str, value: str) -> None:
    if _get_pref_type(name) == SETTING_TYPE_ENCRYPTED_STRING:
        try:
            value = _encrypt_string(value)
        except Exception:
            raise HTTPException(status_code=500, detail="Crypt key missing")
    _repo_set(db, user_id, name, value)


@router.post("/caldav/listCalendars", response_model=list[ListCaldavCalendarsResponse])
def caldav_list_calendars(
    payload: ListCaldavCalendarsRequest,
    current_user: User = Depends(get_current_user),
):
    
    if not _can_crypt():
        raise HTTPException(status_code=500, detail="CalDAV integration requires CRYPT_KEY")

    
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/", response_model=list[GetSettingsResponse])
def get_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = _repo_get_all(db, int(current_user.id))
    res: list[GetSettingsResponse] = []
    for r in rows:
        if not _is_valid_pref_name(r.name):
            
            continue
        res.append(_copy_to_rest(r.name, r.value))
    return res


@router.put("/", status_code=200)
def set_all(
    payload: list[GetSettingsResponse],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for e in payload:
        if not _is_valid_pref_name(e.name):
            raise HTTPException(status_code=404, detail="Not found")
        if not _is_valid_pref_type(e.name, e.value):
            raise HTTPException(status_code=400, detail="Bad request")
        if not _is_valid_pref_value(e.name, e.value):
            raise HTTPException(status_code=400, detail="Bad request")
        _do_set_one(db, int(current_user.id), e.name, e.value)

    return {"status": "updated"}


@router.get("/{name}", response_model=str)
def get_preference(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_valid_pref_name(name):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        value = _repo_get(db, int(current_user.id), name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")

    
    if _get_pref_type(name) == SETTING_TYPE_ENCRYPTED_STRING:
        try:
            return _decrypt_string(value)
        except Exception:
            raise HTTPException(status_code=500, detail="Crypt key missing")
    return value


@router.put("/{name}", status_code=200)
def set_preference(
    name: str,
    payload: SetSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_valid_pref_name(name):
        raise HTTPException(status_code=404, detail="Not found")
    if not _is_valid_pref_type(name, payload.value):
        raise HTTPException(status_code=400, detail="Bad request")
    if not _is_valid_pref_value(name, payload.value):
        raise HTTPException(status_code=400, detail="Bad request")

    _do_set_one(db, int(current_user.id), name, payload.value)
    return {"status": "updated"}