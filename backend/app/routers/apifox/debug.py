"""Apifox 接口调试 · 路由（直接发一次请求，不落库）。"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.apifox import variable_repo
from app.routers.apifox.schemas import AssertionRow, CaseScriptRef, ExtractRow, RequestSpec
from app.services.apifox import debug_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·调试"])


class DebugRequest(BaseModel):
    method: str = "GET"
    path: str = ""
    server_name: Optional[str] = None
    request_spec: RequestSpec = Field(default_factory=RequestSpec)
    environment_id: Optional[int] = None
    # 接口级处理器（调试也执行；断言/提取直接用行对象，脚本按 ref 取内容）
    assertions: List[AssertionRow] = Field(default_factory=list)
    extracts: List[ExtractRow] = Field(default_factory=list)
    pre_scripts: List[CaseScriptRef] = Field(default_factory=list)
    post_scripts: List[CaseScriptRef] = Field(default_factory=list)
    # 绑定的响应模型 id（调试也做契约校验，只展示不判失败）
    response_schema_id: Optional[int] = None


class DebugResponse(BaseModel):
    method: str
    url: str
    request_headers: Dict[str, Any]
    request_body: str
    warnings: List[str] = Field(default_factory=list)
    status_code: Optional[int] = None
    response_headers: Dict[str, Any]
    response_body: str
    duration_ms: float
    error: Optional[str] = None
    assertion_results: List[Dict[str, Any]] = Field(default_factory=list)
    extract_results: List[Dict[str, Any]] = Field(default_factory=list)
    script_logs: List[str] = Field(default_factory=list)
    contract_result: Optional[Dict[str, Any]] = None


@router.post("/projects/{pid}/debug", response_model=DebugResponse)
def debug_send(
    pid: int,
    data: DebugRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    if data.environment_id:
        env = variable_repo.get_environment(db, data.environment_id)
        if not env or env.project_id != pid:
            raise HTTPException(status_code=400, detail="环境不存在或不属于该项目")
    try:
        result = debug_service.debug_send(
            db, pid, data.method, data.path,
            data.request_spec.model_dump(), data.environment_id, user.id,
            server_name=data.server_name,
            assertions=data.assertions, extracts=data.extracts,
            pre_scripts=data.pre_scripts, post_scripts=data.post_scripts,
            response_schema_id=data.response_schema_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DebugResponse(**result)
