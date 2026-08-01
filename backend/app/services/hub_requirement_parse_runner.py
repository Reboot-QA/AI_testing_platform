"""Hub 需求文档 AI 解析：与 SSE 连接解耦，关页后后台仍可跑完。"""

import asyncio
import json
from typing import Awaitable, Callable, List, Optional

from sqlalchemy.orm import Session

from app.services import hub_ai_task_service
from app.services.ai_service import stream_extract_requirements
from app.services.hub_ai_task_wait import hub_task_was_canceled, wait_hub_task_running

HUB_PARSE_STREAM_END = object()


def _sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


async def _put(queue: asyncio.Queue, payload: dict) -> None:
    await queue.put(_sse_line(payload))


async def run_hub_requirement_parse(
    queue: asyncio.Queue,
    *,
    hub_db_call,
    hub_task,
    project_id: int,
    user_id: int,
    filename: str,
    document_text: str,
    truncated: bool,
    llm_config: dict,
    llm_slot_key: int,
    doc_chunk_total: int,
    requirement_parse_concurrency: int,
    global_llm_limit: int,
    is_disconnected: Optional[Callable[[], Awaitable[bool]]] = None,
) -> None:
    saved_count = 0
    mode = "mock" if llm_config["mock_mode"] else "llm"
    done_message: Optional[str] = None
    hub_task_id = hub_task.id
    chunk_total = 0
    chunk_index = 0

    async def _set_worker(active: bool) -> None:
        def _fn(db: Session) -> None:
            hub_ai_task_service.set_hub_parse_worker_active(db, hub_task_id, active)

        await asyncio.to_thread(lambda: hub_db_call(_fn))

    try:
        if hub_task.status == "pending":
            await _put(
                queue,
                {
                    "type": "status",
                    "message": "排队中，等待使用同一模型的其他 AI 需求解析任务完成…",
                    "queued": True,
                    "current": 0,
                    "chunk": 0,
                    "chunk_total": doc_chunk_total,
                    "hub_task_id": hub_task_id,
                },
            )
            slot_status = await wait_hub_task_running(
                hub_db_call,
                hub_task_id,
                is_disconnected=is_disconnected,
            )
            if slot_status != "running":
                err = (
                    "排队任务已取消"
                    if slot_status == "canceled"
                    else "排队任务未能启动，请稍后重试"
                )
                await _put(queue, {"type": "error", "message": err})
                return

        await _set_worker(True)

        if doc_chunk_total:

            def _init_chunk_total(db: Session) -> None:
                hub_ai_task_service.update_progress(db, hub_task_id, total_items=doc_chunk_total)

            await asyncio.to_thread(lambda: hub_db_call(_init_chunk_total))

        await _put(
            queue,
            {
                "type": "status",
                "message": "开始分析文档...",
                "current": 0,
                "chunk": 0,
                "chunk_total": doc_chunk_total,
                "hub_task_id": hub_task_id,
            },
        )

        chunk_item_buffer: List[dict] = []
        buffer_chunk_index = 0

        async def flush_requirement_chunk_buffer() -> None:
            nonlocal chunk_item_buffer
            if not chunk_item_buffer or not hub_task_id:
                return
            batch = list(chunk_item_buffer)
            ci = buffer_chunk_index
            ct = chunk_total
            gen_total = saved_count

            def _batch(db: Session):
                return hub_ai_task_service.record_requirement_stream_batch(
                    db,
                    hub_task_id,
                    project_id=project_id,
                    created_by_id=user_id,
                    items=batch,
                    chunk_index=ci,
                    chunk_total=ct,
                    generated_total=gen_total,
                )

            reqs = await asyncio.to_thread(lambda: hub_db_call(_batch))
            chunk_item_buffer = []
            for item_snapshot, req in zip(batch, reqs):
                snap = dict(item_snapshot)
                await _put(
                    queue,
                    {
                        "type": "requirement",
                        "data": {**snap, "id": req.id, "saved": True},
                        "current": saved_count,
                        "chunk": ci,
                        "chunk_total": ct,
                        "saved": True,
                    },
                )

        async for item, current_mode, current, chunk_index, chunk_total, tail_message in stream_extract_requirements(
            document_text,
            api_base=llm_config["api_base"],
            api_key=llm_config["api_key"],
            model=llm_config["model"],
            mock_mode=llm_config["mock_mode"],
            concurrency=requirement_parse_concurrency,
            global_llm_limit=global_llm_limit,
            llm_slot_key=llm_slot_key,
        ):
            if hub_task_id and await hub_task_was_canceled(hub_db_call, hub_task_id):
                return
            mode = current_mode
            saved_count = current
            if tail_message and tail_message.startswith("__heartbeat__"):
                in_flight = 1
                if ":" in tail_message:
                    try:
                        in_flight = max(1, int(tail_message.split(":", 1)[1]))
                    except ValueError:
                        in_flight = 1

                def _heartbeat(db: Session) -> None:
                    hub_ai_task_service.update_requirement_parse_heartbeat(
                        db,
                        hub_task_id,
                        segments_done=chunk_index,
                        segment_total=chunk_total,
                        segment_in_flight=min(
                            chunk_index + in_flight,
                            chunk_total or chunk_index + in_flight,
                        ),
                        generated_total=saved_count,
                        segments_in_flight_count=in_flight,
                    )

                await asyncio.to_thread(lambda: hub_db_call(_heartbeat))
                parallel_hint = (
                    f"，并行 {in_flight} 段"
                    if in_flight > 1
                    else f"，正在处理第 {min(chunk_index + 1, chunk_total)} 段"
                )
                await _put(
                    queue,
                    {
                        "type": "status",
                        "message": (
                            f"正在调用大模型解析文档（已完成 {chunk_index}/{chunk_total} 段"
                            f"{parallel_hint}），"
                            f"已提取 {saved_count} 条需求点，请稍候…"
                        ),
                        "current": saved_count,
                        "chunk": chunk_index,
                        "chunk_total": chunk_total,
                    },
                )
                continue
            if tail_message:
                done_message = tail_message
            if item is None:
                if chunk_item_buffer:
                    await flush_requirement_chunk_buffer()
                if chunk_total and hub_task_id:

                    def _upd_chunk(db: Session) -> None:
                        hub_ai_task_service.update_chunk_progress(
                            db,
                            hub_task_id,
                            chunk_index=chunk_index,
                            chunk_total=chunk_total,
                            generated_total=saved_count,
                        )

                    await asyncio.to_thread(lambda: hub_db_call(_upd_chunk))
                await _put(
                    queue,
                    {
                        "type": "status",
                        "message": (
                            f"正在分析文档（已完成 {chunk_index}/{chunk_total} 段），"
                            f"已提取 {saved_count} 条需求点..."
                            if chunk_index < chunk_total
                            else f"文档段解析完成，共 {saved_count} 条需求点，正在收尾..."
                        ),
                        "current": saved_count,
                        "chunk": chunk_index,
                        "chunk_total": chunk_total,
                    },
                )
                continue

            if chunk_item_buffer and chunk_index != buffer_chunk_index:
                await flush_requirement_chunk_buffer()
            buffer_chunk_index = chunk_index
            chunk_item_buffer.append(dict(item))

        if chunk_item_buffer:
            await flush_requirement_chunk_buffer()

        if hub_task_id and await hub_task_was_canceled(hub_db_call, hub_task_id):
            return

        message = done_message or f"成功提取 {saved_count} 条需求点，已实时写入需求点"

        def _finish_ok(db: Session) -> None:
            hub_ai_task_service.finish_task(
                db,
                hub_task_id,
                status="succeeded",
                generated_total=saved_count,
                applied_total=saved_count,
                done_items=chunk_total or saved_count,
                total_items=chunk_total or max(saved_count, 1),
                meta={
                    "truncated": truncated,
                    "mode": mode,
                    "filename": filename,
                    "message": message,
                },
            )

        await asyncio.to_thread(lambda: hub_db_call(_finish_ok))
        await _put(
            queue,
            {
                "type": "done",
                "mode": mode,
                "filename": filename,
                "total": saved_count,
                "truncated": truncated,
                "hub_task_id": hub_task_id,
                "provider_name": llm_config.get("provider_name"),
                "model": llm_config.get("model"),
                "message": message,
            },
        )
    except Exception as exc:
        error_message = str(exc)
        if hub_task_id:

            def _finish_fail(db: Session) -> None:
                hub_ai_task_service.finish_task(
                    db,
                    hub_task_id,
                    status="failed",
                    generated_total=saved_count,
                    applied_total=saved_count,
                    done_items=chunk_index,
                    total_items=chunk_total or 0,
                    error=error_message,
                )

            await asyncio.to_thread(lambda: hub_db_call(_finish_fail))
        await _put(queue, {"type": "error", "message": f"AI 解析失败: {exc}"})
    finally:
        if hub_task_id:
            await _set_worker(False)
        await queue.put(HUB_PARSE_STREAM_END)
