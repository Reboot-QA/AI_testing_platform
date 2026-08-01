import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user, require_menu_permission
from app.config import settings
from app.database import SessionLocal, get_db
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.schemas import (
    AIGenerateRequest,
    AIGenerateResponse,
    BatchDeleteResponse,
    TestCaseBatchDelete,
    TestCaseBatchReviewResponse,
    TestCaseBatchReviewUpdate,
    TestCaseCreate,
    TestCaseFileImportResponse,
    TestCaseOut,
    TestCasePageOut,
    TestCaseUpdate,
)
from app.services import hub_ai_task_service
from app.services.ai_service import (
    build_generation_tasks,
    generate_testcases,
    split_generation_batches,
    stream_generate_batches,
)
from app.services.hub_ai_task_wait import hub_task_was_canceled, wait_hub_task_running
from app.services.project_access_service import get_accessible_project, get_accessible_project_ids
from app.services.requirement_io_service import summarize_import_rows
from app.services.requirement_query_helper import fetch_requirements_for_ai
from app.services.settings_service import get_effective_llm_config
from app.services.test_execution_service import delete_testcases_with_execution_cleanup
from app.services.testcase_io_service import (
    build_content_disposition,
    build_testcases_import_template_excel,
    build_testcases_import_template_xmind,
    export_testcases_excel,
    export_testcases_xmind,
    import_testcases_from_rows,
    list_project_testcases,
    next_testcase_sort_order,
    parse_testcase_import_file,
)
from app.services.testcase_query_helper import (
    apply_testcase_list_options,
    apply_testcase_list_order,
    testcase_has_sort_order_column,
    testcase_sort_order_value,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/testcases", tags=["用例"])

_HUB_CASE_TYPE_LABELS = {
    "functional": "功能测试",
    "api": "接口测试",
    "performance": "性能测试",
    "security": "安全测试",
}

AI_CASES_PER_REQUIREMENT = 3
AI_GENERATE_COUNT_MAX = 2000


def _resolve_ai_generate_count(data: AIGenerateRequest, requirement_count: int) -> int:
    if requirement_count > 0:
        return min(requirement_count * AI_CASES_PER_REQUIREMENT, AI_GENERATE_COUNT_MAX)
    return min(data.count, AI_GENERATE_COUNT_MAX)

ALLOWED_REVIEW_STATUSES = {"draft", "pending", "approved", "rejected"}
ALLOWED_TESTCASE_IMPORT_MODES = {"append", "replace"}
REVIEW_TRANSITIONS = {
    "pending": {"draft", "rejected"},
    "approved": {"pending"},
    "rejected": {"pending"},
}


def _check_project(db: Session, project_id: int, user: User) -> Project:
    return get_accessible_project(db, project_id, user)


def _prepare_ai_generate(
    db: Session,
    data: AIGenerateRequest,
    current_user: User,
) -> Dict[str, Any]:
    _check_project(db, data.project_id, current_user)

    requirement_text = data.requirement_text or ""
    requirement_ids = list(dict.fromkeys(data.requirement_ids or []))
    if data.requirement_id and data.requirement_id not in requirement_ids:
        requirement_ids.insert(0, data.requirement_id)

    selected_requirements: List[Requirement] = []
    if requirement_ids:
        selected_requirements = fetch_requirements_for_ai(
            db,
            project_id=data.project_id,
            requirement_ids=requirement_ids,
        )
        if len(selected_requirements) != len(requirement_ids):
            raise HTTPException(status_code=404, detail="部分关联需求不存在")
        not_approved = [req.title for req in selected_requirements if req.status != "approved"]
        if not_approved:
            raise HTTPException(
                status_code=400,
                detail=f"仅已评审需求可关联生成用例：{', '.join(not_approved)}",
            )
        order_map = {item.id: item for item in selected_requirements}
        selected_requirements = [order_map[item_id] for item_id in requirement_ids if item_id in order_map]
        requirement_text = "\n\n".join(
            f"【{req.title}】\n{req.description or ''}" for req in selected_requirements
        )

    if not requirement_text.strip():
        raise HTTPException(status_code=400, detail="请提供需求文本或关联需求")

    llm_config = get_effective_llm_config(db, data.provider_id)
    if data.provider_id and llm_config.get("provider_id") != data.provider_id:
        raise HTTPException(status_code=400, detail="所选模型不存在或已禁用")
    if not llm_config["mock_mode"] and not llm_config["api_key"]:
        raise HTTPException(status_code=400, detail="当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    return {
        "requirement_text": requirement_text,
        "requirement_id": selected_requirements[0].id if selected_requirements else None,
        "selected_requirements": selected_requirements,
        "llm_config": llm_config,
    }


def _testcase_out(case: TestCase, db: Session) -> TestCaseOut:
    creator_name = case.creator.username if case.creator else ""
    if not creator_name and case.created_by_id:
        creator = db.query(User).filter(User.id == case.created_by_id).first()
        creator_name = creator.username if creator else ""
    project_name = case.project.name if case.project else ""
    if not project_name:
        project = db.query(Project).filter(Project.id == case.project_id).first()
        project_name = project.name if project else ""
    return TestCaseOut(
        id=case.id,
        project_id=case.project_id,
        project_name=project_name,
        requirement_id=case.requirement_id,
        requirement_title=case.requirement.title if case.requirement else "",
        title=case.title,
        case_type=case.case_type,
        priority=case.priority,
        preconditions=case.preconditions,
        steps=case.steps,
        expected_results=case.expected_results,
        tags=case.tags,
        source=case.source,
        review_status=case.review_status,
        sort_order=testcase_sort_order_value(case),
        created_by_id=case.created_by_id,
        creator_name=creator_name,
        created_at=case.created_at,
    )


def _stage_generated_case(
    db: Session,
    *,
    project_id: int,
    requirement_id: Optional[int],
    selected_requirements: List[Requirement],
    case_type: str,
    mode: str,
    item: dict,
    created_by_id: Optional[int] = None,
) -> TestCase:
    case = TestCase(
        project_id=project_id,
        requirement_id=requirement_id,
        title=item.get("title", "未命名用例"),
        case_type=case_type,
        priority=item.get("priority", "P1"),
        preconditions=item.get("preconditions"),
        steps=item.get("steps"),
        expected_results=item.get("expected_results"),
        tags=item.get("tags"),
        source="ai_generated",
        review_status="pending",
        created_by_id=created_by_id,
        sort_order=next_testcase_sort_order(db, project_id) if testcase_has_sort_order_column() else 0,
        ai_metadata=json.dumps(
            {
                "mode": mode,
                "requirement_ids": [req.id for req in selected_requirements],
                "requirement_id": requirement_id,
            },
            ensure_ascii=False,
        ),
    )
    db.add(case)
    db.flush()
    db.refresh(case)
    return case


def _save_generated_case(
    db: Session,
    *,
    project_id: int,
    requirement_id: Optional[int],
    selected_requirements: List[Requirement],
    case_type: str,
    mode: str,
    item: dict,
    created_by_id: Optional[int] = None,
) -> TestCase:
    case = _stage_generated_case(
        db,
        project_id=project_id,
        requirement_id=requirement_id,
        selected_requirements=selected_requirements,
        case_type=case_type,
        mode=mode,
        item=item,
        created_by_id=created_by_id,
    )
    db.commit()
    db.refresh(case)
    return case


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _hub_db_call(fn):
    db = SessionLocal()
    try:
        return fn(db)
    finally:
        db.close()


def _abort_functional_hub_stream_task(
    db: Session,
    hub_task_id: int,
    *,
    saved_count: int = 0,
    error: str = "生成已中断",
) -> None:
    task = hub_ai_task_service.get_task(db, hub_task_id)
    if not task or task.status in hub_ai_task_service.HUB_TASK_TERMINAL:
        return
    if task.status == "pending":
        hub_ai_task_service.cancel_pending_hub_task(db, hub_task_id, error=error)
        return
    status = "partial" if saved_count > 0 else "failed"
    hub_ai_task_service.finish_task(
        db,
        hub_task_id,
        status=status,
        generated_total=saved_count,
        applied_total=saved_count,
        done_items=saved_count,
        error=error,
    )


def _build_generation_tasks(ctx: Dict[str, Any], total_count: int) -> List[Dict[str, Any]]:
    req_items = [
        {"id": req.id, "title": req.title, "description": req.description or ""}
        for req in ctx["selected_requirements"]
    ]
    manual_text = ctx["requirement_text"] if not req_items else ""
    return build_generation_tasks(req_items, manual_text, total_count)


ALLOWED_TESTCASE_SOURCES = frozenset({"manual", "ai_generated"})
ALLOWED_LIST_ORDERS = frozenset({"default", "created_at_desc"})


def _apply_testcase_list_order(query, order: Optional[str]):
    if order == "created_at_desc":
        return query.order_by(TestCase.created_at.desc(), TestCase.id.desc())
    return apply_testcase_list_order(query)


@router.get("", response_model=Union[List[TestCaseOut], TestCasePageOut], dependencies=[Depends(require_menu_permission("testcases"))])
def list_testcases(
    project_id: Optional[int] = Query(None),
    requirement_id: Optional[int] = Query(None),
    review_status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, max_length=200),
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible_ids = get_accessible_project_ids(db, current_user)
    if not accessible_ids:
        if page is not None:
            return TestCasePageOut(items=[], total=0, page=page, page_size=page_size)
        return []

    query = (
        db.query(TestCase)
        .options(
            joinedload(TestCase.creator),
            joinedload(TestCase.project),
            joinedload(TestCase.requirement),
        )
        .filter(TestCase.project_id.in_(accessible_ids))
    )
    query = apply_testcase_list_options(query)
    if project_id is not None:
        _check_project(db, project_id, current_user)
        query = query.filter(TestCase.project_id == project_id)
    if requirement_id:
        query = query.filter(TestCase.requirement_id == requirement_id)
    if review_status:
        query = query.filter(TestCase.review_status == review_status)
    if source:
        if source not in ALLOWED_TESTCASE_SOURCES:
            raise HTTPException(status_code=400, detail="无效的 source/order")
        query = query.filter(TestCase.source == source)
    if order:
        if order not in ALLOWED_LIST_ORDERS:
            raise HTTPException(status_code=400, detail="无效的 source/order")
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"
        query = (
            query.outerjoin(Requirement, TestCase.requirement_id == Requirement.id)
            .filter(
                or_(
                    TestCase.title.like(like),
                    TestCase.preconditions.like(like),
                    TestCase.steps.like(like),
                    TestCase.expected_results.like(like),
                    TestCase.tags.like(like),
                    Requirement.title.like(like),
                )
            )
            .distinct()
        )
    query = _apply_testcase_list_order(query, order)

    if page is not None:
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return TestCasePageOut(
            items=[_testcase_out(item, db) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    return [_testcase_out(item, db) for item in query.all()]


@router.post("", response_model=TestCaseOut, dependencies=[Depends(require_menu_permission("testcases"))])
def create_testcase(
    data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user)
    payload = data.model_dump()
    payload["created_by_id"] = current_user.id
    if testcase_has_sort_order_column():
        payload["sort_order"] = next_testcase_sort_order(db, data.project_id)
    case = TestCase(**payload)
    db.add(case)
    db.commit()
    db.refresh(case)
    return _testcase_out(case, db)


@router.post("/ai/generate", response_model=AIGenerateResponse, dependencies=[Depends(require_menu_permission("ai_generate"))])
async def ai_generate(
    data: AIGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ctx = _prepare_ai_generate(db, data, current_user)
    llm_config = ctx["llm_config"]
    generate_count = _resolve_ai_generate_count(data, len(ctx["selected_requirements"]))
    tasks = _build_generation_tasks(ctx, generate_count)

    saved: List[TestCase] = []
    mode = "mock" if llm_config["mock_mode"] else "llm"
    try:
        for task in tasks:
            cases_data, current_mode = await generate_testcases(
                task["requirement_text"],
                data.case_type,
                task["count"],
                api_base=llm_config["api_base"],
                api_key=llm_config["api_key"],
                model=llm_config["model"],
                mock_mode=llm_config["mock_mode"],
            )
            mode = current_mode
            for item in cases_data:
                saved.append(
                    _save_generated_case(
                        db,
                        project_id=data.project_id,
                        requirement_id=task["requirement_id"],
                        selected_requirements=ctx["selected_requirements"],
                        case_type=data.case_type,
                        mode=mode,
                        item=item,
                        created_by_id=current_user.id,
                    )
                )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {exc}") from exc

    return AIGenerateResponse(
        generated_count=len(saved),
        testcases=[_testcase_out(case, db) for case in saved],
        mode=mode,
        provider_name=llm_config.get("provider_name"),
        model=llm_config.get("model"),
    )


@router.post("/ai/generate/stream", dependencies=[Depends(require_menu_permission("ai_generate"))])
async def ai_generate_stream(
    data: AIGenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        ctx = _prepare_ai_generate(db, data, current_user)
    except HTTPException:
        db.close()
        raise
    except Exception as exc:
        db.close()
        logger.exception("AI 生成准备失败")
        detail = str(exc)
        lowered = detail.lower()
        if "sort_order" in lowered or "unknown column" in lowered:
            raise HTTPException(
                status_code=503,
                detail="数据库缺少 requirements.sort_order 列，请重启后端完成迁移，或联系管理员手动执行 ALTER TABLE",
            ) from exc
        raise HTTPException(status_code=500, detail=f"AI 生成准备失败: {detail}") from exc
    db.close()

    async def event_generator():
        stream_db = SessionLocal()
        saved_count = 0
        failed_by_key: Dict[str, Dict[str, Any]] = {}
        mode = "mock" if ctx["llm_config"]["mock_mode"] else "llm"
        llm_config = ctx["llm_config"]
        generate_count = _resolve_ai_generate_count(data, len(ctx["selected_requirements"]))
        tasks = _build_generation_tasks(ctx, generate_count)
        hub_task_id: Optional[int] = None
        task_finished = False
        worker_active = False
        sel = ctx["selected_requirements"]
        target_label = f"{len(sel)} 个需求" if sel else "手动输入需求"
        category_label = _HUB_CASE_TYPE_LABELS.get(data.case_type, data.case_type)
        llm_slot_key = hub_ai_task_service.llm_slot_key_from_config(llm_config)

        try:
            try:
                hub_task = hub_ai_task_service.create_running_task(
                    stream_db,
                    project_id=data.project_id,
                    task_type="functional",
                    created_by=current_user.id,
                    target=target_label,
                    category_label=category_label,
                    total_items=generate_count,
                    provider_id=llm_config.get("provider_id"),
                    meta={
                        "provider_id": llm_config.get("provider_id"),
                        "model": llm_config.get("model"),
                        "provider_name": llm_config.get("provider_name"),
                        "llm_slot_key": llm_slot_key,
                    },
                )
            except hub_ai_task_service.HubTaskCapacityError as exc:
                yield _sse_event({"type": "error", "message": exc.message})
                return

            hub_task_id = hub_task.id
            if hub_task.status == "pending":
                yield _sse_event(
                    {
                        "type": "status",
                        "message": "排队中，等待使用同一模型的其他 AI 用例生成任务完成…",
                        "queued": True,
                        "current": 0,
                        "total": generate_count,
                        "hub_task_id": hub_task_id,
                    }
                )
                slot_status = await wait_hub_task_running(
                    _hub_db_call,
                    hub_task_id,
                    is_disconnected=request.is_disconnected,
                )
                if slot_status != "running":
                    err = (
                        "排队任务已取消"
                        if slot_status == "canceled"
                        else "排队任务未能启动，请稍后重试"
                    )
                    _abort_functional_hub_stream_task(stream_db, hub_task_id, error=err)
                    task_finished = True
                    yield _sse_event({"type": "error", "message": err})
                    return

            if not tasks:
                hub_ai_task_service.finish_task(
                    stream_db,
                    hub_task_id,
                    status="failed",
                    error="没有可生成的需求任务，请检查关联需求",
                )
                task_finished = True
                yield _sse_event({"type": "error", "message": "没有可生成的需求任务，请检查关联需求"})
                return

            batch_call_count = sum(
                len(split_generation_batches(task["count"], settings.ai_generate_batch_size))
                for task in tasks
            )
            yield _sse_event(
                {
                    "type": "status",
                    "message": (
                        f"正在调用大模型：{len(tasks)} 个需求，"
                        f"{batch_call_count} 批请求（并发 {settings.ai_generate_concurrency}）..."
                    ),
                    "current": 0,
                    "total": generate_count,
                    "hub_task_id": hub_task_id,
                }
            )

            hub_ai_task_service.set_hub_parse_worker_active(stream_db, hub_task_id, True)
            worker_active = True

            async for cases_data, batch_mode, batch_index, batch_total, requirement_id, label, task_error in stream_generate_batches(
                tasks,
                data.case_type,
                api_base=llm_config["api_base"],
                api_key=llm_config["api_key"],
                model=llm_config["model"],
                mock_mode=llm_config["mock_mode"],
                batch_size=settings.ai_generate_batch_size,
                concurrency=settings.ai_generate_concurrency,
            ):
                if hub_task_id and await hub_task_was_canceled(_hub_db_call, hub_task_id):
                    _abort_functional_hub_stream_task(
                        stream_db,
                        hub_task_id,
                        saved_count=saved_count,
                        error="任务已取消",
                    )
                    task_finished = True
                    return
                mode = batch_mode
                if task_error:
                    fail_key = str(requirement_id) if requirement_id is not None else f"manual:{label}"
                    if fail_key not in failed_by_key:
                        failed_item = {
                            "requirement_id": requirement_id,
                            "title": label,
                            "reason": task_error,
                        }
                        failed_by_key[fail_key] = failed_item
                        yield _sse_event({"type": "task_failed", **failed_item})
                    yield _sse_event(
                        {
                            "type": "status",
                            "message": f"「{label}」生成失败，已跳过（{batch_index}/{batch_total}）",
                            "current": saved_count,
                            "total": generate_count,
                        }
                    )
                    continue

                yield _sse_event(
                    {
                        "type": "status",
                        "message": f"正在为「{label}」生成用例（{batch_index}/{batch_total} 批）...",
                        "current": saved_count,
                        "total": generate_count,
                    }
                )

                for item in cases_data:
                    case = _stage_generated_case(
                        stream_db,
                        project_id=data.project_id,
                        requirement_id=requirement_id,
                        selected_requirements=ctx["selected_requirements"],
                        case_type=data.case_type,
                        mode=mode,
                        item=item,
                        created_by_id=current_user.id,
                    )
                    stream_db.flush()
                    stream_db.refresh(case)
                    saved_count += 1
                    hub_ai_task_service.record_functional_case_progress(
                        stream_db,
                        hub_task_id,
                        sort_order=saved_count,
                        testcase_id=case.id,
                        done_items=saved_count,
                        generated_total=saved_count,
                        total_items=generate_count,
                    )
                    yield _sse_event(
                        {
                            "type": "case",
                            "data": _testcase_out(case, stream_db).model_dump(mode="json"),
                            "current": saved_count,
                            "total": generate_count,
                            "saved": True,
                        }
                    )
                stream_db.commit()

            if hub_task_id and await hub_task_was_canceled(_hub_db_call, hub_task_id):
                _abort_functional_hub_stream_task(
                    stream_db,
                    hub_task_id,
                    saved_count=saved_count,
                    error="任务已取消",
                )
                task_finished = True
                return

            failed_tasks = list(failed_by_key.values())
            if saved_count == 0:
                detail = (
                    f"{failed_tasks[0]['title']}：{failed_tasks[0]['reason']}"
                    if len(failed_tasks) == 1
                    else "；".join(f"{item['title']}：{item['reason']}" for item in failed_tasks[:3])
                )
                if len(failed_tasks) > 3:
                    detail += f" 等 {len(failed_tasks)} 项"
                raise ValueError(detail or "未生成任何用例，请检查 API Key 或开启 Mock 模式")

            message = f"成功生成 {saved_count} 条用例，已实时写入用例库"
            if failed_tasks:
                message += f"，{len(failed_tasks)} 个需求生成失败已跳过"

            final_status = "partial" if failed_tasks else "succeeded"
            hub_ai_task_service.finish_task(
                stream_db,
                hub_task_id,
                status=final_status,
                generated_total=saved_count,
                applied_total=saved_count,
                done_items=saved_count,
                total_items=generate_count,
                meta={
                    "mode": mode,
                    "failed_count": len(failed_tasks),
                    "message": message,
                },
            )
            task_finished = True

            yield _sse_event(
                {
                    "type": "done",
                    "mode": mode,
                    "provider_name": llm_config.get("provider_name"),
                    "model": llm_config.get("model"),
                    "generated_count": saved_count,
                    "failed_count": len(failed_tasks),
                    "failed_tasks": failed_tasks,
                    "message": message,
                }
            )
        except Exception as exc:
            stream_db.rollback()
            failed_tasks = list(failed_by_key.values())
            if saved_count > 0:
                message = f"已写入用例库 {saved_count} 条，后续生成中断：{exc}"
                if failed_tasks:
                    message += f"；{len(failed_tasks)} 个需求生成失败已跳过"
                if hub_task_id:
                    hub_ai_task_service.finish_task(
                        stream_db,
                        hub_task_id,
                        status="partial",
                        generated_total=saved_count,
                        applied_total=saved_count,
                        done_items=saved_count,
                        total_items=generate_count,
                        error=str(exc),
                        meta={"message": message, "partial": True},
                    )
                task_finished = True
                yield _sse_event(
                    {
                        "type": "done",
                        "mode": mode,
                        "provider_name": llm_config.get("provider_name"),
                        "model": llm_config.get("model"),
                        "generated_count": saved_count,
                        "failed_count": len(failed_tasks),
                        "failed_tasks": failed_tasks,
                        "partial": True,
                        "message": message,
                    }
                )
            else:
                if hub_task_id:
                    hub_ai_task_service.finish_task(
                        stream_db,
                        hub_task_id,
                        status="failed",
                        generated_total=0,
                        applied_total=0,
                        error=str(exc),
                    )
                task_finished = True
                yield _sse_event({"type": "error", "message": f"AI 生成失败: {exc}"})
        finally:
            if worker_active and hub_task_id:
                hub_ai_task_service.set_hub_parse_worker_active(stream_db, hub_task_id, False)
            if hub_task_id and not task_finished:
                _abort_functional_hub_stream_task(
                    stream_db,
                    hub_task_id,
                    saved_count=saved_count,
                    error="连接中断或生成异常退出",
                )
            stream_db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/export/excel", dependencies=[Depends(require_menu_permission("testcases"))])
def export_excel(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project(db, project_id, current_user)
    cases = list_project_testcases(db, project_id)
    buffer, filename = export_testcases_excel(project, cases)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": build_content_disposition(filename, "testcases.xlsx")},
    )


@router.get("/export/xmind", dependencies=[Depends(require_menu_permission("testcases"))])
def export_xmind(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project(db, project_id, current_user)
    cases = list_project_testcases(db, project_id)
    buffer, filename = export_testcases_xmind(project, cases)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.xmind.workbook",
        headers={"Content-Disposition": build_content_disposition(filename, "testcases.xmind")},
    )


@router.post("/import/file", response_model=TestCaseFileImportResponse, dependencies=[Depends(require_menu_permission("testcases"))])
async def import_testcases_file(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    import_mode: str = Form("append"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project(db, project_id, current_user)
    if import_mode not in ALLOWED_TESTCASE_IMPORT_MODES:
        raise HTTPException(status_code=400, detail="无效的导入模式，仅支持 append 或 replace")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")
    try:
        rows = parse_testcase_import_file(file.filename or "", file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    total_rows, unique_count, duplicate_merged, duplicate_titles = summarize_import_rows(rows)
    created, skipped, cleared = import_testcases_from_rows(
        db,
        project,
        rows,
        current_user,
        mode=import_mode,  # type: ignore[arg-type]
    )

    def _build_import_response(message: str) -> TestCaseFileImportResponse:
        return TestCaseFileImportResponse(
            imported_count=created,
            skipped_count=skipped,
            cleared_count=cleared,
            total_rows=total_rows,
            unique_count=unique_count,
            duplicate_merged_count=duplicate_merged,
            duplicate_titles=duplicate_titles,
            message=message,
        )

    if created == 0:
        if import_mode == "replace" and cleared > 0:
            return _build_import_response(f"已清空 {cleared} 条原用例，但 Excel 中没有可导入的有效行")
        if skipped > 0:
            detail = "标题为空或字段无效"
            return _build_import_response(f"未导入新用例，跳过 {skipped} 条（{detail}）")
        raise HTTPException(status_code=400, detail="没有成功导入任何用例，请检查文件内容")

    parts: List[str] = []
    if import_mode == "replace" and cleared:
        parts.append(f"已清空 {cleared} 条原用例")
    parts.append(f"共读取 {total_rows} 行，按标题合并后 {unique_count} 条")
    if duplicate_merged:
        preview = "、".join(duplicate_titles[:3])
        if len(duplicate_titles) > 3:
            preview += f" 等 {len(duplicate_titles)} 个标题"
        parts.append(f"{duplicate_merged} 行标题重复已合并（{preview}）")
    parts.append(f"成功导入 {created} 条")
    message = "；".join(parts)
    if skipped:
        message += f"；跳过 {skipped} 条"
    return _build_import_response(message)


@router.get("/import/template/excel", dependencies=[Depends(require_menu_permission("testcases"))])
def download_testcases_import_template_excel(
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    buffer, filename = build_testcases_import_template_excel()
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": build_content_disposition(filename, "testcases_import_template.xlsx")},
    )


@router.get("/import/template/xmind", dependencies=[Depends(require_menu_permission("testcases"))])
def download_testcases_import_template_xmind(
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    buffer, filename = build_testcases_import_template_xmind()
    return StreamingResponse(
        buffer,
        media_type="application/vnd.xmind.workbook",
        headers={"Content-Disposition": build_content_disposition(filename, "testcases_import_template.xmind")},
    )


@router.post("/batch/review", response_model=TestCaseBatchReviewResponse, dependencies=[Depends(require_menu_permission("testcases"))])
def batch_review_testcases(
    data: TestCaseBatchReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.review_status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="无效的评审状态")

    _check_project(db, data.project_id, current_user)
    cases = db.query(TestCase).filter(
        TestCase.id.in_(data.case_ids),
        TestCase.project_id == data.project_id,
    ).all()
    if len(cases) != len(set(data.case_ids)):
        raise HTTPException(status_code=404, detail="部分用例不存在")

    allowed_from = REVIEW_TRANSITIONS.get(data.review_status)
    updated = 0
    skipped = 0
    for case in cases:
        if allowed_from and case.review_status not in allowed_from:
            skipped += 1
            continue
        case.review_status = data.review_status
        updated += 1

    if updated == 0:
        status_labels = {
            "pending": "提交评审",
            "approved": "通过",
            "rejected": "驳回",
        }
        raise HTTPException(
            status_code=400,
            detail=f"所选用例均无法批量{status_labels.get(data.review_status, '更新')}",
        )

    db.commit()
    message = f"成功{('通过' if data.review_status == 'approved' else '驳回' if data.review_status == 'rejected' else '提交评审')} {updated} 条用例"
    if skipped:
        message += f"，跳过 {skipped} 条状态不符的用例"
    return TestCaseBatchReviewResponse(
        updated_count=updated,
        skipped_count=skipped,
        message=message,
    )


@router.post("/batch/delete", response_model=BatchDeleteResponse, dependencies=[Depends(require_menu_permission("testcases"))])
def batch_delete_testcases(
    data: TestCaseBatchDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user)
    cases = db.query(TestCase).filter(
        TestCase.id.in_(data.case_ids),
        TestCase.project_id == data.project_id,
    ).all()
    if not cases:
        raise HTTPException(status_code=404, detail="未找到可删除的用例")
    deleted_count = delete_testcases_with_execution_cleanup(db, cases)
    db.commit()
    return BatchDeleteResponse(deleted_count=deleted_count, message=f"成功删除 {deleted_count} 条用例")


@router.get("/{case_id}", response_model=TestCaseOut, dependencies=[Depends(require_menu_permission("testcases"))])
def get_testcase(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = db.query(TestCase).options(joinedload(TestCase.creator)).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    _check_project(db, case.project_id, current_user)
    return _testcase_out(case, db)


@router.put("/{case_id}", response_model=TestCaseOut, dependencies=[Depends(require_menu_permission("testcases"))])
def update_testcase(
    case_id: int,
    data: TestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    _check_project(db, case.project_id, current_user)

    updates = data.model_dump(exclude_unset=True)
    review_status = updates.get("review_status")
    if review_status is not None and review_status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="无效的评审状态")

    if "requirement_id" in updates and updates["requirement_id"] is not None:
        matched = fetch_requirements_for_ai(
            db,
            project_id=case.project_id,
            requirement_ids=[updates["requirement_id"]],
        )
        requirement = matched[0] if matched else None
        if not requirement:
            raise HTTPException(status_code=404, detail="关联需求不存在或不属于当前项目")

    for key, value in updates.items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return _testcase_out(case, db)


@router.delete("/{case_id}", status_code=204, dependencies=[Depends(require_menu_permission("testcases"))])
def delete_testcase(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    _check_project(db, case.project_id, current_user)
    delete_testcases_with_execution_cleanup(db, [case])
    db.commit()
    return None
