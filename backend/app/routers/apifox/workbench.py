"""Apifox 工作台 · 路由（跨项目只读聚合概览，作用域=当前用户可见项目）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.routers.apifox.workbench_schemas import WorkbenchOverviewOut
from app.services.apifox import workbench_service

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·工作台"])


@router.get("/workbench/overview", response_model=WorkbenchOverviewOut)
def workbench_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return workbench_service.get_overview(db, user)
