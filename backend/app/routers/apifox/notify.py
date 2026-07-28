"""Apifox 失败通知配置 · 路由（项目作用域）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.apifox import notify_repo
from app.routers.apifox.notify_schemas import (
    NotifyConfigOut,
    NotifyConfigUpdate,
    NotifyTestResult,
)
from app.services.apifox import notify_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·失败通知"])


@router.get("/projects/{pid}/notify-config", response_model=NotifyConfigOut)
def get_notify_config(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    cfg = notify_repo.get_or_create(db, pid)
    db.commit()
    return notify_service.config_out(cfg)


@router.put("/projects/{pid}/notify-config", response_model=NotifyConfigOut)
def update_notify_config(
    pid: int,
    data: NotifyConfigUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    cfg = notify_service.update_config(db, pid, data)
    return notify_service.config_out(cfg)


@router.post("/projects/{pid}/notify-config/test", response_model=NotifyTestResult)
def test_notify_config(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    cfg = notify_repo.get_or_create(db, pid)
    db.commit()
    return notify_service.test_config(cfg)
