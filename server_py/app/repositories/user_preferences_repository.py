from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class UserPreference:
    UserID: str = ""
    Name: str = ""
    Value: str = ""


@dataclass
class PreferenceName:
    Name: str
    Type: int  


# NOTE: Type values depend on your SettingType mapping in Python.
# We keep them as ints and DO NOT change behavior here.

PreferenceEnterTime = PreferenceName(Name="enter_time", Type=0)
PreferenceWorkdayStart = PreferenceName(Name="workday_start", Type=0)
PreferenceWorkdayEnd = PreferenceName(Name="workday_end", Type=0)
PreferenceWorkdays = PreferenceName(Name="workdays", Type=0)
PreferenceLocation = PreferenceName(Name="location_id", Type=0)
PreferenceBookedColor = PreferenceName(Name="booked_color", Type=0)
PreferenceNotBookedColor = PreferenceName(Name="not_booked_color", Type=0)
PreferenceSelfBookedColor = PreferenceName(Name="self_booked_color", Type=0)
PreferencePartiallyBookedColor = PreferenceName(Name="partially_booked_color", Type=0)
PreferenceBuddyBookedColor = PreferenceName(Name="buddy_booked_color", Type=0)
PreferenceDisallowedColor = PreferenceName(Name="disallowed_color", Type=0)
PreferenceCalDAVURL = PreferenceName(Name="caldav_url", Type=0)
PreferenceCalDAVUser = PreferenceName(Name="caldav_user", Type=0)
PreferenceCalDAVPass = PreferenceName(Name="caldav_pass", Type=0)
PreferenceCalDAVPath = PreferenceName(Name="caldav_path", Type=0)
PreferenceMailNotifications = PreferenceName(Name="mail_notifications", Type=0)
PreferenceDateFormat = PreferenceName(Name="date_format", Type=0)
PreferenceApprovalNotifications = PreferenceName(Name="approval_notifications", Type=0)
Preference24HourTime = PreferenceName(Name="use_24_hour_time", Type=0)
PreferenceEnterTimeNow: int = 1
PreferenceEnterTimeNextDay: int = 2
PreferenceEnterTimeNextWorkday: int = 3


class UserPreferencesRepository:
    """
    Porting diretto di user-preferences-repository.go
    """

    def ensure_table(self, db: Session) -> None:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS users_preferences ("
                "user_id uuid NOT NULL, "
                "name VARCHAR NOT NULL, "
                "value VARCHAR NOT NULL DEFAULT '', "
                "PRIMARY KEY (user_id, name))"
            )
        )
        db.commit()

    def run_schema_upgrade(self, cur_version: int, target_version: int) -> None:
        
        return

    def set(self, db: Session, user_id: str, name: str, value: str) -> None:
        db.execute(
            text(
                "INSERT INTO users_preferences (user_id, name, value) "
                "VALUES (:user_id, :name, :value) "
                "ON CONFLICT (user_id, name) DO UPDATE SET value = :value"
            ),
            {"user_id": user_id, "name": name, "value": value},
        )
        db.commit()

    def get(self, db: Session, user_id: str, name: str) -> str:
        row = db.execute(
            text(
                "SELECT value FROM users_preferences "
                "WHERE user_id = :user_id AND name = :name"
            ),
            {"user_id": user_id, "name": name},
        ).fetchone()

        if not row:
            
            raise KeyError(f"preference not found: user_id={user_id} name={name}")

        return str(row[0])

    def get_int(self, db: Session, user_id: str, name: str) -> int:
        res = self.get(db, user_id, name)
        return int(res)

    
    def get_bool(self, db: Session, user_id: str, name: str) -> bool:
        res = self.get(db, user_id, name)
        return res == "1"

    def get_all(self, db: Session, user_id: str) -> List[UserPreference]:
        rows = db.execute(
            text(
                "SELECT user_id, name, value FROM users_preferences "
                "WHERE user_id = :user_id "
                "ORDER BY name"
            ),
            {"user_id": user_id},
        ).fetchall()

        result: List[UserPreference] = []
        for r in rows:
            e = UserPreference()
            e.UserID = str(r[0])
            e.Name = str(r[1])
            e.Value = str(r[2])
            result.append(e)

        return result

    def init_default_settings_for_user(self, db: Session, user_id: str) -> None:
        db.execute(
            text(
                "INSERT INTO users_preferences (user_id, name, value) "
                "VALUES "
                "(:user_id, 'enter_time', :enter_time), "
                "(:user_id, 'workday_start', '9'), "
                "(:user_id, 'workday_end', '17'), "
                "(:user_id, 'workdays', '1,2,3,4,5'), "
                "(:user_id, 'location_id', ''), "
                "(:user_id, 'booked_color', '#ff453a'), "
                "(:user_id, 'not_booked_color', '#30d158'), "
                "(:user_id, 'self_booked_color', '#b825de'), "
                "(:user_id, 'partially_booked_color', '#ff9100'), "
                "(:user_id, 'buddy_booked_color', '#2415c5'), "
                "(:user_id, 'disallowed_color', '#eeeeee'), "
                "(:user_id, 'approval_notifications', '0'), "
                "(:user_id, 'use_24_hour_time', '1'), "
                "(:user_id, 'date_format', 'Y-m-d') "
                "ON CONFLICT (user_id, name) DO NOTHING"
            ),
            {"user_id": user_id, "enter_time": str(PreferenceEnterTimeNow)},
        )
        db.commit()

    def init_default_settings(self, db: Session, user_ids: List[str]) -> None:
        for uid in user_ids:
            self.init_default_settings_for_user(db, uid)

    def delete_all(self, db: Session, user_id: str) -> None:
        db.execute(
            text("DELETE FROM users_preferences WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        db.commit()


_user_preferences_repository: Optional[UserPreferencesRepository] = None
_lock = threading.Lock()


def get_user_preferences_repository() -> UserPreferencesRepository:
    global _user_preferences_repository
    if _user_preferences_repository is None:
        with _lock:
            if _user_preferences_repository is None:
                _user_preferences_repository = UserPreferencesRepository()
    return _user_preferences_repository