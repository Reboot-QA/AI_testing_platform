from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models.department import Department
from app.models.project import Project
from app.models.user import User
from app.schemas import DepartmentCreate, DepartmentOut, DepartmentPermissionsOut, DepartmentPermissionsUpdate, DepartmentUpdate
from app.constants.menus import MENU_KEY_SET
from app.services.permission_service import (
    ensure_default_department_permissions,
    get_department_menu_keys,
    list_menu_definitions,
    set_department_menu_keys,
)

router = APIRouter(prefix="/departments", tags=["部门"])


def _department_out(department: Department, db: Session) -> DepartmentOut:
    user_count = db.query(User).filter(User.department_id == department.id).count()
    project_count = db.query(Project).filter(Project.department_id == department.id).count()
    return DepartmentOut(
        id=department.id,
        name=department.name,
        description=department.description,
        user_count=user_count,
        project_count=project_count,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )


@router.get("", response_model=List[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    departments = db.query(Department).order_by(Department.id.asc()).all()
    return [_department_out(item, db) for item in departments]


@router.post("", response_model=DepartmentOut)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="部门名称不能为空")
    if db.query(Department).filter(Department.name == name).first():
        raise HTTPException(status_code=400, detail="部门名称已存在")
    department = Department(name=name, description=data.description)
    db.add(department)
    db.commit()
    db.refresh(department)
    ensure_default_department_permissions(db, department.id)
    return _department_out(department, db)


@router.get("/menus", response_model=List[dict])
def list_menus(_: User = Depends(get_current_admin)):
    return list_menu_definitions()


@router.get("/{department_id}/permissions", response_model=DepartmentPermissionsOut)
def get_department_permissions(
    department_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    return DepartmentPermissionsOut(
        department_id=department.id,
        department_name=department.name,
        menu_permissions=get_department_menu_keys(db, department.id),
    )


@router.put("/{department_id}/permissions", response_model=DepartmentPermissionsOut)
def update_department_permissions(
    department_id: int,
    data: DepartmentPermissionsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    invalid = [key for key in data.menu_permissions if key not in MENU_KEY_SET]
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效菜单权限：{', '.join(invalid)}")

    keys = set_department_menu_keys(db, department.id, data.menu_permissions)
    return DepartmentPermissionsOut(
        department_id=department.id,
        department_name=department.name,
        menu_permissions=keys,
    )


@router.put("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="部门名称不能为空")
        exists = (
            db.query(Department)
            .filter(Department.name == name, Department.id != department_id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="部门名称已存在")
        department.name = name
    if data.description is not None:
        department.description = data.description
    db.commit()
    db.refresh(department)
    return _department_out(department, db)


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    user_count = db.query(User).filter(User.department_id == department_id).count()
    project_count = db.query(Project).filter(Project.department_id == department_id).count()
    if user_count or project_count:
        raise HTTPException(
            status_code=400,
            detail=f"部门下仍有 {user_count} 个用户、{project_count} 个项目，请先调整后再删除",
        )
    db.delete(department)
    db.commit()
    return {"message": "删除成功"}
