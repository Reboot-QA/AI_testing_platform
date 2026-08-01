"""Apifox 接口调试 · 路由（直接发一次请求，不落库）。"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.constants.limits import PATH_MAX_LEN
from app.database import get_db
from app.models.user import User
from app.repositories.apifox import variable_repo
from app.routers.apifox.schemas import AssertionRow, CaseScriptRef, ExtractRow, ProcessorRow, RequestSpec
from app.services.apifox import debug_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·调试"])


class DebugInlineScript(BaseModel):
    """内联脚本（正文直接携带，调试直发时执行，不查脚本库）。"""

    content: str = ""
    lang: str = "javascript"
    enabled: bool = True


class DebugRequest(BaseModel):
    method: str = "GET"
    path: str = Field(default="", max_length=PATH_MAX_LEN)
    server_name: Optional[str] = None
    request_spec: RequestSpec = Field(default_factory=RequestSpec)
    environment_id: Optional[int] = None
    # 接口级处理器（调试也执行；断言/提取直接用行对象，脚本按 ref 取内容）
    assertions: List[AssertionRow] = Field(default_factory=list)
    extracts: List[ExtractRow] = Field(default_factory=list)
    pre_scripts: List[CaseScriptRef] = Field(default_factory=list)
    post_scripts: List[CaseScriptRef] = Field(default_factory=list)
    # 内联脚本（正文直接携带，调试直发也执行，避免有序处理器里的内联脚本被静默丢弃）
    pre_inline: List[DebugInlineScript] = Field(default_factory=list)
    post_inline: List[DebugInlineScript] = Field(default_factory=list)
    # 有序处理器中的等待项（毫秒），调试直发也执行，避免「等待」被静默丢弃
    pre_waits: List[int] = Field(default_factory=list)
    post_waits: List[int] = Field(default_factory=list)
    # 绑定的响应模型 id（调试也做契约校验，只展示不判失败）
    response_schema_id: Optional[int] = None
    # 有序处理器（含 database / database_script；调试直发走 run_engine 管线）
    pre_processors: List[ProcessorRow] = Field(default_factory=list)
    post_processors: List[ProcessorRow] = Field(default_factory=list)
    # 开启后在控制台 Tab 打印 SQL 与查询结果
    console_print_db: bool = False


class DebugConsoleDbLog(BaseModel):
    time: str = ""
    sql: str
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    passed: bool = True
    error: Optional[str] = None


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
    console_db_logs: List[DebugConsoleDbLog] = Field(default_factory=list)
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
            pre_inline=data.pre_inline, post_inline=data.post_inline,
            pre_waits=data.pre_waits, post_waits=data.post_waits,
            response_schema_id=data.response_schema_id,
            pre_processors=data.pre_processors, post_processors=data.post_processors,
            console_print_db=data.console_print_db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DebugResponse(**result)
