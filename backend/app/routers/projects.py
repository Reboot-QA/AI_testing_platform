from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.department import Department
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.schemas import (
    DashboardStats,
    ProjectCreate,
    ProjectMemberAddIn,
    ProjectMemberCandidateOut,
    ProjectMemberOut,
    ProjectOut,
    ProjectPageOut,
    ProjectPrefOrderIn,
    ProjectUpdate,
)
from app.services import project_member_service, user_project_pref_service
from app.services.apifox.project_cleanup import purge_project_all
from app.services.project_access_service import (
    accessible_projects_query,
    get_accessible_project,
    get_accessible_project_ids,
    is_admin,
    is_project_manager,
)

router = APIRouter(prefix="/projects", tags=["项目"])


def _project_out(project: Project, db: Session) -> ProjectOut:
    req_count = db.query(Requirement).filter(Requirement.project_id == project.id).count()
    case_count = db.query(TestCase).filter(TestCase.project_id == project.id).count()
    owner_name = project.owner.username if project.owner else ""
    if not owner_name and project.owner_id:
        owner = db.query(User).filter(User.id == project.owner_id).first()
        owner_name = owner.username if owner else ""
    department_name = project.department.name if project.department else ""
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        owner_name=owner_name,
        department_id=project.department_id,
        department_name=department_name,
        status=project.status,
        created_at=project.created_at,
        requirement_count=req_count,
        testcase_count=case_count,
    )


@router.get("", response_model=Union[List[ProjectOut], ProjectPageOut])
def list_projects(
    keyword: Optional[str] = Query(None, max_length=200),
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = accessible_projects_query(db, current_user).options(
        joinedload(Project.owner), joinedload(Project.department)
    )
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"
        owner_ids = db.query(User.id).filter(
            or_(User.username.like(like), User.full_name.like(like))
        )
        dept_ids = db.query(Department.id).filter(Department.name.like(like))
        query = query.filter(
            or_(
                Project.name.like(like),
                Project.description.like(like),
                Project.owner_id.in_(owner_ids),
                Project.department_id.in_(dept_ids),
            )
        )
    query = query.order_by(Project.id.desc())

    if page is not None:
        total = query.count()
        projects = query.offset((page - 1) * page_size).limit(page_size).all()
        return ProjectPageOut(
            items=[_project_out(p, db) for p in projects],
            total=total,
            page=page,
            page_size=page_size,
        )

    projects = query.all()
    return [_project_out(p, db) for p in projects]


@router.post("", response_model=ProjectOut)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
        department_id=current_user.department_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_out(project, db)


@router.put("/preferences/order")
def save_project_preferences(
    data: ProjectPrefOrderIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存当前用户的项目置顶 / 排序偏好（按传入展示顺序）。"""
    user_project_pref_service.save_order(db, current_user, [i.model_dump() for i in data.items])
    return {"message": "已保存"}


@router.get("/stats/dashboard", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project_ids = get_accessible_project_ids(db, current_user)
    if not project_ids:
        return DashboardStats(
            project_count=0,
            requirement_count=0,
            testcase_count=0,
            ai_generated_count=0,
            pending_review_count=0,
        )
    req_count = db.query(Requirement).filter(Requirement.project_id.in_(project_ids)).count()
    cases = db.query(TestCase).filter(TestCase.project_id.in_(project_ids)).all()
    return DashboardStats(
        project_count=len(project_ids),
        requirement_count=req_count,
        testcase_count=len(cases),
        ai_generated_count=sum(1 for c in cases if c.source == "ai_generated"),
        pending_review_count=sum(1 for c in cases if c.review_status == "pending"),
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_accessible_project(db, project_id, current_user)
    return _project_out(project, db)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_accessible_project(db, project_id, current_user)
    payload = data.model_dump(exclude_unset=True)
    new_owner_id = payload.pop("owner_id", None)
    if new_owner_id is not None and new_owner_id != project.owner_id:
        if not is_admin(current_user):
            raise HTTPException(status_code=403, detail="仅系统管理员可变更项目负责人")
        if not db.query(User).filter(User.id == new_owner_id).first():
            raise HTTPException(status_code=404, detail="指定的负责人用户不存在")
        project.owner_id = new_owner_id
    # 项目名称仅项目负责人/系统管理员可改，成员不可改名
    if "name" in payload and payload["name"] != project.name and not is_project_manager(current_user, project):
        raise HTTPException(status_code=403, detail="仅项目负责人或系统管理员可修改项目名称")
    for key, value in payload.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return _project_out(project, db)


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_accessible_project(db, project_id, current_user)
    # 硬删除不可逆且清空整个项目：仅项目负责人或系统管理员可执行
    if not (is_admin(current_user) or project.owner_id == current_user.id):
        raise HTTPException(status_code=403, detail="仅项目负责人或系统管理员可删除项目")
    purge_project_all(db, project.id)  # 级联清空该项目全部数据（老平台 + apifox），避免 FK 阻塞/孤儿
    db.delete(project)
    db.commit()
    return {"message": "删除成功"}


# ---------- 项目成员（显式授权，跨部门加人） ----------
def _manager_project(db: Session, project_id: int, user: User) -> Project:
    """管理成员需项目负责人或系统管理员。"""
    project = get_accessible_project(db, project_id, user)
    if not is_project_manager(user, project):
        raise HTTPException(status_code=403, detail="仅项目负责人或系统管理员可管理成员")
    return project


@router.get("/{project_id}/members", response_model=List[ProjectMemberOut])
def list_project_members(
    project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    get_accessible_project(db, project_id, current_user)  # 项目可见即可查看成员
    return project_member_service.list_members(db, project_id)


@router.get("/{project_id}/member-candidates", response_model=List[ProjectMemberCandidateOut])
def list_member_candidates(
    project_id: int,
    keyword: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _manager_project(db, project_id, current_user)
    return project_member_service.list_candidates(db, project_id, keyword)


@router.post("/{project_id}/members", response_model=ProjectMemberOut)
def add_project_member(
    project_id: int,
    data: ProjectMemberAddIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _manager_project(db, project_id, current_user)
    return project_member_service.add_member(db, project_id, data.user_id, current_user.id)


@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _manager_project(db, project_id, current_user)
    if not project_member_service.remove_member(db, project_id, user_id):
        raise HTTPException(status_code=404, detail="该用户不是项目成员")
    return {"message": "已移除成员"}
