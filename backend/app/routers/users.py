from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_admin, get_password_hash
from app.constants.menus import MENU_KEY_SET
from app.database import get_db
from app.models.department import Department
from app.models.project import Project
from app.models.test_execution import ManualTestRun, ManualTestRunCase
from app.models.user import User
from app.schemas import (
    MenuDefinitionOut,
    UserCreateByAdmin,
    UserOut,
    UserPasswordReset,
    UserPermissionsOut,
    UserPermissionsUpdate,
    UserUpdate,
)
from app.services.permission_service import (
    ensure_default_department_permissions,
    get_user_menu_keys,
    list_menu_definitions,
    set_user_menu_keys,
)

ALLOWED_ROLES = {"admin", "tester"}

router = APIRouter(prefix="/users", tags=["用户管理"])


def _user_out(user: User, db: Session) -> UserOut:
    department_name = user.department.name if user.department else ""
    if not department_name and user.department_id:
        department = db.query(Department).filter(Department.id == user.department_id).first()
        department_name = department.name if department else ""

    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        department_id=user.department_id,
        department_name=department_name,
        created_at=user.created_at,
        menu_permissions=get_user_menu_keys(db, user),
    )


def _validate_department_id(db: Session, department_id: Optional[int]) -> None:
    if department_id is None:
        return
    if not db.query(Department).filter(Department.id == department_id).first():
        raise HTTPException(status_code=400, detail="所选部门不存在")


@router.get("/menus", response_model=List[MenuDefinitionOut])
def list_menus(_: User = Depends(get_current_admin)):
    return list_menu_definitions()


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [_user_out(user, db) for user in users]


@router.post("", response_model=UserOut)
def create_user(
    data: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    if data.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="无效的用户角色")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if data.email and db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已存在")
    _validate_department_id(db, data.department_id)

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        role=data.role or "tester",
        department_id=data.department_id,
        hashed_password=get_password_hash(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if user.department_id:
        ensure_default_department_permissions(db, user.department_id)
    return _user_out(user, db)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if data.full_name is not None:
        user.full_name = data.full_name

    if "email" in data.model_fields_set:
        new_email = data.email
        if new_email != user.email:
            if new_email and db.query(User).filter(User.email == new_email, User.id != user_id).first():
                raise HTTPException(status_code=400, detail="邮箱已存在")
            user.email = new_email

    if data.role is not None:
        if data.role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="无效的用户角色")
        if user.id == current_admin.id and data.role != "admin":
            raise HTTPException(status_code=400, detail="不能修改自己的管理员角色")
        user.role = data.role

    if data.is_active is not None:
        if user.id == current_admin.id and not data.is_active:
            raise HTTPException(status_code=400, detail="不能禁用当前登录账号")
        user.is_active = data.is_active

    if "department_id" in data.model_fields_set:
        _validate_department_id(db, data.department_id)
        user.department_id = data.department_id

    db.commit()
    db.refresh(user)
    return _user_out(user, db)


@router.put("/{user_id}/password")
def reset_password(
    user_id: int,
    data: UserPasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.hashed_password = get_password_hash(data.password)
    user.must_change_password = True
    db.commit()
    return {"message": "密码已重置"}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")

    project_count = db.query(Project).filter(Project.owner_id == user_id).count()
    if project_count:
        raise HTTPException(
            status_code=400,
            detail=f"该用户仍拥有 {project_count} 个项目，请先删除或转移项目后再删除用户",
        )

    db.query(ManualTestRun).filter(ManualTestRun.executor_id == user_id).update(
        {ManualTestRun.executor_id: None},
        synchronize_session=False,
    )
    db.query(ManualTestRunCase).filter(ManualTestRunCase.executed_by == user_id).update(
        {ManualTestRunCase.executed_by: None},
        synchronize_session=False,
    )

    db.delete(user)
    db.commit()
    return {"message": "用户已删除"}


@router.get("/{user_id}/permissions", response_model=UserPermissionsOut)
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserPermissionsOut(
        user_id=user.id,
        username=user.username,
        role=user.role,
        menu_permissions=get_user_menu_keys(db, user),
    )


@router.put("/{user_id}/permissions", response_model=UserPermissionsOut)
def update_user_permissions(
    user_id: int,
    data: UserPermissionsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员默认拥有全部菜单权限，无需单独授权")

    invalid = [key for key in data.menu_permissions if key not in MENU_KEY_SET]
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效菜单权限：{', '.join(invalid)}")

    keys = set_user_menu_keys(db, user.id, data.menu_permissions)
    return UserPermissionsOut(
        user_id=user.id,
        username=user.username,
        role=user.role,
        menu_permissions=keys,
    )
