import json
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.assistant_action_service import plan_assistant_actions
from app.services.assistant_service import stream_assistant_reply
from app.services.settings_service import get_effective_llm_config

router = APIRouter(prefix="/assistant", tags=["AI助手"])


class AssistantMessage(BaseModel):
    role: str
    content: str = Field(min_length=1)


class AssistantChatRequest(BaseModel):
    messages: List[AssistantMessage] = Field(min_length=1)
    provider_id: Optional[int] = None
    page_path: Optional[str] = None
    demo_preset: Optional[str] = None


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@router.post("/chat/stream")
async def assistant_chat_stream(
    data: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    llm_config = get_effective_llm_config(db, data.provider_id)
    messages = [{"role": item.role, "content": item.content} for item in data.messages]

    plan = await plan_assistant_actions(
        messages,
        api_base=llm_config["api_base"],
        api_key=llm_config["api_key"],
        model=llm_config["model"],
        mock_mode=llm_config["mock_mode"],
        page_path=data.page_path,
        demo_preset=data.demo_preset,
    )

    preset_reply = plan.get("reply") if plan.get("actions") else None
    if plan.get("actions") and not (preset_reply or "").strip():
        preset_reply = "已为您规划浏览器操作步骤，请确认后执行。"

    async def event_generator():
        try:
            yield _sse_event(
                {
                    "type": "meta",
                    "mode": "mock" if llm_config["mock_mode"] else "llm",
                    "model": llm_config.get("model"),
                    "provider_name": llm_config.get("provider_name"),
                }
            )
            if plan.get("actions"):
                yield _sse_event(
                    {
                        "type": "plan",
                        "reply": plan.get("reply") or "",
                        "actions": plan.get("actions") or [],
                        "needs_confirmation": plan.get("needs_confirmation", True),
                    }
                )
            async for token in stream_assistant_reply(
                messages,
                api_base=llm_config["api_base"],
                api_key=llm_config["api_key"],
                model=llm_config["model"],
                mock_mode=llm_config["mock_mode"],
                page_path=data.page_path,
                preset_reply=preset_reply,
            ):
                yield _sse_event({"type": "token", "content": token})
            yield _sse_event({"type": "done"})
        except ValueError as exc:
            yield _sse_event({"type": "error", "message": str(exc)})
        except Exception as exc:
            yield _sse_event({"type": "error", "message": f"助手服务异常: {exc}"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
