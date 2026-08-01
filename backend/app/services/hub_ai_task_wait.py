"""Hub 需求/用例 SSE 任务排队等待（与 Apifox AI 生成 pending → worker 对齐）。"""

import asyncio
from typing import Awaitable, Callable, Optional

from sqlalchemy.orm import Session

from app.services import hub_ai_task_service as hub_svc

QUEUE_POLL_SECONDS = 2.0


async def wait_hub_task_running(
    hub_db_call,
    task_id: int,
    *,
    is_disconnected: Optional[Callable[[], Awaitable[bool]]] = None,
    poll_seconds: float = QUEUE_POLL_SECONDS,
) -> str:
    """等待 pending 任务进入 running。返回 running / canceled / failed / missing / 其他终态。"""
    await asyncio.to_thread(
        lambda: hub_db_call(lambda db: hub_svc.set_task_sse_waiting(db, task_id, True))
    )
    try:
        while True:
            if is_disconnected is not None and await is_disconnected():
                await asyncio.to_thread(
                    lambda: hub_db_call(
                        lambda db: hub_svc.cancel_pending_hub_task(
                            db, task_id, error="连接已断开，排队任务已取消"
                        )
                    )
                )
                return "canceled"

            def _step(db: Session) -> str:
                hub_svc.try_promote_hub_task(db, task_id)
                task = hub_svc.get_task(db, task_id)
                if not task:
                    return "missing"
                return task.status

            status = await asyncio.to_thread(lambda: hub_db_call(_step))
            if status == "running":
                return "running"
            if status in hub_svc.HUB_TASK_TERMINAL:
                return status
            await asyncio.sleep(poll_seconds)
    finally:
        await asyncio.to_thread(
            lambda: hub_db_call(lambda db: hub_svc.set_task_sse_waiting(db, task_id, False))
        )


async def hub_task_was_canceled(hub_db_call, task_id: int) -> bool:
    def _check(db: Session) -> bool:
        return hub_svc.hub_task_is_canceled(db, task_id)

    return await asyncio.to_thread(lambda: hub_db_call(_check))
