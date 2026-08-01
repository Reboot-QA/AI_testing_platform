import json
import zlib
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.constants.limits import normalize_req_case_title
from app.models.hub_ai_task import (
    HUB_AI_TASK_ORPHAN_MINUTES,
    HUB_AI_TASK_STALE_MINUTES,
    HUB_AI_TASK_STATUSES,
    HUB_AI_TASK_TYPES,
    HubAiTask,
)
from app.models.hub_ai_task_case_item import HubAiTaskCaseItem
from app.models.hub_ai_task_requirement_item import HubAiTaskRequirementItem
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.services.llm_label import format_llm_task_model_column, llm_task_model_column_from_meta
from app.services.requirement_io_service import next_requirement_sort_order

# 单项目同时进行中的 Hub AI 任务（需求解析 + 用例生成）上限，避免拖垮 DB / LLM
MAX_CONCURRENT_RUNNING_HUB_TASKS = 3
# 功能用例 SSE 生成占用 LLM 批并发，单项目同时仅允许 1 个，避免多任务互抢卡死
MAX_CONCURRENT_FUNCTIONAL_HUB_TASKS = 1
# 需求文档 SSE 解析单项目同时仅 1 个，避免同项目双任务互抢；跨项目靠全局 LLM 信号量限流
MAX_CONCURRENT_REQUIREMENT_HUB_TASKS = 1
# 列表/详情补入库时每请求最多处理条数，避免一次同步数百条阻塞 worker
SYNC_REQUIREMENT_IMPORT_BATCH = 8

HUB_TASK_TERMINAL = ("succeeded", "partial", "failed", "canceled")
# 需求/用例 SSE：同一模型同时仅 1 个 running（跨项目），不同模型互不排队
HUB_SSE_TASK_TYPES = ("requirement", "functional")


def provider_queue_key(provider_id: Optional[int]) -> int:
    """排队槽位键：None/未指定视为 0（与环境默认模型同槽）。"""
    return int(provider_id) if provider_id is not None else 0


def llm_slot_key_from_config(llm_config: dict) -> int:
    """Hub 排队 + LLM HTTP 限流共用：有 provider_id 用 id，否则按 base+model 区分。"""
    pid = llm_config.get("provider_id")
    if pid is not None:
        return int(pid)
    sig = "|".join(
        [
            str(llm_config.get("api_base") or ""),
            str(llm_config.get("model") or ""),
            str(llm_config.get("provider_name") or ""),
        ]
    )
    if sig.replace("|", "").strip():
        return zlib.crc32(sig.encode("utf-8")) & 0x7FFFFFFF
    return 0


def llm_slot_key_from_meta(meta: dict) -> int:
    if meta.get("llm_slot_key") is not None:
        return int(meta["llm_slot_key"])
    if meta.get("provider_id") is not None:
        return int(meta["provider_id"])
    sig = "|".join(
        [
            str(meta.get("api_base") or ""),
            str(meta.get("model") or ""),
            str(meta.get("provider_name") or ""),
        ]
    )
    if sig.replace("|", "").strip():
        return zlib.crc32(sig.encode("utf-8")) & 0x7FFFFFFF
    return 0


def task_provider_id(task: HubAiTask) -> int:
    if not task.meta_json:
        return 0
    try:
        meta = json.loads(task.meta_json)
    except json.JSONDecodeError:
        return 0
    if not isinstance(meta, dict):
        return 0
    return llm_slot_key_from_meta(meta)


def _hub_task_meta(task: HubAiTask) -> Dict[str, Any]:
    if not task.meta_json:
        return {}
    try:
        raw = json.loads(task.meta_json)
        return raw if isinstance(raw, dict) else {}
    except json.JSONDecodeError:
        return {}


def hub_task_model_label(db: Session, task: HubAiTask) -> str:
    """列表/详情「模型」列：仅 model 标识。"""
    meta = _hub_task_meta(task)
    model_meta = str(meta.get("model") or "").strip()
    if model_meta:
        return model_meta
    label = llm_task_model_column_from_meta(db, meta)
    if label:
        return label
    legacy = (task.category_label or "").strip()
    if legacy and task.task_type == "requirement":
        return format_llm_task_model_column(provider_name=legacy)
    return ""


def set_task_sse_waiting(db: Session, task_id: int, waiting: bool) -> None:
    """标记 pending 任务是否有 SSE 连接在 wait_hub_task_running 中等待（防止无连接被 promote 成假 running）。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).with_for_update().first()
    if not task:
        return
    meta = _hub_task_meta(task)
    if waiting:
        meta["sse_waiting"] = True
    else:
        meta.pop("sse_waiting", None)
    task.meta_json = json.dumps(meta, ensure_ascii=False)
    _touch_task(task)
    db.commit()


def set_hub_parse_worker_active(db: Session, task_id: int, active: bool) -> None:
    """标记需求/用例 SSE 后台解析协程是否在跑（用于识别无 worker 的僵尸 running）。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).with_for_update().first()
    if not task:
        return
    meta = _hub_task_meta(task)
    if active:
        meta["parse_worker_active"] = True
        meta["parse_worker_at"] = datetime.utcnow().isoformat()
    else:
        meta.pop("parse_worker_active", None)
        meta.pop("parse_worker_at", None)
    task.meta_json = json.dumps(meta, ensure_ascii=False)
    _touch_task(task)
    db.commit()


def _parse_worker_at_dt(meta: Dict[str, Any]) -> Optional[datetime]:
    raw = meta.get("parse_worker_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _acquire_hub_sse_slot_lock(db: Session, task_type: str, slot_key: int) -> Optional[str]:
    """创建 Hub SSE 任务前占槽，避免跨项目并发误判双 running。返回 MySQL 锁名；sqlite 用行锁。"""
    bind = db.get_bind()
    if bind.dialect.name == "mysql":
        lock_name = f"hub_ai:{task_type}:{slot_key}"[:64]
        conn = db.connection()
        got = conn.execute(text("SELECT GET_LOCK(:n, 20)"), {"n": lock_name}).scalar()
        if got != 1:
            raise HubTaskCapacityError("系统繁忙，请稍后重试")
        return lock_name
    db.query(HubAiTask).filter(
        HubAiTask.task_type == task_type,
        HubAiTask.status.in_(("running", "pending")),
    ).order_by(HubAiTask.id).with_for_update().limit(1).all()
    return None


def _release_hub_sse_slot_lock(db: Session, lock_name: Optional[str]) -> None:
    if not lock_name:
        return
    bind = db.get_bind()
    if bind.dialect.name != "mysql":
        return
    conn = db.connection()
    conn.execute(text("SELECT RELEASE_LOCK(:n)"), {"n": lock_name})


class HubTaskCapacityError(Exception):
    """项目 Hub AI 任务并发已达上限。"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def create_running_task(
    db: Session,
    *,
    project_id: int,
    task_type: str,
    created_by: Optional[int],
    target: str,
    category_label: str = "",
    total_items: int = 0,
    meta: Optional[Dict[str, Any]] = None,
    provider_id: Optional[int] = None,
) -> HubAiTask:
    if task_type not in HUB_AI_TASK_TYPES:
        raise ValueError("无效的任务类型")

    from app.models.project import Project

    project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
    if not project:
        raise ValueError("项目不存在")

    fail_stale_running_tasks(db, project_id=project_id)

    merged_meta = dict(meta or {})
    if provider_id is not None:
        merged_meta.setdefault("provider_id", provider_id)
    slot_key = merged_meta.get("llm_slot_key")
    if slot_key is None:
        slot_key = provider_queue_key(provider_id)
        merged_meta["llm_slot_key"] = slot_key
    else:
        slot_key = int(slot_key)

    lock_name: Optional[str] = None
    try:
        if task_type in HUB_SSE_TASK_TYPES:
            lock_name = _acquire_hub_sse_slot_lock(db, task_type, slot_key)
            initial_status = (
                "pending"
                if hub_task_should_queue(
                    db, project_id, task_type, provider_id=slot_key
                )
                else "running"
            )
        else:
            capacity_msg = hub_running_task_capacity_message(
                db, project_id, creating_task_type=task_type, provider_id=provider_id
            )
            if capacity_msg:
                raise HubTaskCapacityError(capacity_msg)
            initial_status = "running"

        task = HubAiTask(
            project_id=project_id,
            task_type=task_type,
            created_by=created_by,
            status=initial_status,
            target=target[:500],
            category_label=(category_label or "")[:200],
            total_items=max(total_items, 0),
            done_items=0,
            meta_json=json.dumps(merged_meta, ensure_ascii=False) if merged_meta else None,
        )
        now = datetime.utcnow()
        if initial_status == "running":
            task.progress_at = now
        task.updated_at = now
        db.add(task)
        if lock_name:
            _release_hub_sse_slot_lock(db, lock_name)
            lock_name = None
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise
    finally:
        _release_hub_sse_slot_lock(db, lock_name)


def _touch_task(task: HubAiTask) -> None:
    task.updated_at = datetime.utcnow()


def _touch_progress(task: HubAiTask) -> None:
    """仅在实际生成/解析有进展时更新，供僵死任务检测；勿在补入库等读路径调用。"""
    now = datetime.utcnow()
    task.progress_at = now
    task.updated_at = now


def update_progress(
    db: Session,
    task_id: int,
    *,
    done_items: Optional[int] = None,
    generated_total: Optional[int] = None,
    total_items: Optional[int] = None,
) -> None:
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task:
        return
    if done_items is not None:
        task.done_items = done_items
    if generated_total is not None:
        task.generated_total = generated_total
    if total_items is not None:
        task.total_items = total_items
    _touch_progress(task)
    db.commit()


def finish_task(
    db: Session,
    task_id: int,
    *,
    status: str,
    generated_total: int = 0,
    applied_total: int = 0,
    done_items: Optional[int] = None,
    total_items: Optional[int] = None,
    error: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    if status not in HUB_AI_TASK_STATUSES:
        status = "failed"
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task:
        return
    task.status = status
    task.generated_total = generated_total
    task.applied_total = applied_total
    if done_items is not None:
        task.done_items = done_items
    if total_items is not None:
        task.total_items = total_items
    task.error = error
    if meta is not None:
        existing = {}
        if task.meta_json:
            try:
                existing = json.loads(task.meta_json)
            except json.JSONDecodeError:
                existing = {}
        if isinstance(existing, dict):
            existing.update(meta)
            task.meta_json = json.dumps(existing, ensure_ascii=False)
        else:
            task.meta_json = json.dumps(meta, ensure_ascii=False)
    task.finished_at = datetime.utcnow()
    _touch_task(task)
    task_type = task.task_type
    slot_provider = task_provider_id(task)
    db.commit()
    if task_type in HUB_SSE_TASK_TYPES and status in HUB_TASK_TERMINAL:
        promote_next_pending_hub_task(db, task_type, slot_provider)


def count_running_hub_tasks_for_provider(
    db: Session, task_type: str, provider_id: int
) -> int:
    rows = (
        db.query(HubAiTask)
        .filter(
            HubAiTask.task_type == task_type,
            HubAiTask.status == "running",
        )
        .all()
    )
    return sum(1 for t in rows if task_provider_id(t) == provider_id)


def hub_task_should_queue(
    db: Session,
    project_id: int,
    task_type: str,
    *,
    provider_id: int = 0,
) -> bool:
    """是否应创建为 pending（同类型+同模型已有 running，或项目内同模型并发已满）。"""
    if task_type in HUB_SSE_TASK_TYPES:
        if count_running_hub_tasks_for_provider(db, task_type, provider_id) >= 1:
            return True
    return (
        hub_running_task_capacity_message(
            db,
            project_id,
            creating_task_type=task_type,
            provider_id=provider_id,
        )
        is not None
    )


def _first_pending_for_provider(
    db: Session, task_type: str, provider_id: int
) -> Optional[HubAiTask]:
    pending = (
        db.query(HubAiTask)
        .filter(HubAiTask.task_type == task_type, HubAiTask.status == "pending")
        .order_by(HubAiTask.id)
        .all()
    )
    for t in pending:
        if task_provider_id(t) == provider_id:
            return t
    return None


def try_promote_hub_task(db: Session, task_id: int) -> bool:
    """队首 pending 任务在有空闲执行槽时升为 running（同类型+同模型 FIFO）。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).with_for_update().first()
    if not task:
        return False
    if task.status == "running":
        return True
    if task.status != "pending":
        return False
    slot_provider = task_provider_id(task)
    head = _first_pending_for_provider(db, task.task_type, slot_provider)
    if not head or head.id != task.id:
        return False
    if hub_task_should_queue(
        db, task.project_id, task.task_type, provider_id=slot_provider
    ):
        return False
    if not _hub_task_meta(task).get("sse_waiting"):
        return False
    now = datetime.utcnow()
    task.status = "running"
    task.progress_at = now
    task.updated_at = now
    db.commit()
    return True


def promote_next_pending_hub_task(db: Session, task_type: str, provider_id: int) -> None:
    """某 running 任务结束后，尝试启动同模型队列中下一条 pending。"""
    if task_type not in HUB_SSE_TASK_TYPES:
        return
    first = _first_pending_for_provider(db, task_type, provider_id)
    if first:
        try_promote_hub_task(db, first.id)


def cancel_pending_hub_task(db: Session, task_id: int, *, error: str = "用户已取消") -> None:
    cancel_hub_task(db, task_id, error=error)


def cancel_hub_task(
    db: Session, task_id: int, *, error: str = "用户已停止任务"
) -> Optional[HubAiTask]:
    """停止 pending / running 任务（保留已生成条数），并尝试拉起同类型队列中的下一条。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).with_for_update().first()
    if not task:
        return None
    if task.status in HUB_TASK_TERMINAL:
        db.commit()
        return task
    generated = task.generated_total or 0
    applied = task.applied_total or 0
    finish_task(
        db,
        task_id,
        status="canceled",
        generated_total=generated,
        applied_total=applied,
        done_items=task.done_items,
        total_items=task.total_items,
        error=error,
    )
    return get_task(db, task_id)


def hub_task_is_canceled(db: Session, task_id: int) -> bool:
    task = get_task(db, task_id)
    return task is not None and task.status == "canceled"


def touch_hub_task_progress(db: Session, task_id: int) -> None:
    """长段 LLM 等待期间刷新 progress_at，避免被僵死回收误判。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if task and task.status == "running":
        _touch_progress(task)
        db.commit()


def _filtered_query(
    db: Session,
    project_id: int,
    task_type: str,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    task_id: Optional[int] = None,
):
    query = db.query(HubAiTask).filter(
        HubAiTask.project_id == project_id,
        HubAiTask.task_type == task_type,
    )
    if task_id is not None:
        query = query.filter(HubAiTask.id == task_id)
    if status:
        query = query.filter(HubAiTask.status == status)
    if date_from:
        query = query.filter(HubAiTask.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(
            HubAiTask.created_at < datetime.combine(date_to, time.min) + timedelta(days=1)
        )
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"
        creator_ids = select_user_ids_by_keyword(db, like)
        clauses = [
            HubAiTask.target.like(like),
            HubAiTask.category_label.like(like),
        ]
        if creator_ids:
            clauses.append(HubAiTask.created_by.in_(creator_ids))
        query = query.filter(or_(*clauses))
    return query


def select_user_ids_by_keyword(db: Session, like: str) -> List[int]:
    rows = (
        db.query(User.id)
        .filter(or_(User.full_name.like(like), User.username.like(like)))
        .all()
    )
    return [row[0] for row in rows]


def count_tasks(
    db: Session,
    project_id: int,
    task_type: str,
    **filters,
) -> int:
    return _filtered_query(db, project_id, task_type, **filters).count()


def list_tasks_page(
    db: Session,
    project_id: int,
    task_type: str,
    page: int,
    page_size: int,
    **filters,
) -> List[HubAiTask]:
    return (
        _filtered_query(db, project_id, task_type, **filters)
        .order_by(HubAiTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


def get_task(db: Session, task_id: int) -> Optional[HubAiTask]:
    return db.query(HubAiTask).filter(HubAiTask.id == task_id).first()


def count_running_hub_tasks(
    db: Session,
    project_id: int,
    *,
    task_type: Optional[str] = None,
    provider_id: Optional[int] = None,
) -> int:
    query = db.query(HubAiTask).filter(
        HubAiTask.project_id == project_id,
        HubAiTask.status == "running",
        HubAiTask.task_type.in_(("requirement", "functional")),
    )
    if task_type:
        query = query.filter(HubAiTask.task_type == task_type)
    rows = query.all()
    if provider_id is None:
        return len(rows)
    key = provider_queue_key(provider_id)
    return sum(1 for t in rows if task_provider_id(t) == key)


def hub_running_task_capacity_message(
    db: Session,
    project_id: int,
    *,
    creating_task_type: Optional[str] = None,
    provider_id: Optional[int] = None,
) -> Optional[str]:
    slot_key = provider_queue_key(provider_id)
    if creating_task_type == "functional":
        n_fn = count_running_hub_tasks(
            db, project_id, task_type="functional", provider_id=slot_key
        )
        if n_fn >= MAX_CONCURRENT_FUNCTIONAL_HUB_TASKS:
            return (
                f"当前项目已有 {n_fn} 个同模型 AI 用例生成任务进行中，请等待完成后再试"
                f"（同模型同时仅支持 {MAX_CONCURRENT_FUNCTIONAL_HUB_TASKS} 个）"
            )
    if creating_task_type == "requirement":
        n_req = count_running_hub_tasks(
            db, project_id, task_type="requirement", provider_id=slot_key
        )
        if n_req >= MAX_CONCURRENT_REQUIREMENT_HUB_TASKS:
            return (
                f"当前项目已有 {n_req} 个同模型 AI 需求解析任务进行中，请等待完成后再试"
                f"（同模型同时仅支持 {MAX_CONCURRENT_REQUIREMENT_HUB_TASKS} 个）"
            )
    n = count_running_hub_tasks(db, project_id)
    if n >= MAX_CONCURRENT_RUNNING_HUB_TASKS:
        return (
            f"当前项目已有 {n} 个 AI 任务进行中，请等待完成后再试"
            f"（上限 {MAX_CONCURRENT_RUNNING_HUB_TASKS} 个）"
        )
    return None


def _create_requirement_from_extract_fields(
    db: Session,
    *,
    project_id: int,
    created_by_id: Optional[int],
    title: str,
    description: Optional[str],
    req_type: str,
    priority: str,
) -> Requirement:
    req = Requirement(
        project_id=project_id,
        title=normalize_req_case_title(title or "", default="未命名需求点"),
        description=description,
        req_type=req_type or "functional",
        priority=priority or "P1",
        status="draft",
        source="ai_document",
        sort_order=next_requirement_sort_order(db, project_id),
        created_by_id=created_by_id,
    )
    db.add(req)
    db.flush()
    return req


def _mark_requirement_hub_row_imported(
    row: HubAiTaskRequirementItem,
    requirement_id: int,
    *,
    imported_at: Optional[datetime] = None,
) -> None:
    row.requirement_id = requirement_id
    row.imported_at = imported_at or datetime.utcnow()


def _import_requirement_hub_row(
    db: Session,
    task: HubAiTask,
    row: HubAiTaskRequirementItem,
) -> int:
    """将任务明细行写入 requirements 表并标记已入库，返回 requirement id。"""
    if row.requirement_id:
        if row.imported_at is None:
            row.imported_at = datetime.utcnow()
        return row.requirement_id
    req = _create_requirement_from_extract_fields(
        db,
        project_id=task.project_id,
        created_by_id=task.created_by,
        title=row.title,
        description=row.description,
        req_type=row.req_type,
        priority=row.priority,
    )
    _mark_requirement_hub_row_imported(row, req.id)
    return req.id


def sync_unimported_requirement_items(
    db: Session,
    task_id: int,
    *,
    limit: int = SYNC_REQUIREMENT_IMPORT_BATCH,
) -> int:
    """补入库：流式已写入明细但未标记 imported 的行（兼容旧任务 / 中断部署）。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task or task.task_type != "requirement":
        return 0
    batch_size = max(1, min(limit, 50))
    pending = (
        db.query(HubAiTaskRequirementItem)
        .filter(
            HubAiTaskRequirementItem.task_id == task_id,
            HubAiTaskRequirementItem.imported_at.is_(None),
            HubAiTaskRequirementItem.requirement_id.is_(None),
        )
        .order_by(HubAiTaskRequirementItem.sort_order, HubAiTaskRequirementItem.id)
        .limit(batch_size)
        .all()
    )
    if not pending:
        return 0
    for row in pending:
        _import_requirement_hub_row(db, task, row)
    applied = requirement_applied_count(db, task_id)
    task.applied_total = applied
    db.commit()
    return len(pending)


def record_requirement_stream_progress(
    db: Session,
    task_id: int,
    *,
    project_id: int,
    created_by_id: Optional[int],
    sort_order: int,
    title: str,
    description: Optional[str] = None,
    req_type: str = "functional",
    priority: str = "P1",
    chunk_index: int = 0,
    chunk_total: int = 0,
    generated_total: int = 0,
) -> Requirement:
    """写入需求点到库、任务明细并更新进度（单次 commit，便于详情轮询读到）。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    req = _create_requirement_from_extract_fields(
        db,
        project_id=project_id,
        created_by_id=created_by_id,
        title=title,
        description=description,
        req_type=req_type,
        priority=priority,
    )
    hub_row = HubAiTaskRequirementItem(
        task_id=task_id,
        sort_order=sort_order,
        title=(title or "")[:500],
        description=description,
        req_type=req_type or "functional",
        priority=priority or "P1",
    )
    _mark_requirement_hub_row_imported(hub_row, req.id)
    db.add(hub_row)
    task.generated_total = generated_total
    task.applied_total = generated_total
    if chunk_total:
        task.done_items = chunk_index
        task.total_items = chunk_total
    _touch_progress(task)
    db.commit()
    db.refresh(req)
    return req


def record_requirement_stream_batch(
    db: Session,
    task_id: int,
    *,
    project_id: int,
    created_by_id: Optional[int],
    items: List[Dict[str, Any]],
    chunk_index: int,
    chunk_total: int,
    generated_total: int,
) -> List[Requirement]:
    """同文档段多条需求点一次 commit，避免 SSE 循环逐条写库阻塞后续 LLM 段。"""
    if not items:
        return []
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    reqs: List[Requirement] = []
    base_order = generated_total - len(items)
    for offset, raw in enumerate(items):
        sort_order = base_order + offset + 1
        title = str(raw.get("title") or "")
        req = _create_requirement_from_extract_fields(
            db,
            project_id=project_id,
            created_by_id=created_by_id,
            title=title,
            description=raw.get("description"),
            req_type=str(raw.get("req_type") or "functional"),
            priority=str(raw.get("priority") or "P1"),
        )
        hub_row = HubAiTaskRequirementItem(
            task_id=task_id,
            sort_order=sort_order,
            title=title[:500],
            description=raw.get("description"),
            req_type=str(raw.get("req_type") or "functional"),
            priority=str(raw.get("priority") or "P1"),
        )
        _mark_requirement_hub_row_imported(hub_row, req.id)
        db.add(hub_row)
        reqs.append(req)
    task.generated_total = generated_total
    task.applied_total = generated_total
    if chunk_total:
        task.done_items = chunk_index
        task.total_items = chunk_total
    _touch_progress(task)
    db.commit()
    for req in reqs:
        db.refresh(req)
    return reqs


def update_chunk_progress(
    db: Session,
    task_id: int,
    *,
    chunk_index: int,
    chunk_total: int,
    generated_total: int,
) -> None:
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task:
        return
    task.done_items = chunk_index
    task.total_items = chunk_total
    task.generated_total = generated_total
    _touch_progress(task)
    db.commit()


def update_requirement_parse_heartbeat(
    db: Session,
    task_id: int,
    *,
    segments_done: int,
    segment_total: int,
    segment_in_flight: int,
    generated_total: int,
    segments_in_flight_count: int = 0,
) -> None:
    """SSE 长等待心跳：刷新 progress_at，并记录正在处理的段号（done_items 仍为已完成段数）。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task:
        return
    task.done_items = segments_done
    task.total_items = segment_total
    task.generated_total = generated_total
    meta: Dict[str, Any] = {}
    if task.meta_json:
        try:
            raw = json.loads(task.meta_json)
            if isinstance(raw, dict):
                meta = raw
        except json.JSONDecodeError:
            meta = {}
    meta["segment_in_flight"] = min(max(segment_in_flight, 1), segment_total or segment_in_flight)
    if segments_in_flight_count > 0:
        meta["segments_in_flight_count"] = segments_in_flight_count
    meta["parse_worker_active"] = True
    meta["parse_worker_at"] = datetime.utcnow().isoformat()
    task.meta_json = json.dumps(meta, ensure_ascii=False)
    # 心跳仅表示 SSE 仍在等 LLM，不算「解析进展」；勿刷新 progress_at，否则僵死回收永远触发不了
    _touch_task(task)
    db.commit()


def fail_stale_running_tasks(
    db: Session,
    *,
    project_id: Optional[int] = None,
    max_minutes: int = HUB_AI_TASK_STALE_MINUTES,
) -> int:
    """将长时间无进展的 running 任务标记为失败；无 worker 的僵尸 running 更快回收。"""
    now = datetime.utcnow()
    progress_cutoff = now - timedelta(minutes=max(1, max_minutes))
    orphan_cutoff = now - timedelta(minutes=max(1, HUB_AI_TASK_ORPHAN_MINUTES))

    query = db.query(HubAiTask).filter(HubAiTask.status == "running")
    if project_id is not None:
        query = query.filter(HubAiTask.project_id == project_id)
    running = query.all()

    stale: List[HubAiTask] = []
    for task in running:
        if task.task_type in HUB_SSE_TASK_TYPES:
            meta = _hub_task_meta(task)
            worker_at = _parse_worker_at_dt(meta)
            if meta.get("parse_worker_active") and worker_at and worker_at >= orphan_cutoff:
                progress_stale = (
                    task.progress_at < progress_cutoff
                    if task.progress_at is not None
                    else task.updated_at < progress_cutoff
                )
                if progress_stale:
                    stale.append(task)
                continue
            if task.updated_at < orphan_cutoff:
                stale.append(task)
            continue
        progress_stale = (
            task.progress_at < progress_cutoff
            if task.progress_at is not None
            else task.updated_at < progress_cutoff
        )
        if progress_stale:
            stale.append(task)

    if not stale:
        return 0
    msg = f"任务超过 {max_minutes} 分钟无进展，已自动停止（连接中断或服务重启等）"
    orphan_msg = (
        f"任务超过 {HUB_AI_TASK_ORPHAN_MINUTES} 分钟无后台执行心跳，已自动停止（页面已关闭或进程中断）"
    )
    for task in stale:
        has_output = (task.generated_total or 0) > 0 or (task.applied_total or 0) > 0
        meta = _hub_task_meta(task)
        worker_at = _parse_worker_at_dt(meta)
        is_orphan = task.task_type in HUB_SSE_TASK_TYPES and not (
            meta.get("parse_worker_active") and worker_at and worker_at >= orphan_cutoff
        )
        err = orphan_msg if is_orphan else msg
        if task.task_type == "requirement" and has_output:
            task.status = "partial"
            task.error = task.error or f"{err}，已保留已提取的 {task.generated_total or 0} 条需求点"
        else:
            task.status = "failed" if not has_output else "partial"
            task.error = task.error or (f"{err}，已保留已生成 {task.generated_total or 0} 条" if has_output else err)
        task.finished_at = task.finished_at or now
        _touch_task(task)
    db.commit()
    promoted: set[tuple[str, int]] = set()
    for task in stale:
        if task.task_type in HUB_SSE_TASK_TYPES:
            promoted.add((task.task_type, task_provider_id(task)))
    for task_type, slot_provider in promoted:
        promote_next_pending_hub_task(db, task_type, slot_provider)
    return len(stale)


def record_functional_case_progress(
    db: Session,
    task_id: int,
    *,
    sort_order: int,
    testcase_id: int,
    done_items: int,
    generated_total: int,
    total_items: int,
) -> None:
    db.add(
        HubAiTaskCaseItem(
            task_id=task_id,
            sort_order=sort_order,
            testcase_id=testcase_id,
        )
    )
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if task:
        task.done_items = done_items
        task.generated_total = generated_total
        task.total_items = total_items
        task.applied_total = generated_total
        _touch_progress(task)
    db.commit()


def add_applied_import(
    db: Session,
    task_id: int,
    *,
    project_id: int,
    imported_count: int,
) -> None:
    """兼容旧逻辑：按条数累加（用例任务等）。"""
    if imported_count <= 0:
        return
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task or task.project_id != project_id:
        return
    cap = max(task.generated_total, 0)
    task.applied_total = min(cap, (task.applied_total or 0) + imported_count)
    _touch_task(task)
    db.commit()


def mark_requirements_imported(
    db: Session,
    task_id: int,
    *,
    project_id: int,
    titles: List[str],
) -> None:
    """批量导入后标记任务内需求点明细已入库，并同步 applied_total。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task or task.project_id != project_id or task.task_type != "requirement":
        return
    title_set = {t.strip() for t in titles if t and t.strip()}
    if not title_set:
        return
    now = datetime.utcnow()
    rows = (
        db.query(HubAiTaskRequirementItem)
        .filter(HubAiTaskRequirementItem.task_id == task_id)
        .all()
    )
    for row in rows:
        if row.title.strip() in title_set and row.imported_at is None:
            row.imported_at = now
    task.applied_total = (
        db.query(HubAiTaskRequirementItem)
        .filter(
            HubAiTaskRequirementItem.task_id == task_id,
            HubAiTaskRequirementItem.imported_at.isnot(None),
        )
        .count()
    )
    _touch_task(task)
    db.commit()


def requirement_applied_count(db: Session, task_id: int) -> int:
    return (
        db.query(HubAiTaskRequirementItem)
        .filter(
            HubAiTaskRequirementItem.task_id == task_id,
            or_(
                HubAiTaskRequirementItem.imported_at.isnot(None),
                HubAiTaskRequirementItem.requirement_id.isnot(None),
            ),
        )
        .count()
    )


def list_requirement_items(db: Session, task_id: int) -> List[Dict[str, Any]]:
    sync_unimported_requirement_items(db, task_id)
    rows = (
        db.query(HubAiTaskRequirementItem)
        .filter(HubAiTaskRequirementItem.task_id == task_id)
        .order_by(HubAiTaskRequirementItem.sort_order, HubAiTaskRequirementItem.id)
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "req_type": r.req_type,
            "priority": r.priority,
            "requirement_id": r.requirement_id,
            "imported_at": r.imported_at,
        }
        for r in rows
    ]


def list_requirement_items_page(
    db: Session, task_id: int, *, page: int, page_size: int
) -> tuple[List[Dict[str, Any]], int]:
    sync_unimported_requirement_items(db, task_id)
    base = db.query(HubAiTaskRequirementItem).filter(HubAiTaskRequirementItem.task_id == task_id)
    total = base.count()
    rows = (
        base.order_by(HubAiTaskRequirementItem.sort_order, HubAiTaskRequirementItem.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "req_type": r.req_type,
            "priority": r.priority,
            "requirement_id": r.requirement_id,
            "imported_at": r.imported_at,
        }
        for r in rows
    ]
    return items, total


def list_case_items(db: Session, task_id: int) -> List[Dict[str, Any]]:
    links = (
        db.query(HubAiTaskCaseItem)
        .filter(HubAiTaskCaseItem.task_id == task_id)
        .order_by(HubAiTaskCaseItem.sort_order, HubAiTaskCaseItem.id)
        .all()
    )
    return _hydrate_case_items_from_links(db, links)


def _hydrate_case_items_from_links(
    db: Session, links: List[HubAiTaskCaseItem]
) -> List[Dict[str, Any]]:
    from app.models.requirement import Requirement

    if not links:
        return []
    case_ids = [link.testcase_id for link in links]
    cases = {c.id: c for c in db.query(TestCase).filter(TestCase.id.in_(case_ids)).all()}
    req_titles: Dict[int, str] = {}
    req_ids = [c.requirement_id for c in cases.values() if c.requirement_id]
    if req_ids:
        for req in db.query(Requirement.id, Requirement.title).filter(Requirement.id.in_(req_ids)).all():
            req_titles[req[0]] = req[1]
    out: List[Dict[str, Any]] = []
    for link in links:
        case = cases.get(link.testcase_id)
        if not case:
            continue
        out.append(
            {
                "id": case.id,
                "link_id": link.id,
                "title": case.title,
                "case_type": case.case_type,
                "priority": case.priority,
                "preconditions": case.preconditions,
                "steps": case.steps,
                "expected_results": case.expected_results,
                "tags": case.tags,
                "requirement_title": req_titles.get(case.requirement_id or 0, ""),
                "review_status": case.review_status,
            }
        )
    return out


def list_case_items_page(
    db: Session, task_id: int, *, page: int, page_size: int
) -> tuple[List[Dict[str, Any]], int]:
    filt = HubAiTaskCaseItem.task_id == task_id
    total = db.query(HubAiTaskCaseItem).filter(filt).count()
    links = (
        db.query(HubAiTaskCaseItem)
        .filter(filt)
        .order_by(HubAiTaskCaseItem.sort_order, HubAiTaskCaseItem.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return _hydrate_case_items_from_links(db, links), total


def discard_requirement_items(
    db: Session,
    task_id: int,
    *,
    project_id: int,
    item_ids: List[int],
) -> int:
    """从任务明细中废弃未入库的需求点草稿（物理删除）。"""
    task = db.query(HubAiTask).filter(HubAiTask.id == task_id).first()
    if not task or task.project_id != project_id or task.task_type != "requirement":
        return 0
    unique_ids = list(dict.fromkeys(item_ids))
    if not unique_ids:
        return 0
    rows = (
        db.query(HubAiTaskRequirementItem)
        .filter(
            HubAiTaskRequirementItem.task_id == task_id,
            HubAiTaskRequirementItem.id.in_(unique_ids),
        )
        .all()
    )
    removed = 0
    for row in rows:
        if row.imported_at is not None or row.requirement_id is not None:
            continue
        db.delete(row)
        removed += 1
    if removed:
        remaining = (
            db.query(HubAiTaskRequirementItem)
            .filter(HubAiTaskRequirementItem.task_id == task_id)
            .count()
        )
        task.generated_total = remaining
        _touch_task(task)
        db.commit()
    return removed


def task_brief(db: Session, task: HubAiTask) -> Dict[str, Any]:
    creator_name = ""
    if task.created_by:
        user = db.query(User).filter(User.id == task.created_by).first()
        creator_name = (user.username or user.full_name or "") if user else ""
    applied_total = task.applied_total or 0
    if task.task_type == "requirement":
        applied_total = requirement_applied_count(db, task.id)
    return {
        "id": task.id,
        "project_id": task.project_id,
        "task_type": task.task_type,
        "status": task.status,
        "target": task.target,
        "category_label": task.category_label,
        "model_label": hub_task_model_label(db, task),
        "total_items": task.total_items,
        "done_items": task.done_items,
        "generated_total": task.generated_total,
        "applied_total": applied_total,
        "error": task.error,
        "creator_name": creator_name,
        "created_at": task.created_at,
        "finished_at": task.finished_at,
    }
