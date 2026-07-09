"""Apifox 脚本库 · 路由（项目作用域，复用 project_access_service）。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.script import ApifoxScript
from app.models.user import User
from app.repositories.apifox import script_repo as repo
from app.routers.apifox.script_schemas import (
    ScriptBrief,
    ScriptCreate,
    ScriptOut,
    ScriptUpdate,
)
from app.services.apifox import script_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·脚本库"])


def _script_checked(db: Session, sid: int, user: User) -> ApifoxScript:
    script = repo.get_script(db, sid)
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    get_accessible_project(db, script.project_id, user)
    return script


@router.get("/projects/{pid}/scripts", response_model=List[ScriptBrief])
def list_scripts(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_scripts(db, pid)


@router.post("/projects/{pid}/scripts", response_model=ScriptOut)
def create_script(
    pid: int, data: ScriptCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_script(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/scripts/{sid}", response_model=ScriptOut)
def get_script(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    script = _script_checked(db, sid, user)
    return service.get_script_out(script)


@router.put("/scripts/{sid}", response_model=ScriptOut)
def update_script(
    sid: int, data: ScriptUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    script = _script_checked(db, sid, user)
    try:
        return service.update_script(db, script, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/scripts/{sid}")
def delete_script(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    script = _script_checked(db, sid, user)
    try:
        service.delete_script(db, script)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "脚本已删除"}
