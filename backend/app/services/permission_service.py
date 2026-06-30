from typing import List

from sqlalchemy.orm import Session

from app.constants.menus import ALL_MENU_KEYS, DEFAULT_TESTER_MENUS, MENU_DEFINITIONS, MENU_KEY_SET
from app.models.user import User
from app.models.user_permission import UserMenuPermission

API_AUTOMATION_MENU_KEYS = [
    "api_automation_env",
    "api_automation_suites",
    "api_automation_reports",
    "api_automation_schedule",
]


def _migrate_legacy_api_automation_menu(db: Session) -> None:
    rows = (
        db.query(UserMenuPermission)
        .filter(UserMenuPermission.menu_key == "api_automation")
        .all()
    )
    if not rows:
        return
    for row in rows:
        user_id = row.user_id
        db.delete(row)
        existing = {
            item[0]
            for item in db.query(UserMenuPermission.menu_key)
            .filter(UserMenuPermission.user_id == user_id)
            .all()
        }
        for key in API_AUTOMATION_MENU_KEYS:
            if key not in existing:
                db.add(UserMenuPermission(user_id=user_id, menu_key=key))
    db.commit()


def get_user_menu_keys(db: Session, user: User) -> List[str]:
    if user.role == "admin":
        return list(ALL_MENU_KEYS)
    rows = (
        db.query(UserMenuPermission.menu_key)
        .filter(UserMenuPermission.user_id == user.id)
        .all()
    )
    return [row[0] for row in rows if row[0] in MENU_KEY_SET]


def set_user_menu_keys(db: Session, user_id: int, menu_keys: List[str]) -> List[str]:
    valid_keys = []
    seen = set()
    for key in menu_keys:
        if key in MENU_KEY_SET and key not in seen:
            valid_keys.append(key)
            seen.add(key)

    db.query(UserMenuPermission).filter(UserMenuPermission.user_id == user_id).delete()
    for key in valid_keys:
        db.add(UserMenuPermission(user_id=user_id, menu_key=key))
    db.commit()
    return valid_keys


def ensure_default_permissions(db: Session, user: User) -> None:
    if user.role == "admin":
        return
    existing = {
        row[0]
        for row in db.query(UserMenuPermission.menu_key)
        .filter(UserMenuPermission.user_id == user.id)
        .all()
    }
    target_keys = [key for key in DEFAULT_TESTER_MENUS if key not in existing]
    if not target_keys:
        return
    for key in target_keys:
        db.add(UserMenuPermission(user_id=user.id, menu_key=key))
    db.commit()


def migrate_all_user_permissions(db: Session) -> None:
    _migrate_legacy_api_automation_menu(db)
    users = db.query(User).all()
    for user in users:
        ensure_default_permissions(db, user)


def list_menu_definitions() -> List[dict]:
    return MENU_DEFINITIONS
