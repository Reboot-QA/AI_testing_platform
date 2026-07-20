"""Apifox 执行 · 路由（SSE 流式运行 + 运行记录查询）。

SSE 端点对齐旧模块范式：不用 Depends(get_db)（避免长流占用请求级连接），
鉴权用临时 session 校验后立即释放，生成器内部单开 stream_db，异常一律转 error 事件。
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import SessionLocal, get_db
from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.models.user import User
from app.repositories.apifox import (
    case_repo,
    endpoint_repo,
    run_repo,
    scenario_repo,
    suite_repo,
    variable_repo,
)
from app.routers.apifox.run_schemas import RunBrief, RunOut, RunStepOut
from app.services.apifox import run_export_service, run_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·执行"])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _sse_response(generator) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _resolve_environment(db: Session, environment_id: Optional[int], project_id: int):
    if not environment_id:
        return None
    env = variable_repo.get_environment(db, environment_id)
    if not env or env.project_id != project_id:
        raise ValueError("环境不存在或不属于该项目")
    return env


@router.post("/cases/{cid}/run/stream")
def run_case_stream(
    cid: int,
    environment_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        case = case_repo.get_case(db, cid)
        if not case:
            raise HTTPException(status_code=404, detail="用例不存在")
        get_accessible_project(db, case.project_id, current_user)
        triggered_by = current_user.username
        user_id = current_user.id
    finally:
        db.close()

    def event_generator():
        stream_db = SessionLocal()
        try:
            stream_case = case_repo.get_case(stream_db, cid)
            if not stream_case:
                yield _sse_event({"type": "error", "message": "用例不存在"})
                return
            environment = _resolve_environment(stream_db, environment_id, stream_case.project_id)
            for event in run_service.iter_case_run(
                stream_db, stream_case, environment, triggered_by, user_id
            ):
                yield _sse_event(event)
        except ValueError as exc:
            yield _sse_event({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001 - SSE 内异常必须转事件而非 500
            yield _sse_event({"type": "error", "message": f"执行失败: {exc}"})
        finally:
            stream_db.close()

    return _sse_response(event_generator())


@router.post("/scenarios/{sid}/run/stream")
def run_scenario_stream(
    sid: int,
    environment_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        scenario = scenario_repo.get_scenario(db, sid)
        if not scenario:
            raise HTTPException(status_code=404, detail="场景不存在")
        get_accessible_project(db, scenario.project_id, current_user)
        triggered_by = current_user.username
        user_id = current_user.id
    finally:
        db.close()

    def event_generator():
        stream_db = SessionLocal()
        try:
            stream_scenario = scenario_repo.get_scenario(stream_db, sid)
            if not stream_scenario:
                yield _sse_event({"type": "error", "message": "场景不存在"})
                return
            environment = _resolve_environment(stream_db, environment_id, stream_scenario.project_id)
            for event in run_service.iter_scenario_run(
                stream_db, stream_scenario, environment, triggered_by, user_id
            ):
                yield _sse_event(event)
        except ValueError as exc:
            yield _sse_event({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            yield _sse_event({"type": "error", "message": f"执行失败: {exc}"})
        finally:
            stream_db.close()

    return _sse_response(event_generator())


@router.post("/suites/{sid}/run/stream")
def run_suite_stream(
    sid: int,
    environment_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        suite = suite_repo.get_suite(db, sid)
        if not suite:
            raise HTTPException(status_code=404, detail="套件不存在")
        get_accessible_project(db, suite.project_id, current_user)
        triggered_by = current_user.username
        user_id = current_user.id
    finally:
        db.close()

    def event_generator():
        stream_db = SessionLocal()
        try:
            stream_suite = suite_repo.get_suite(stream_db, sid)
            if not stream_suite:
                yield _sse_event({"type": "error", "message": "套件不存在"})
                return
            environment = _resolve_environment(stream_db, environment_id, stream_suite.project_id)
            for event in run_service.iter_suite_run(
                stream_db, stream_suite, environment, triggered_by, user_id
            ):
                yield _sse_event(event)
        except ValueError as exc:
            yield _sse_event({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            yield _sse_event({"type": "error", "message": f"执行失败: {exc}"})
        finally:
            stream_db.close()

    return _sse_response(event_generator())


# ---------- 运行记录查询 ----------
def _loads(text: Optional[str], fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return fallback


def _brief(run: ApifoxRun) -> RunBrief:
    return RunBrief(
        id=run.id,
        parent_run_id=run.parent_run_id,
        target_type=run.target_type,
        target_id=run.target_id,
        target_name=run.target_name,
        environment_id=run.environment_id,
        status=run.status,
        total_count=run.total_count,
        passed_count=run.passed_count,
        failed_count=run.failed_count,
        pass_rate=run.pass_rate,
        duration_ms=run.duration_ms,
        triggered_by=run.triggered_by,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _step_out(step: ApifoxRunStep) -> RunStepOut:
    return RunStepOut(
        id=step.id,
        step_type=step.step_type,
        depth=step.depth,
        iteration=step.iteration,
        case_id=step.case_id,
        case_name=step.case_name,
        method=step.method,
        url=step.url,
        status=step.status,
        duration_ms=step.duration_ms,
        response_status=step.response_status,
        request_headers=_loads(step.request_headers, {}),
        request_body=step.request_body or "",
        response_headers=_loads(step.response_headers, {}),
        response_body=step.response_body or "",
        assertion_results=_loads(step.assertion_results, []),
        extract_results=_loads(step.extract_results, []),
        script_logs=_loads(step.script_logs, []),
        contract_result=_loads(step.contract_result, None),
        warnings=_loads(step.warnings, []),
        error_message=step.error_message,
    )


@router.get("/projects/{pid}/runs", response_model=List[RunBrief])
def list_runs(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return [_brief(r) for r in run_repo.list_runs(db, pid)]


@router.get("/endpoints/{eid}/runs", response_model=List[RunBrief])
def list_endpoint_runs(eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    endpoint = endpoint_repo.get_endpoint(db, eid)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    get_accessible_project(db, endpoint.project_id, user)
    return [_brief(r) for r in run_repo.list_case_runs_by_endpoint(db, eid)]


def _full_run_out(db: Session, run: ApifoxRun) -> RunOut:
    data: Dict[str, Any] = _brief(run).model_dump()
    data["steps"] = [_step_out(s) for s in run_repo.list_steps(db, run.id)]
    # 套件父运行：附子运行汇总（各用例/场景一条）供两级报告
    data["children"] = [_brief(c) for c in run_repo.list_child_runs(db, run.id)]
    data["iterations"] = _loads(run.iterations_meta, [])
    return RunOut(**data)


@router.get("/runs/{rid}", response_model=RunOut)
def get_run(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = run_repo.get_run(db, rid)
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    get_accessible_project(db, run.project_id, user)
    return _full_run_out(db, run)


@router.get("/runs/{rid}/export")
def export_run(
    rid: int,
    format: str = "excel",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出单个运行报告为 Excel / Word / PDF / JSON。"""
    run = run_repo.get_run(db, rid)
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    get_accessible_project(db, run.project_id, user)
    report = _full_run_out(db, run)
    try:
        content, media_type, ext = run_export_service.build_run_export([report], format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:  # PDF 依赖缺失等
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - docx/openpyxl 等未预期异常兜底成 500 带 detail
        raise HTTPException(status_code=500, detail=f"导出失败: {exc}")
    body = content.getvalue() if hasattr(content, "getvalue") else content
    filename = run_export_service.build_export_filename([report], ext)
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": run_export_service.build_content_disposition(filename, f"report.{ext}")},
    )
