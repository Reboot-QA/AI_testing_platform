from typing import List

from sqlalchemy.orm import Session

from app.constants.menus import ALL_MENU_KEYS, DEFAULT_TESTER_MENUS, MENU_DEFINITIONS, MENU_KEY_SET
from app.models.department_permission import DepartmentMenuPermission
from app.models.user import User
from app.models.user_permission import UserMenuPermission

SYSTEM_MENU_KEYS = {
    "system_settings",
    "system_users",
    "system_departments",
    "system_permissions",
    "system_logs",
    "system_error_logs",
}


def get_department_menu_keys(db: Session, department_id: int) -> List[str]:
    rows = (
        db.query(DepartmentMenuPermission.menu_key)
        .filter(DepartmentMenuPermission.department_id == department_id)
        .all()
    )
    return [row[0] for row in rows if row[0] in MENU_KEY_SET]


def set_department_menu_keys(db: Session, department_id: int, menu_keys: List[str]) -> List[str]:
    valid_keys = []
    seen = set()
    for key in menu_keys:
        if key in MENU_KEY_SET and key not in seen:
            valid_keys.append(key)
            seen.add(key)

    db.query(DepartmentMenuPermission).filter(
        DepartmentMenuPermission.department_id == department_id
    ).delete()
    for key in valid_keys:
        db.add(DepartmentMenuPermission(department_id=department_id, menu_key=key))
    db.commit()
    return valid_keys


def ensure_default_department_permissions(db: Session, department_id: int) -> None:
    existing = {
        row[0]
        for row in db.query(DepartmentMenuPermission.menu_key)
        .filter(DepartmentMenuPermission.department_id == department_id)
        .all()
    }
    target_keys = [key for key in DEFAULT_TESTER_MENUS if key not in existing]
    if not target_keys:
        return
    for key in target_keys:
        db.add(DepartmentMenuPermission(department_id=department_id, menu_key=key))
    db.commit()


def get_user_menu_keys(db: Session, user: User) -> List[str]:
    if user.role == "admin":
        return list(ALL_MENU_KEYS)
    if not user.department_id:
        return []
    return get_department_menu_keys(db, user.department_id)


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
    if user.department_id:
        ensure_default_department_permissions(db, user.department_id)
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


def migrate_user_permissions_to_departments(db: Session) -> None:
    from sqlalchemy import inspect, text

    from app.database import engine
    from app.models.department import Department

    inspector = inspect(engine)
    if "department_menu_permissions" not in inspector.get_table_names():
        dialect = engine.dialect.name
        id_column = (
            "id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY"
            if dialect == "mysql"
            else "id INTEGER PRIMARY KEY"
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS department_menu_permissions ("
                    f"{id_column}, "
                    "department_id INTEGER NOT NULL, "
                    "menu_key VARCHAR(50) NOT NULL, "
                    "CONSTRAINT uq_department_menu UNIQUE (department_id, menu_key))"
                )
            )
        db.expire_all()

    departments = db.query(Department).all()
    for department in departments:
        dept_keys = set(get_department_menu_keys(db, department.id))
        users = db.query(User).filter(User.department_id == department.id).all()
        for user in users:
            if user.role == "admin":
                dept_keys.update(ALL_MENU_KEYS)
                continue
            user_keys = {
                row[0]
                for row in db.query(UserMenuPermission.menu_key)
                .filter(UserMenuPermission.user_id == user.id)
                .all()
            }
            dept_keys.update(user_keys)
        if not dept_keys:
            dept_keys.update(DEFAULT_TESTER_MENUS)
        set_department_menu_keys(db, department.id, sorted(dept_keys))

    for department in departments:
        ensure_default_department_permissions(db, department.id)


def migrate_all_user_permissions(db: Session) -> None:
    from app.models.department import Department

    migrate_user_permissions_to_departments(db)
    departments = db.query(Department).all()
    for department in departments:
        ensure_default_department_permissions(db, department.id)


def list_menu_definitions() -> List[dict]:
    return MENU_DEFINITIONS


def user_has_system_access(db: Session, user: User) -> bool:
    if user.role == "admin":
        return True
    keys = set(get_user_menu_keys(db, user))
    return bool(keys & SYSTEM_MENU_KEYS)
