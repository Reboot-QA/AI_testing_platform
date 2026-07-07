import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.api_automation import ApiScheduledTask, ApiScheduledTaskSuite, ApiTestRun, ApiTestSuite
from app.models.system_setting import SystemSetting
from app.services.api_runner_service import run_api_suite
from app.utils.time_util import local_utc_offset, now_local, utc_naive_to_local

logger = logging.getLogger(__name__)

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
SCHEDULE_TYPES = {"daily", "weekly", "interval"}
MIN_INTERVAL_MINUTES = 5
CHECK_INTERVAL_SECONDS = 15

_scheduler_thread: Optional[threading.Thread] = None
_scheduler_stop = threading.Event()


def _parse_run_time(run_time: str) -> Tuple[int, int]:
    parts = (run_time or "09:00").strip().split(":")
    hour = int(parts[0]) if parts else 9
    minute = int(parts[1]) if len(parts) > 1 else 0
    return max(0, min(23, hour)), max(0, min(59, minute))


def format_schedule_desc(task: ApiScheduledTask) -> str:
    if task.schedule_type == "daily":
        return f"每天 {task.run_time or '09:00'}"
    if task.schedule_type == "weekly":
        day = task.week_day if task.week_day is not None else 0
        day_label = WEEKDAY_LABELS[day] if 0 <= day <= 6 else "周一"
        return f"每{day_label} {task.run_time or '09:00'}"
    minutes = max(MIN_INTERVAL_MINUTES, task.interval_minutes or MIN_INTERVAL_MINUTES)
    return f"每 {minutes} 分钟"


def compute_next_run_at(task: ApiScheduledTask, from_dt: Optional[datetime] = None) -> datetime:
    now = (from_dt or now_local()).replace(microsecond=0)
    hour, minute = _parse_run_time(task.run_time)

    if task.schedule_type == "interval":
        interval = max(MIN_INTERVAL_MINUTES, task.interval_minutes or MIN_INTERVAL_MINUTES)
        if task.last_run_at:
            base = task.last_run_at.replace(microsecond=0)
            candidate = base + timedelta(minutes=interval)
            return candidate if candidate > now else now + timedelta(minutes=interval)
        return now + timedelta(minutes=interval)

    if task.schedule_type == "weekly":
        target_weekday = task.week_day if task.week_day is not None else 0
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (target_weekday - candidate.weekday()) % 7
        if days_ahead == 0 and candidate <= now:
            days_ahead = 7
        return candidate + timedelta(days=days_ahead)

    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def refresh_task_schedule(db: Session, task: ApiScheduledTask, *, force_from_now: bool = False) -> None:
    if task.enabled:
        base = now_local() if force_from_now else None
        task.next_run_at = compute_next_run_at(task, from_dt=base)
    else:
        task.next_run_at = None
    db.commit()
    db.refresh(task)


def validate_schedule_fields(
    *,
    schedule_type: str,
    run_time: Optional[str] = None,
    week_day: Optional[int] = None,
    interval_minutes: Optional[int] = None,
) -> None:
    if schedule_type not in SCHEDULE_TYPES:
        raise ValueError("调度类型无效，支持 daily / weekly / interval")
    if schedule_type in {"daily", "weekly"}:
        _parse_run_time(run_time or "09:00")
    if schedule_type == "weekly" and week_day is not None and not (0 <= week_day <= 6):
        raise ValueError("week_day 必须在 0-6 之间（0=周一）")
    if schedule_type == "interval":
        minutes = interval_minutes or MIN_INTERVAL_MINUTES
        if minutes < MIN_INTERVAL_MINUTES:
            raise ValueError(f"间隔执行最少 {MIN_INTERVAL_MINUTES} 分钟")


def get_scheduled_task_suite_ids(db: Session, task: ApiScheduledTask) -> List[int]:
    rows = (
        db.query(ApiScheduledTaskSuite)
        .filter(ApiScheduledTaskSuite.task_id == task.id)
        .order_by(ApiScheduledTaskSuite.sort_order.asc(), ApiScheduledTaskSuite.id.asc())
        .all()
    )
    if rows:
        return [row.suite_id for row in rows]
    if task.suite_id:
        return [task.suite_id]
    return []


def get_scheduled_task_suites(db: Session, task: ApiScheduledTask) -> List[ApiTestSuite]:
    suites: List[ApiTestSuite] = []
    for suite_id in get_scheduled_task_suite_ids(db, task):
        suite = db.query(ApiTestSuite).filter(ApiTestSuite.id == suite_id).first()
        if suite:
            suites.append(suite)
    return suites


def replace_scheduled_task_suites(db: Session, task: ApiScheduledTask, suite_ids: List[int]) -> None:
    unique_ids: List[int] = []
    for suite_id in suite_ids:
        if suite_id not in unique_ids:
            unique_ids.append(suite_id)
    db.query(ApiScheduledTaskSuite).filter(ApiScheduledTaskSuite.task_id == task.id).delete()
    for index, suite_id in enumerate(unique_ids):
        db.add(
            ApiScheduledTaskSuite(
                task_id=task.id,
                suite_id=suite_id,
                sort_order=index,
            )
        )
    task.suite_id = unique_ids[0] if unique_ids else None


def execute_scheduled_task(db: Session, task: ApiScheduledTask) -> None:
    suites = get_scheduled_task_suites(db, task)
    if not suites:
        logger.warning("定时任务 %s 关联套件不存在", task.id)
        task.next_run_at = compute_next_run_at(task) if task.enabled else None
        db.commit()
        return

    last_run: Optional[ApiTestRun] = None
    overall_status = "passed"
    for suite in suites:
        try:
            run = run_api_suite(db, suite, triggered_by=f"schedule:{task.name}")
            last_run = run
            if run.status != "passed":
                overall_status = run.status
        except Exception as exc:
            logger.exception("定时任务 %s 执行套件 %s 失败: %s", task.id, suite.id, exc)
            overall_status = "failed"

    task.last_run_at = now_local()
    task.last_run_id = last_run.id if last_run else None
    task.last_run_status = overall_status
    if last_run:
        logger.info(
            "定时任务 %s (%s) 执行完成: run_id=%s status=%s suites=%s",
            task.id,
            task.name,
            last_run.id,
            overall_status,
            len(suites),
        )
    if task.enabled:
        task.next_run_at = compute_next_run_at(task)
    db.commit()


def run_due_tasks(db: Session) -> int:
    now = now_local()
    due_tasks = (
        db.query(ApiScheduledTask)
        .filter(
            ApiScheduledTask.enabled.is_(True),
            ApiScheduledTask.next_run_at.isnot(None),
            ApiScheduledTask.next_run_at <= now,
        )
        .all()
    )
    if due_tasks:
        logger.info("发现 %s 个到期定时任务 (当前本地时间 %s)", len(due_tasks), now.strftime("%Y-%m-%d %H:%M:%S"))
    for task in due_tasks:
        execute_scheduled_task(db, task)
    return len(due_tasks)


def _scheduler_thread_loop() -> None:
    logger.info("定时任务调度线程已启动，检查间隔 %s 秒", CHECK_INTERVAL_SECONDS)
    while not _scheduler_stop.is_set():
        db = SessionLocal()
        try:
            run_due_tasks(db)
        except Exception:
            logger.exception("定时任务调度循环异常")
        finally:
            db.close()
        _scheduler_stop.wait(CHECK_INTERVAL_SECONDS)


def start_scheduler() -> None:
    global _scheduler_thread
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_thread_loop, daemon=True, name="api-schedule-worker")
    _scheduler_thread.start()
    logger.info("接口自动化定时任务调度器已启动")


def stop_scheduler() -> None:
    global _scheduler_thread
    _scheduler_stop.set()
    if _scheduler_thread is not None:
        _scheduler_thread.join(timeout=5)
        _scheduler_thread = None


def _migrate_api_automation_utc_to_local(db: Session) -> None:
    key = "api_automation_utc_to_local_v1"
    if db.query(SystemSetting).filter(SystemSetting.key == key).first():
        return

    if local_utc_offset() == timedelta(0):
        db.add(SystemSetting(key=key, value="skipped_utc"))
        db.commit()
        return

    for run in db.query(ApiTestRun).all():
        if run.started_at:
            run.started_at = utc_naive_to_local(run.started_at)
        if run.finished_at:
            run.finished_at = utc_naive_to_local(run.finished_at)

    for task in db.query(ApiScheduledTask).all():
        if task.last_run_at:
            task.last_run_at = utc_naive_to_local(task.last_run_at)
        if task.enabled:
            task.next_run_at = compute_next_run_at(task, from_dt=now_local())
        else:
            task.next_run_at = None

    db.add(SystemSetting(key=key, value="done"))
    db.commit()
    logger.info("接口自动化历史时间已从 UTC 迁移为本地时间")


def init_schedules_on_startup(db: Session) -> None:
    _migrate_api_automation_utc_to_local(db)
    tasks = db.query(ApiScheduledTask).filter(ApiScheduledTask.enabled.is_(True)).all()
    changed = False
    now = now_local()
    for task in tasks:
        if not task.next_run_at:
            task.next_run_at = compute_next_run_at(task)
            changed = True
        elif task.next_run_at <= now:
            # 重启后补跑已过期的任务（next_run_at 保持过期，由 run_due_tasks 立即执行）
            logger.info("定时任务 %s 已过期，等待调度器补跑: %s", task.id, task.next_run_at)
    if changed:
        db.commit()
    # 到期任务由后台调度线程异步执行，避免启动阶段同步跑接口用例阻塞 HTTP 服务
