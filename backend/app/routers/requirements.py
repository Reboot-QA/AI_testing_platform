import json
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.schemas import (
    RequirementBatchDelete,
    RequirementBatchDeleteResponse,
    RequirementBatchImport,
    RequirementBatchImportResponse,
    RequirementBatchStatusResponse,
    RequirementBatchStatusUpdate,
    RequirementCreate,
    RequirementExtractResponse,
    RequirementFileImportResponse,
    RequirementOut,
    RequirementPageOut,
    RequirementUpdate,
)
from app.services.ai_service import extract_requirements_from_document, stream_extract_requirements
from app.services.document_service import extract_text_from_document
from app.services.project_access_service import get_accessible_project, get_accessible_project_ids
from app.services.requirement_io_service import (
    build_content_disposition,
    import_requirements_from_rows,
    list_project_requirements,
    next_requirement_sort_order,
    parse_requirement_import_file,
    summarize_import_rows,
)
from app.services.requirement_io_service import (
    export_requirements_excel as build_requirements_excel,
)
from app.services.requirement_io_service import (
    export_requirements_xmind as build_requirements_xmind,
)
from app.services.requirement_query_helper import (
    apply_requirement_list_options,
    apply_requirement_list_order,
    requirement_has_sort_order_column,
    requirement_sort_order_value,
)
from app.services.settings_service import get_effective_llm_config

ALLOWED_REQUIREMENT_STATUSES = {"draft", "approved", "closed"}
ALLOWED_REQUIREMENT_IMPORT_MODES = {"append", "replace"}

router = APIRouter(prefix="/requirements", tags=["需求"])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _requirement_out(req: Requirement, db: Session) -> RequirementOut:
    case_count = db.query(TestCase).filter(TestCase.requirement_id == req.id).count()
    creator_name = req.creator.username if req.creator else ""
    if not creator_name and req.created_by_id:
        creator = db.query(User).filter(User.id == req.created_by_id).first()
        creator_name = creator.username if creator else ""
    project_name = req.project.name if req.project else ""
    if not project_name:
        project = db.query(Project).filter(Project.id == req.project_id).first()
        project_name = project.name if project else ""
    return RequirementOut(
        id=req.id,
        project_id=req.project_id,
        project_name=project_name,
        title=req.title,
        description=req.description,
        req_type=req.req_type,
        priority=req.priority,
        status=req.status,
        source=req.source,
        sort_order=requirement_sort_order_value(req),
        created_by_id=req.created_by_id,
        creator_name=creator_name,
        created_at=req.created_at,
        testcase_count=case_count,
    )


def _check_project(db: Session, project_id: int, user: User) -> Project:
    return get_accessible_project(db, project_id, user)


def _clear_requirement_testcases(db: Session, req_id: int) -> int:
    cases = db.query(TestCase).filter(TestCase.requirement_id == req_id).all()
    for case in cases:
        db.delete(case)
    if cases:
        db.flush()
    return len(cases)


ALLOWED_REQUIREMENT_SOURCES = frozenset({"manual", "ai_document"})
ALLOWED_LIST_ORDERS = frozenset({"default", "created_at_desc"})


def _apply_requirement_list_order(query, order: Optional[str]):
    if order == "created_at_desc":
        return query.order_by(Requirement.created_at.desc(), Requirement.id.desc())
    return apply_requirement_list_order(query)


@router.get("", response_model=Union[List[RequirementOut], RequirementPageOut])
def list_requirements(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    unreviewed: Optional[bool] = Query(None),
    linked: Optional[bool] = Query(None),
    keyword: Optional[str] = Query(None, max_length=200),
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible_ids = get_accessible_project_ids(db, current_user)
    if not accessible_ids:
        if page is not None:
            return RequirementPageOut(items=[], total=0, page=page, page_size=page_size)
        return []

    query = apply_requirement_list_options(
        db.query(Requirement)
        .options(joinedload(Requirement.creator), joinedload(Requirement.project))
        .filter(Requirement.project_id.in_(accessible_ids))
    )
    if project_id is not None:
        _check_project(db, project_id, current_user)
        query = query.filter(Requirement.project_id == project_id)
    if status:
        if status not in ALLOWED_REQUIREMENT_STATUSES:
            raise HTTPException(status_code=400, detail="无效的需求状态")
        query = query.filter(Requirement.status == status)
    if source:
        if source not in ALLOWED_REQUIREMENT_SOURCES:
            raise HTTPException(status_code=400, detail="无效的 source/order")
        query = query.filter(Requirement.source == source)
    if order:
        if order not in ALLOWED_LIST_ORDERS:
            raise HTTPException(status_code=400, detail="无效的 source/order")
    if unreviewed:
        query = query.filter(Requirement.status != "approved")
    if linked is not None:
        tc_query = select(TestCase.requirement_id).where(TestCase.requirement_id.isnot(None))
        if project_id is not None:
            tc_query = tc_query.where(TestCase.project_id == project_id)
        tc_query = tc_query.distinct()
        if linked:
            query = query.filter(Requirement.id.in_(tc_query))
        else:
            query = query.filter(~Requirement.id.in_(tc_query))
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Requirement.title.like(like),
                Requirement.description.like(like),
            )
        )
    query = _apply_requirement_list_order(query, order)

    if page is not None:
        total = query.count()
        reqs = query.offset((page - 1) * page_size).limit(page_size).all()
        return RequirementPageOut(
            items=[_requirement_out(r, db) for r in reqs],
            total=total,
            page=page,
            page_size=page_size,
        )

    reqs = query.all()
    return [_requirement_out(r, db) for r in reqs]


@router.post("", response_model=RequirementOut)
def create_requirement(
    data: RequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user)
    payload = data.model_dump()
    payload["created_by_id"] = current_user.id
    if requirement_has_sort_order_column():
        payload["sort_order"] = next_requirement_sort_order(db, data.project_id)
    req = Requirement(**payload)
    db.add(req)
    db.commit()
    db.refresh(req)
    return _requirement_out(req, db)


@router.post("/batch/status", response_model=RequirementBatchStatusResponse)
def batch_update_requirement_status(
    data: RequirementBatchStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.status not in ALLOWED_REQUIREMENT_STATUSES:
        raise HTTPException(status_code=400, detail="无效的需求状态")

    _check_project(db, data.project_id, current_user)
    requirements = (
        db.query(Requirement)
        .filter(
            Requirement.id.in_(data.requirement_ids),
            Requirement.project_id == data.project_id,
        )
        .all()
    )
    if len(requirements) != len(set(data.requirement_ids)):
        raise HTTPException(status_code=404, detail="部分需求不存在")

    for req in requirements:
        req.status = data.status
    db.commit()
    return RequirementBatchStatusResponse(
        updated_count=len(requirements),
        message=f"成功更新 {len(requirements)} 条需求状态",
    )


@router.post("/batch/delete", response_model=RequirementBatchDeleteResponse)
def batch_delete_requirements(
    data: RequirementBatchDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user)
    requirements = (
        db.query(Requirement)
        .filter(
            Requirement.id.in_(data.requirement_ids),
            Requirement.project_id == data.project_id,
        )
        .all()
    )
    if len(requirements) != len(set(data.requirement_ids)):
        raise HTTPException(status_code=404, detail="部分需求不存在")

    deleted_count = 0
    skipped_titles: List[str] = []
    for req in requirements:
        case_count = db.query(TestCase).filter(TestCase.requirement_id == req.id).count()
        if case_count > 0:
            skipped_titles.append(req.title)
            continue
        db.delete(req)
        deleted_count += 1

    if deleted_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"所选用需求均有关联用例，无法删除：{', '.join(skipped_titles[:10])}",
        )

    db.commit()
    message = f"成功删除 {deleted_count} 条需求"
    if skipped_titles:
        message += f"，跳过 {len(skipped_titles)} 条有关联用例的需求"
    return RequirementBatchDeleteResponse(
        deleted_count=deleted_count,
        skipped_count=len(skipped_titles),
        skipped_titles=skipped_titles,
        message=message,
    )


@router.post("/ai/extract", response_model=RequirementExtractResponse)
async def extract_requirements_from_file(
    project_id: int = Form(...),
    provider_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, project_id, current_user)
    content = await file.read()
    filename = file.filename or "document.txt"

    try:
        document_text, truncated = extract_text_from_document(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    llm_config = get_effective_llm_config(db, provider_id)
    if provider_id and llm_config.get("provider_id") != provider_id:
        raise HTTPException(status_code=400, detail="所选模型不存在或已禁用")
    if not llm_config["mock_mode"] and not llm_config["api_key"]:
        raise HTTPException(status_code=400, detail="当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    try:
        requirements_data, mode = await extract_requirements_from_document(
            document_text,
            api_base=llm_config["api_base"],
            api_key=llm_config["api_key"],
            model=llm_config["model"],
            mock_mode=llm_config["mock_mode"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"AI 解析失败: {exc}") from exc

    message = f"成功提取 {len(requirements_data)} 条需求点"
    if truncated:
        message += "（文档过长，已截取前 15000 字解析）"

    return RequirementExtractResponse(
        filename=filename,
        requirements=requirements_data,
        mode=mode,
        provider_name=llm_config.get("provider_name"),
        model=llm_config.get("model"),
        truncated=truncated,
        message=message,
    )


@router.post("/ai/extract/stream")
async def extract_requirements_stream(
    project_id: int = Form(...),
    provider_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, project_id, current_user)
    content = await file.read()
    filename = file.filename or "document.txt"

    try:
        document_text, truncated = extract_text_from_document(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    llm_config = get_effective_llm_config(db, provider_id)
    if provider_id and llm_config.get("provider_id") != provider_id:
        raise HTTPException(status_code=400, detail="所选模型不存在或已禁用")
    if not llm_config["mock_mode"] and not llm_config["api_key"]:
        raise HTTPException(status_code=400, detail="当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    async def event_generator():
        saved_count = 0
        mode = "mock" if llm_config["mock_mode"] else "llm"
        try:
            yield _sse_event(
                {
                    "type": "status",
                    "message": "开始分析文档...",
                    "current": 0,
                    "chunk": 0,
                    "chunk_total": 0,
                }
            )
            async for item, current_mode, current, chunk_index, chunk_total in stream_extract_requirements(
                document_text,
                api_base=llm_config["api_base"],
                api_key=llm_config["api_key"],
                model=llm_config["model"],
                mock_mode=llm_config["mock_mode"],
            ):
                mode = current_mode
                saved_count = current
                yield _sse_event(
                    {
                        "type": "status",
                        "message": f"正在分析文档第 {chunk_index}/{chunk_total} 段，已提取 {saved_count} 条需求点...",
                        "current": saved_count,
                        "chunk": chunk_index,
                        "chunk_total": chunk_total,
                    }
                )
                yield _sse_event(
                    {
                        "type": "requirement",
                        "data": item,
                        "current": saved_count,
                        "chunk": chunk_index,
                        "chunk_total": chunk_total,
                    }
                )

            message = f"成功提取 {saved_count} 条需求点"
            if truncated:
                message += "（文档过长，已截取前 15000 字解析）"
            yield _sse_event(
                {
                    "type": "done",
                    "mode": mode,
                    "filename": filename,
                    "total": saved_count,
                    "truncated": truncated,
                    "provider_name": llm_config.get("provider_name"),
                    "model": llm_config.get("model"),
                    "message": message,
                }
            )
        except Exception as exc:
            yield _sse_event({"type": "error", "message": f"AI 解析失败: {exc}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/batch/import", response_model=RequirementBatchImportResponse)
def batch_import_requirements(
    data: RequirementBatchImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user)
    saved: List[Requirement] = []
    next_sort_order = next_requirement_sort_order(db, data.project_id)
    for item in data.requirements:
        req_kwargs = {
            "project_id": data.project_id,
            "title": item.title.strip(),
            "description": item.description,
            "req_type": item.req_type,
            "priority": item.priority,
            "status": "draft",
            "source": "ai_document",
            "created_by_id": current_user.id,
        }
        if requirement_has_sort_order_column():
            req_kwargs["sort_order"] = next_sort_order
            next_sort_order += 1
        req = Requirement(**req_kwargs)
        db.add(req)
        saved.append(req)
    db.commit()
    for req in saved:
        db.refresh(req)
    return RequirementBatchImportResponse(
        imported_count=len(saved),
        requirements=[_requirement_out(req, db) for req in saved],
        message=f"成功导入 {len(saved)} 条需求到需求点",
    )


@router.get("/export/excel")
def export_requirements_excel(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project(db, project_id, current_user)
    requirements = list_project_requirements(db, project_id)
    buffer, filename = build_requirements_excel(project, requirements)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": build_content_disposition(filename, "requirements.xlsx")},
    )


@router.get("/export/xmind")
def export_requirements_xmind(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project(db, project_id, current_user)
    requirements = list_project_requirements(db, project_id)
    buffer, filename = build_requirements_xmind(project, requirements)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.xmind.workbook",
        headers={"Content-Disposition": build_content_disposition(filename, "requirements.xmind")},
    )


@router.post("/import/file", response_model=RequirementFileImportResponse)
async def import_requirements_file(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    import_mode: str = Form("append"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _check_project(db, project_id, current_user)
    if import_mode not in ALLOWED_REQUIREMENT_IMPORT_MODES:
        raise HTTPException(status_code=400, detail="无效的导入模式，仅支持 append 或 replace")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")
    try:
        rows = parse_requirement_import_file(file.filename or "", file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    total_rows, unique_count, duplicate_merged, duplicate_titles = summarize_import_rows(rows)
    created, skipped, cleared = import_requirements_from_rows(
        db,
        project,
        rows,
        current_user,
        mode=import_mode,  # type: ignore[arg-type]
    )

    def _build_import_response(message: str) -> RequirementFileImportResponse:
        return RequirementFileImportResponse(
            imported_count=created,
            updated_count=0,
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
            return _build_import_response(f"已清空 {cleared} 条原需求，但 Excel 中没有可导入的有效行")
        if skipped > 0:
            return _build_import_response(f"未导入任何需求，跳过 {skipped} 条（标题为空或字段无效）")
        raise HTTPException(status_code=400, detail="没有成功导入任何需求，请检查文件格式与内容")

    parts: List[str] = []
    if import_mode == "replace" and cleared:
        parts.append(f"已清空 {cleared} 条原需求")
    parts.append(f"共读取 {total_rows} 行，成功导入 {created} 条")
    message = "；".join(parts)
    if skipped:
        message += f"；跳过 {skipped} 条"
    return _build_import_response(message)


@router.get("/{req_id}", response_model=RequirementOut)
def get_requirement(req_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(Requirement).filter(Requirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    _check_project(db, req.project_id, current_user)
    return _requirement_out(req, db)


@router.put("/{req_id}", response_model=RequirementOut)
def update_requirement(
    req_id: int,
    data: RequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Requirement).filter(Requirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    _check_project(db, req.project_id, current_user)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(req, key, value)
    db.commit()
    db.refresh(req)
    return _requirement_out(req, db)


@router.delete("/{req_id}/testcases")
def clear_requirement_testcases(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Requirement).filter(Requirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    _check_project(db, req.project_id, current_user)

    deleted_count = _clear_requirement_testcases(db, req_id)
    db.commit()
    if deleted_count:
        return {"message": f"已清理 {deleted_count} 条关联用例", "deleted_testcase_count": deleted_count}
    return {"message": "暂无关联用例", "deleted_testcase_count": 0}


@router.delete("/{req_id}")
def delete_requirement(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(Requirement).filter(Requirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    _check_project(db, req.project_id, current_user)

    case_count = db.query(TestCase).filter(TestCase.requirement_id == req_id).count()
    if case_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该需求下存在 {case_count} 条关联用例，请先清理全部关联用例后再删除",
        )

    db.delete(req)
    db.commit()
    return {"message": "删除成功", "deleted_testcase_count": 0}
