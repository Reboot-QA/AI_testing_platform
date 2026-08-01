"""Apifox AI 生成任务 · 后台执行线程（单例守护线程，独立于 HTTP 连接 → 进度可恢复）。

沿用 scheduler.py 并发范式：轮询、每轮独立 session、循环异常 try/except 兜住不打死线程。
任务内**并发扇出** LLM 生成（信号量限流）：先同步建各接口计划（DB 读），再纯异步并发调 LLM、
完成一条写一条（写库全在单事件循环单 session 串行，协程不碰 db）。
状态严格 try/finally 兜底写终态，避免抛异常即永久卡 running（并发规范 #5）。
"""

import asyncio
import logging
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.apifox.ai_gen_task import ApifoxAiGenTask
from app.repositories.apifox import ai_gen_task_repo as repo
from app.repositories.apifox import endpoint_repo
from app.services.apifox import ai_case_service
from app.services.apifox import ai_gen_task_service as service
from app.services.settings_service import get_ai_gen_concurrency, get_effective_llm_config

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 3

_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()


_MAX_LLM_ATTEMPTS = 2  # 生成失败（LLM 超时/网络抖动/偶发格式）自动重试一次


async def _run_gen_with_retry(
    plan,
    llm_config: dict,
    endpoint_id: int,
    on_batch,
):
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_LLM_ATTEMPTS + 1):
        try:
            cases, _mode = await ai_case_service.run_gen_plan_incremental(
                plan, llm_config, on_batch
            )
            return cases
        except Exception as exc:  # noqa: BLE001 - 可重试：超时/抖动/LLM 偶发返回
            last_exc = exc
            logger.warning("AI 生成 item(endpoint %s) 第 %s 次失败: %s", endpoint_id, attempt, exc)
    raise last_exc  # type: ignore[misc]


async def _run_concurrent(db: Session, task: ApifoxAiGenTask, plans: dict, llm_config: dict) -> None:
    """并发跑各接口的 LLM 生成（信号量限流）；完成一条写一条。

    协程内**只做纯 LLM 调用**（不碰 db）；结果写库全在本 as_completed 主循环里串行执行，
    单事件循环单 session，无并发访问 session（并发规范：DB session 不共享）。
    """
    # 并发上限：全局设置优先、缺省回退 env（可在系统管理页调整，无需重启）
    sem = asyncio.Semaphore(get_ai_gen_concurrency(db))
    canceled = {"flag": False}

    async def _one(item_id: int, plan):
        async with sem:
            if canceled["flag"]:
                return item_id, None, "任务已取消"
            item = repo.get_item(db, item_id)
            if item and item.status == "pending":
                item.status = "running"
                db.commit()
            accumulated: list = []

            def on_batch(batch) -> None:
                accumulated.extend(batch)
                it = repo.get_item(db, item_id)
                if it is None:
                    return
                it.result_cases = service.dump_cases(accumulated)
                it.generated_count = len(accumulated)
                it.status = "running"
                db.commit()

            try:
                cases = await _run_gen_with_retry(plan, llm_config, item_id, on_batch)
                return item_id, cases, None
            except Exception as exc:  # noqa: BLE001 - 单接口失败隔离
                return item_id, None, str(exc)

    coros = [asyncio.create_task(_one(iid, p)) for iid, p in plans.items()]
    for fut in asyncio.as_completed(coros):
        item_id, cases, error = await fut
        item = repo.get_item(db, item_id)
        if item is None:
            continue
        if cases is not None:
            item.result_cases = service.dump_cases(cases)
            item.generated_count = len(cases)
            item.status = "succeeded"
            item.error = None
        else:
            item.status = "failed"
            item.error = (error or "生成失败")[:1000]
            logger.warning("AI 生成任务 item %s 最终失败: %s", item_id, error)
        task.done_items += 1
        db.commit()
        db.refresh(task)
        if task.status == "canceled":  # 运行中被取消 → 不再启动排队中的接口
            canceled["flag"] = True


def _finalize(db: Session, task: ApifoxAiGenTask) -> None:
    db.refresh(task)
    if task.status != "canceled":
        items = repo.list_items(db, task.id)
        ok = sum(1 for i in items if i.status == "succeeded")
        bad = sum(1 for i in items if i.status == "failed")
        task.status = "succeeded" if ok and not bad else "failed" if bad and not ok else "partial"
    task.finished_at = datetime.utcnow()
    db.commit()
    if task.status != "canceled":  # 成功/失败/部分 各按开关推送；取消不通知
        _notify_task(db, task)


def _notify_task(db: Session, task: ApifoxAiGenTask) -> None:
    """AI 生成任务完成通知（成功/失败按开关分别推送；partial 归为失败）。"""
    from app.services.apifox import notify_service  # 延迟导入避免顶层循环
    from app.services.apifox.notify_templates import NotifyPayload

    try:
        items = repo.list_items(db, task.id)
        ok = sum(1 for i in items if i.status == "succeeded")
        bad = sum(1 for i in items if i.status == "failed")
        total = task.total_items or len(items)
        stats = f"{ok}/{total} 个接口生成成功"
        if bad:
            stats += f"，{bad} 个失败"
        payload = NotifyPayload(
            event_type="aigen",
            result="success" if task.status == "succeeded" else "failure",
            project_name=notify_service.project_name(db, task.project_id),
            scene="AI 生成任务",
            stats_text=stats,
            ref_id=task.id,
            ref_label="任务",
            happened_at=task.finished_at,
        )
        notify_service.notify_event(db, task.project_id, payload)
    except Exception:  # noqa: BLE001 - 通知不影响主流程
        logger.exception("AI 生成通知异常 task=%s", task.id)


def _process_task(db: Session, task: ApifoxAiGenTask) -> None:
    task.status = "running"
    db.commit()
    llm_config = get_effective_llm_config(db, task.provider_id)
    task.mode = "mock" if llm_config["mock_mode"] else "llm"
    db.commit()
    categories = service.load_categories(task.categories)

    # 1) 同步阶段：逐接口构建生成计划（DB 读）；接口缺失/建计划失败即定终态
    plans: dict = {}
    for item in repo.list_items(db, task.id):
        if item.status != "pending":
            continue
        endpoint = endpoint_repo.get_endpoint(db, item.endpoint_id)
        if not endpoint:
            item.status = "failed"
            item.error = "接口不存在"
            task.done_items += 1
            continue
        try:
            plans[item.id] = ai_case_service.build_gen_plan(db, endpoint, categories, llm_config)
        except Exception as exc:  # noqa: BLE001 - 单接口建计划失败隔离
            item.status = "failed"
            item.error = str(exc)[:1000]
            task.done_items += 1
    db.commit()

    # 2) 并发阶段：限流扇出 LLM 调用，完成一条写一条
    if plans:
        asyncio.run(_run_concurrent(db, task, plans, llm_config))

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
