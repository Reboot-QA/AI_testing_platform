"""Apifox 测试套件 · 路由（项目作用域，复用 project_access_service）。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.suite import ApifoxSuite
from app.models.user import User
from app.repositories.apifox import suite_repo as repo
from app.routers.apifox.suite_schemas import (
    SuiteBrief,
    SuiteCreate,
    SuiteOut,
    SuiteUpdate,
)
from app.services.apifox import suite_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·测试套件"])


def _suite_checked(db: Session, sid: int, user: User) -> ApifoxSuite:
    suite = repo.get_suite(db, sid)
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")
    get_accessible_project(db, suite.project_id, user)
    return suite


@router.get("/projects/{pid}/suites", response_model=List[SuiteBrief])
def list_suites(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_suites(db, pid)


@router.post("/projects/{pid}/suites", response_model=SuiteOut)
def create_suite(
    pid: int, data: SuiteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_suite(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/suites/{sid}", response_model=SuiteOut)
def get_suite(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    suite = _suite_checked(db, sid, user)
    return service.get_suite_out(db, suite)


@router.put("/suites/{sid}", response_model=SuiteOut)
def update_suite(
    sid: int, data: SuiteUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    suite = _suite_checked(db, sid, user)
    try:
        return service.update_suite(db, suite, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/suites/{sid}")
def delete_suite(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    suite = _suite_checked(db, sid, user)
    service.delete_suite(db, suite)
    return {"message": "套件已删除"}
