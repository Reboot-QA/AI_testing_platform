"""Apifox AI 生成任务 · 后台执行线程（单例守护线程，独立于 HTTP 连接 → 进度可恢复）。

沿用 scheduler.py 并发范式：轮询、每轮独立 session、循环异常 try/except 兜住不打死线程。
任务内**顺序**处理各接口（DB 写单线程安全、进度逐条可见）；并发扇出限流留作后续优化。
状态严格 try/finally 兜底写终态，避免抛异常即永久卡 running（并发规范 #5）。
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.apifox.ai_gen_task import ApifoxAiGenTask, ApifoxAiGenTaskItem
from app.repositories.apifox import ai_gen_task_repo as repo
from app.repositories.apifox import endpoint_repo
from app.routers.apifox.case_schemas import AiGenCategory
from app.services.apifox import ai_case_service
from app.services.apifox import ai_gen_task_service as service
from app.services.settings_service import get_effective_llm_config

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 3

_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()


def _process_item(
    db: Session,
    item: ApifoxAiGenTaskItem,
    categories: List[AiGenCategory],
    llm_config: dict,
) -> None:
    endpoint = endpoint_repo.get_endpoint(db, item.endpoint_id)
    if not endpoint:
        item.status = "failed"
        item.error = "接口不存在"
        return
    item.status = "running"
    db.commit()
    try:
        cases, _mode = asyncio.run(
            ai_case_service.generate_cases(db, endpoint, categories, llm_config)
        )
        item.result_cases = service.dump_cases(cases)
        item.generated_count = len(cases)
        item.status = "succeeded"
        item.error = None
    except Exception as exc:  # noqa: BLE001 - 单接口失败隔离，不影响同任务其它接口
        item.status = "failed"
        item.error = str(exc)[:1000]
        logger.warning("AI 生成任务 item %s 失败: %s", item.id, exc)


def _finalize(db: Session, task: ApifoxAiGenTask) -> None:
    db.refresh(task)
    if task.status != "canceled":
        items = repo.list_items(db, task.id)
        ok = sum(1 for i in items if i.status == "succeeded")
        bad = sum(1 for i in items if i.status == "failed")
        task.status = "succeeded" if ok and not bad else "failed" if bad and not ok else "partial"
    task.finished_at = datetime.utcnow()
    db.commit()


def _process_task(db: Session, task: ApifoxAiGenTask) -> None:
    task.status = "running"
    db.commit()
    llm_config = get_effective_llm_config(db, task.provider_id)
    task.mode = "mock" if llm_config["mock_mode"] else "llm"
    db.commit()
    categories = service.load_categories(task.categories)

    for item in repo.list_items(db, task.id):
        db.refresh(task)
        if task.status == "canceled":  # 运行中被取消 → 停止处理剩余接口
            break
        if item.status != "pending":
            continue
        _process_item(db, item, categories, llm_config)
        task.done_items += 1
        db.commit()

    _finalize(db, task)


def _run_due(db: Session) -> None:
    task = repo.claim_next_pending(db)
    if not task:
        return
    try:
        _process_task(db, task)
    except Exception:  # noqa: BLE001 - 兜底写失败态，杜绝永久卡 running
        logger.exception("AI 生成任务 %s 执行异常", task.id)
        db.rollback()
        task.status = "failed"
        task.error = "任务执行异常，请重试"
        task.finished_at = datetime.utcnow()
        db.commit()


def _worker_loop() -> None:
    logger.info("apifox AI 生成任务 worker 已启动，轮询间隔 %s 秒", CHECK_INTERVAL_SECONDS)
    while not _worker_stop.is_set():
        db = SessionLocal()
        try:
            _run_due(db)
        except Exception:  # noqa: BLE001 - 轮询异常不得打死线程
            logger.exception("apifox AI 生成任务 worker 轮询异常")
        finally:
            db.close()
        _worker_stop.wait(CHECK_INTERVAL_SECONDS)


def start_ai_gen_worker() -> None:
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    _worker_stop.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop, daemon=True, name="apifox-ai-gen-worker"
    )
    _worker_thread.start()
    logger.info("apifox AI 生成任务 worker 已启动")


def stop_ai_gen_worker() -> None:
    global _worker_thread
    _worker_stop.set()
    if _worker_thread is not None:
        _worker_thread.join(timeout=5)
        _worker_thread = None


def init_ai_gen_tasks_on_startup(db: Session) -> None:
    """启动恢复：残留 running（上次进程崩溃）重置 pending，交由 worker 重跑。"""
    n = repo.reset_running_to_pending(db)
    if n:
        db.commit()
        logger.info("重置 %s 个残留 running 的 AI 生成任务为 pending", n)
