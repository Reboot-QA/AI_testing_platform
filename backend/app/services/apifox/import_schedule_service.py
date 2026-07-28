"""Apifox 定时导入 · 业务层。

调度算法/校验/描述 duck-typed 复用 apifox schedule_service（只读 schedule_type/run_time/
week_day/interval_minutes/cron_expr/last_run_at）。执行体独立：拉取 URL → 归一化 →
import_sync_service.apply_sync，落 last_run_status/detail。由 scheduler 线程驱动。
"""

import logging

from sqlalchemy.orm import Session

from app.models.apifox.import_schedule import ApifoxImportSchedule
from app.repositories.apifox import import_schedule_repo
from app.services.apifox import import_converters, import_service, import_sync_service, schedule_service
from app.utils.time_util import now_local

logger = logging.getLogger(__name__)

# 校验/下次运行计算/描述直接复用（schedule_service 内部已 cast(Any)，duck-typed 兼容本模型）
validate_fields = schedule_service.validate_fields
describe = schedule_service.describe
_compute_next = schedule_service._compute_next


def refresh_schedule(db: Session, task: ApifoxImportSchedule, *, force_from_now: bool = False) -> None:
    if task.enabled:
        base = now_local() if force_from_now else None
        task.next_run_at = _compute_next(task, from_dt=base)
    else:
        task.next_run_at = None
    db.commit()
    db.refresh(task)


def _load_doc(task: ApifoxImportSchedule) -> dict:
    auth = None
    if task.basic_auth_user:
        auth = (task.basic_auth_user, task.basic_auth_pwd or "")
    headers = import_service.git_token_headers(task.git_token) if task.git_token else None
    raw = import_service.fetch_source(task.url, auth=auth, headers=headers)
    return import_converters.to_openapi3(raw)


def _run_import_once(db: Session, task: ApifoxImportSchedule) -> tuple[str, str]:
    """跑一次定时导入，返回 (status, detail)。异常在外层兜底。"""
    doc = _load_doc(task)
    report = import_sync_service.apply_sync(db, task.project_id, doc, task.delete_unreferenced)
    detail = (
        f"新增 {report.added}、更新 {report.updated}、删除 {report.deleted}、"
        f"保留(被引用) {report.kept_referenced}"
    )
    return "success", detail


def execute_schedule(db: Session, task: ApifoxImportSchedule) -> None:
    """定时导入执行体：失败吞掉记 failed，try/finally 兜底写终态与下次运行，避免拖垮轮询线程。"""
    status, detail = "failed", ""
    try:
        try:
            status, detail = _run_import_once(db, task)
        except Exception as exc:  # noqa: BLE001 - 单次导入异常不得中断轮询线程
            logger.exception("apifox 定时导入 %s 执行异常", task.id)
            db.rollback()
            status, detail = "failed", f"{type(exc).__name__}: {exc}"[:500]
        task.last_run_at = now_local()
        task.last_run_status = status
        task.last_run_detail = detail[:500]
    finally:
        if task.enabled:
            try:
                task.next_run_at = _compute_next(task, from_dt=now_local())
            except Exception:  # noqa: BLE001 - 下次运行算不出（损坏 cron）禁用止损，避免每轮重试
                logger.exception("apifox 定时导入 %s 计算下次运行失败，已禁用以止损", task.id)
                task.enabled = False
                task.next_run_at = None
        db.commit()

    if task.last_run_status == "failed":
        _notify_import_failure(db, task)


def _notify_import_failure(db: Session, task: ApifoxImportSchedule) -> None:
    from app.services.apifox import notify_service  # 延迟导入避免顶层循环

    try:
        detail = f"定时导入「{task.name}」执行失败：{task.last_run_detail or ''}"
        notify_service.notify_failure(
            db, task.project_id, "import_schedule", f"定时导入失败：{task.name}", detail
        )
    except Exception:  # noqa: BLE001 - 通知不影响主流程
        logger.exception("定时导入失败通知异常 task=%s", task.id)


def run_due_import_schedules(db: Session) -> None:
    """轮询线程调用：执行所有到期的定时导入。单条异常隔离，不中断整批。"""
    for task in import_schedule_repo.list_due(db, now_local()):
        try:
            execute_schedule(db, task)
        except Exception:  # noqa: BLE001 - 一条坏数据不得中断其余任务
            logger.exception("apifox 定时导入 %s 处理异常", task.id)
            db.rollback()


def init_on_startup(db: Session) -> None:
    """启动时给缺 next_run_at 的启用中定时导入补算下次运行。"""
    tasks = db.query(ApifoxImportSchedule).filter(ApifoxImportSchedule.enabled.is_(True)).all()
    changed = False
    for task in tasks:
        if not task.next_run_at:
            try:
                task.next_run_at = _compute_next(task)
                changed = True
            except Exception:  # noqa: BLE001 - 单条坏数据不阻塞启动
                logger.exception("apifox 定时导入 %s 启动初始化失败", task.id)
    if changed:
        db.commit()


__all__ = [
    "validate_fields",
    "describe",
    "refresh_schedule",
    "execute_schedule",
    "run_due_import_schedules",
    "init_on_startup",
]
