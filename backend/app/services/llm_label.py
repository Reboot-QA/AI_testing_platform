"""大模型列表/任务「模型」列展示文案（任务列表仅展示 model 标识，不展示 Provider 名称）。"""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider


def _legacy_text_to_model_id(text: str) -> str:
    """历史 category_label / 拼接文案 → 取 · 后的 model，无分隔符则整段视为 model。"""
    t = (text or "").strip()
    if not t:
        return ""
    for sep in (" · ", " ·", "· ", "·", "."):
        if sep in t:
            return t.split(sep)[-1].strip()
    return t


def format_llm_task_model_column(
    *,
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    model_s = (model or "").strip()
    if model_s:
        return model_s
    return _legacy_text_to_model_id(str(provider_name or ""))


def llm_task_model_column_from_provider(provider: Optional[LLMProvider]) -> str:
    if not provider:
        return ""
    return format_llm_task_model_column(provider_name=provider.name, model=provider.model)


def llm_task_model_column_from_meta(db: Session, meta: Dict[str, Any]) -> str:
    if meta.get("mock_mode") is True or meta.get("mode") == "mock":
        return "Mock"
    pid = meta.get("provider_id")
    if pid is not None:
        try:
            provider = db.query(LLMProvider).filter(LLMProvider.id == int(pid)).first()
        except (TypeError, ValueError):
            provider = None
        label = llm_task_model_column_from_provider(provider)
        if label:
            return label
    return format_llm_task_model_column(
        provider_name=str(meta.get("provider_name") or ""),
        model=str(meta.get("model") or ""),
    )


# 兼容旧引用（其它场景若需「名称 · model」可再用下列函数）
def format_llm_model_display(
    *,
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    return format_llm_task_model_column(provider_name=provider_name, model=model)


def llm_model_display_from_provider(provider: Optional[LLMProvider]) -> str:
    return llm_task_model_column_from_provider(provider)


def llm_model_display_from_meta(db: Session, meta: Dict[str, Any]) -> str:
    return llm_task_model_column_from_meta(db, meta)
