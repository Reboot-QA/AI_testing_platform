"""Apifox 定时任务 · 调度线程宿主（单例守护线程 + 启停 + 启动初始化）。

迁移自老 schedule_service：仅驱动 apifox 定时任务（老 ApiScheduledTask 已随老模块退休）。
沿用既有并发范式：轮询单例线程、每轮独立 session、循环异常 try/except 兜住不打死线程。
run_due_apifox_tasks 延迟 import，避免顶层 循环 import。
"""

import logging
import threading
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 15

_scheduler_thread: Optional[threading.Thread] = None
_scheduler_stop = threading.Event()
# 回收站到期清理每日至多一次：记录上次清理的日期（进程内），跨天才再扫
_last_trash_sweep: Optional[date] = None


def _maybe_sweep_trash(db: Session) -> None:
    global _last_trash_sweep
    today = date.today()
    if _last_trash_sweep == today:
        return
    from app.services.apifox import run_retention_service, trash_service

    purged = trash_service.purge_expired(db)
    _last_trash_sweep = today
    if purged:
        logger.info("回收站到期清理：彻底删除 %s 项", purged)
    run_retention_service.purge_expired_case_runs(db)


def _scheduler_thread_loop() -> None:
    logger.info("apifox 定时任务调度线程已启动，检查间隔 %s 秒", CHECK_INTERVAL_SECONDS)
    while not _scheduler_stop.is_set():
        db = SessionLocal()
        try:
            from app.services.apifox.import_schedule_service import run_due_import_schedules
            from app.services.apifox.schedule_service import run_due_apifox_tasks

            run_due_apifox_tasks(db)
            run_due_import_schedules(db)
            _maybe_sweep_trash(db)
        except Exception:  # noqa: BLE001 - 调度循环异常不得打死线程
            logger.exception("apifox 定时任务调度循环异常")
        finally:
            db.close()
        _scheduler_stop.wait(CHECK_INTERVAL_SECONDS)


def start_scheduler() -> None:
    global _scheduler_thread
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_thread_loop, daemon=True, name="apifox-schedule-worker"
    )
    _scheduler_thread.start()
    logger.info("apifox 定时任务调度器已启动")


def stop_scheduler() -> None:
    global _scheduler_thread
    _scheduler_stop.set()
    if _scheduler_thread is not None:
        _scheduler_thread.join(timeout=5)
        _scheduler_thread = None


def init_schedules_on_startup(db: Session) -> None:
    """启动时给缺 next_run_at 的启用中 apifox 定时任务补算下次运行（过期者由 run_due 补跑）。

    老 schedule_service 的一次性 UTC→本地时间迁移（_migrate_api_automation_utc_to_local）
    只作用于老 ApiTestRun/ApiScheduledTask（老模块已下线、老表归档不再展示），故意不迁入。
    """
    from app.models.apifox.schedule import ApifoxSchedule
    from app.services.apifox import import_schedule_service, schedule_service

    tasks = db.query(ApifoxSchedule).filter(ApifoxSchedule.enabled.is_(True)).all()
    changed = False
    for task in tasks:
        if not task.next_run_at:
            try:
                task.next_run_at = schedule_service._compute_next(task)
                changed = True
            except Exception:  # noqa: BLE001 - 单条坏数据（如非法 cron）不阻塞启动
                logger.exception("apifox 定时任务 %s 启动初始化失败", task.id)
    if changed:
        db.commit()
    import_schedule_service.init_on_startup(db)
