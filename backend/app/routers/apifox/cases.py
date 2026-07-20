"""Apifox 接口用例 · 路由（项目作用域；case→endpoint→project 归属+权限）。

与 endpoints/variables 共用 /apifox 命名空间。router 只做校验/编排，业务在 service。
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.user import User
from app.repositories.apifox import case_repo, endpoint_repo
from app.routers.apifox.case_schemas import (
    AiGenerateRequest,
    AiGenerateResult,
    CaseBrief,
    CaseCreate,
    CaseOut,
    CaseUpdate,
    ProjectCaseBrief,
)
from app.services.apifox import ai_case_service
from app.services.apifox import case_service as service
from app.services.apifox.errors import ConflictError
from app.services.project_access_service import get_accessible_project
from app.services.settings_service import get_effective_llm_config

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·用例"])


def _endpoint_checked(db: Session, eid: int, user: User) -> ApifoxEndpoint:
    endpoint = endpoint_repo.get_endpoint(db, eid)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    get_accessible_project(db, endpoint.project_id, user)
    return endpoint


def _case_checked(db: Session, cid: int, user: User) -> ApifoxEndpointCase:
    case = case_repo.get_case(db, cid)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    endpoint = endpoint_repo.get_endpoint(db, case.endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    get_accessible_project(db, endpoint.project_id, user)
    return case


@router.get("/projects/{pid}/cases", response_model=List[ProjectCaseBrief])
def list_project_cases(
    pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    return service.list_project_cases(db, pid)


@router.get("/endpoints/{eid}/cases", response_model=List[CaseBrief])
def list_cases(eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    endpoint = _endpoint_checked(db, eid, user)
    return service.list_cases(db, endpoint.id)


@router.post("/endpoints/{eid}/cases", response_model=CaseOut)
def create_case(
    eid: int, data: CaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    endpoint = _endpoint_checked(db, eid, user)
    try:
        return service.create_case(db, endpoint.project_id, endpoint.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/endpoints/{eid}/cases/ai-generate", response_model=AiGenerateResult)
async def ai_generate_cases(
    eid: int,
    data: AiGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    endpoint = _endpoint_checked(db, eid, user)
    llm_config = get_effective_llm_config(db, data.provider_id)
    try:
        cases, mode = await ai_case_service.generate_cases(db, endpoint, data.categories, llm_config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AiGenerateResult(mode=mode, cases=cases)


@router.get("/cases/{cid}", response_model=CaseOut)
def get_case(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_checked(db, cid, user)
    return service.get_case_out(db, case)


@router.post("/cases/{cid}/copy", response_model=CaseOut)
def copy_case(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_checked(db, cid, user)
    return service.copy_case(db, case)


@router.put("/cases/{cid}", response_model=CaseOut)
def update_case(
    cid: int, data: CaseUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = _case_checked(db, cid, user)
    try:
        return service.update_case(db, case, data)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/cases/{cid}")
def delete_case(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_checked(db, cid, user)
    try:
        service.delete_case(db, case)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "用例已删除"}
