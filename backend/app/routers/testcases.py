import asyncio
import json
from io import BytesIO
from urllib.parse import quote

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.auth import get_current_user
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
    TestCaseOut,
    TestCasePageOut,
    TestCaseUpdate,
)
from app.services.ai_service import build_generation_tasks, generate_testcases, stream_generate_batches
from app.services.settings_service import get_effective_llm_config

router = APIRouter(prefix="/testcases", tags=["用例"])

ALLOWED_REVIEW_STATUSES = {"draft", "pending", "approved", "rejected"}
REVIEW_TRANSITIONS = {
    "pending": {"draft", "rejected"},
    "approved": {"pending"},
    "rejected": {"pending"},
}


def _check_project(db: Session, project_id: int, user_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _build_content_disposition(filename: str) -> str:
    """Build RFC 5987 Content-Disposition header for non-ASCII filenames."""
    ascii_fallback = "testcases.xlsx"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def _prepare_ai_generate(
    db: Session,
    data: AIGenerateRequest,
    current_user: User,
) -> Dict[str, Any]:
    _check_project(db, data.project_id, current_user.id)

    requirement_text = data.requirement_text or ""
    requirement_ids = list(dict.fromkeys(data.requirement_ids or []))
    if data.requirement_id and data.requirement_id not in requirement_ids:
        requirement_ids.insert(0, data.requirement_id)

    selected_requirements: List[Requirement] = []
    if requirement_ids:
        selected_requirements = (
            db.query(Requirement)
            .filter(
                Requirement.id.in_(requirement_ids),
                Requirement.project_id == data.project_id,
            )
            .all()
        )
        if len(selected_requirements) != len(requirement_ids):
            raise HTTPException(status_code=404, detail="部分关联需求不存在")
        not_approved = [req.title for req in selected_requirements if req.status != "approved"]
        if not_approved:
            raise HTTPException(
                status_code=400,
                detail=f"仅已评审需求可关联生成用例：{', '.join(not_approved)}",
            )
        requirement_ids_with_cases = {
            row[0]
            for row in db.query(TestCase.requirement_id)
            .filter(TestCase.requirement_id.in_(requirement_ids))
            .distinct()
            .all()
        }
        has_cases = [req.title for req in selected_requirements if req.id in requirement_ids_with_cases]
        if has_cases:
            raise HTTPException(
                status_code=400,
                detail=f"以下需求已有关联用例，不能重复 AI 生成：{', '.join(has_cases)}",
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


def _stage_generated_case(
    db: Session,
    *,
    project_id: int,
    requirement_id: Optional[int],
    selected_requirements: List[Requirement],
    case_type: str,
    mode: str,
    item: dict,
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
) -> TestCase:
    case = _stage_generated_case(
        db,
        project_id=project_id,
        requirement_id=requirement_id,
        selected_requirements=selected_requirements,
        case_type=case_type,
        mode=mode,
        item=item,
    )
    db.commit()
    db.refresh(case)
    return case


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _build_generation_tasks(ctx: Dict[str, Any], total_count: int) -> List[Dict[str, Any]]:
    req_items = [
        {"id": req.id, "title": req.title, "description": req.description or ""}
        for req in ctx["selected_requirements"]
    ]
    manual_text = ctx["requirement_text"] if not req_items else ""
    return build_generation_tasks(req_items, manual_text, total_count)


@router.get("", response_model=Union[List[TestCaseOut], TestCasePageOut])
def list_testcases(
    project_id: int = Query(...),
    requirement_id: Optional[int] = Query(None),
    review_status: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, project_id, current_user.id)
    query = db.query(TestCase).filter(TestCase.project_id == project_id)
    if requirement_id:
        query = query.filter(TestCase.requirement_id == requirement_id)
    if review_status:
        query = query.filter(TestCase.review_status == review_status)
    query = query.order_by(TestCase.id.desc())

    if page is not None:
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return TestCasePageOut(items=items, total=total, page=page, page_size=page_size)

    return query.all()


@router.post("", response_model=TestCaseOut)
def create_testcase(
    data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user.id)
    case = TestCase(**data.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.post("/ai/generate", response_model=AIGenerateResponse)
async def ai_generate(
    data: AIGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ctx = _prepare_ai_generate(db, data, current_user)
    llm_config = ctx["llm_config"]
    tasks = _build_generation_tasks(ctx, data.count)

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
                    )
                )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {exc}") from exc

    return AIGenerateResponse(
        generated_count=len(saved),
        testcases=saved,
        mode=mode,
        provider_name=llm_config.get("provider_name"),
        model=llm_config.get("model"),
    )


@router.post("/ai/generate/stream")
async def ai_generate_stream(
    data: AIGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        ctx = _prepare_ai_generate(db, data, current_user)
    except HTTPException:
        db.close()
        raise
    db.close()

    async def event_generator():
        stream_db = SessionLocal()
        saved_count = 0
        failed_tasks: List[str] = []
        mode = "mock" if ctx["llm_config"]["mock_mode"] else "llm"
        llm_config = ctx["llm_config"]
        tasks = _build_generation_tasks(ctx, data.count)

        try:
            if not tasks:
                yield _sse_event({"type": "error", "message": "没有可生成的需求任务，请检查关联需求"})
                return

            yield _sse_event(
                {
                    "type": "status",
                    "message": "开始生成用例...",
                    "current": 0,
                    "total": data.count,
                }
            )

            async for cases_data, batch_mode, batch_index, batch_total, requirement_id, label, task_error in stream_generate_batches(
                tasks,
                data.case_type,
                api_base=llm_config["api_base"],
                api_key=llm_config["api_key"],
                model=llm_config["model"],
                mock_mode=llm_config["mock_mode"],
            ):
                mode = batch_mode
                if task_error:
                    failed_tasks.append(f"{label}：{task_error}")
                    yield _sse_event(
                        {
                            "type": "status",
                            "message": f"「{label}」生成失败，已跳过（{batch_index}/{batch_total}）",
                            "current": saved_count,
                            "total": data.count,
                        }
                    )
                    continue

                yield _sse_event(
                    {
                        "type": "status",
                        "message": f"正在为「{label}」生成用例（{batch_index}/{batch_total} 批）...",
                        "current": saved_count,
                        "total": data.count,
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
                    )
                    stream_db.commit()
                    saved_count += 1
                    yield _sse_event(
                        {
                            "type": "case",
                            "data": TestCaseOut.model_validate(case).model_dump(mode="json"),
                            "current": saved_count,
                            "total": data.count,
                            "saved": True,
                        }
                    )
                    if llm_config["mock_mode"]:
                        await asyncio.sleep(0.08)

            if saved_count == 0:
                detail = failed_tasks[0] if len(failed_tasks) == 1 else "；".join(failed_tasks[:3])
                if len(failed_tasks) > 3:
                    detail += f" 等 {len(failed_tasks)} 项"
                raise ValueError(detail or "未生成任何用例，请检查 API Key 或开启 Mock 模式")

            message = f"成功生成 {saved_count} 条用例，已实时写入用例库"
            if failed_tasks:
                message += f"，{len(failed_tasks)} 个需求生成失败已跳过"

            yield _sse_event(
                {
                    "type": "done",
                    "mode": mode,
                    "provider_name": llm_config.get("provider_name"),
                    "model": llm_config.get("model"),
                    "generated_count": saved_count,
                    "failed_count": len(failed_tasks),
                    "message": message,
                }
            )
        except Exception as exc:
            stream_db.rollback()
            if saved_count > 0:
                message = f"已写入用例库 {saved_count} 条，后续生成中断：{exc}"
                if failed_tasks:
                    message += f"；{len(failed_tasks)} 个需求生成失败已跳过"
                yield _sse_event(
                    {
                        "type": "done",
                        "mode": mode,
                        "provider_name": llm_config.get("provider_name"),
                        "model": llm_config.get("model"),
                        "generated_count": saved_count,
                        "failed_count": len(failed_tasks),
                        "partial": True,
                        "message": message,
                    }
                )
            else:
                yield _sse_event({"type": "error", "message": f"AI 生成失败: {exc}"})
        finally:
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


@router.get("/export/excel")
def export_excel(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project(db, project_id, current_user.id)
    cases = db.query(TestCase).filter(TestCase.project_id == project_id).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "测试用例"
    headers = ["ID", "标题", "类型", "优先级", "前置条件", "步骤", "预期结果", "标签", "来源", "评审状态"]
    ws.append(headers)
    for c in cases:
        ws.append([
            c.id, c.title, c.case_type, c.priority,
            c.preconditions, c.steps, c.expected_results,
            c.tags, c.source, c.review_status,
        ])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"{project.name}_testcases.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _build_content_disposition(filename)},
    )


@router.post("/batch/review", response_model=TestCaseBatchReviewResponse)
def batch_review_testcases(
    data: TestCaseBatchReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.review_status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="无效的评审状态")

    _check_project(db, data.project_id, current_user.id)
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


@router.post("/batch/delete", response_model=BatchDeleteResponse)
def batch_delete_testcases(
    data: TestCaseBatchDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user.id)
    cases = db.query(TestCase).filter(
        TestCase.id.in_(data.case_ids),
        TestCase.project_id == data.project_id,
    ).all()
    if not cases:
        raise HTTPException(status_code=404, detail="未找到可删除的用例")
    for case in cases:
        db.delete(case)
    db.commit()
    return BatchDeleteResponse(deleted_count=len(cases), message=f"成功删除 {len(cases)} 条用例")


@router.get("/{case_id}", response_model=TestCaseOut)
def get_testcase(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    _check_project(db, case.project_id, current_user.id)
    return case


@router.put("/{case_id}", response_model=TestCaseOut)
def update_testcase(
    case_id: int,
    data: TestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    _check_project(db, case.project_id, current_user.id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}")
def delete_testcase(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    _check_project(db, case.project_id, current_user.id)
    db.delete(case)
    db.commit()
    return {"message": "删除成功"}
