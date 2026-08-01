from app.models.llm_provider import LLMProvider
from app.services.llm_label import (
    format_llm_task_model_column,
    llm_task_model_column_from_meta,
)


def test_task_model_column_prefers_model_field():
    assert format_llm_task_model_column(provider_name="智谱 GLM-4-Flash", model="glm-4-flash") == (
        "glm-4-flash"
    )
    assert format_llm_task_model_column(provider_name="deepseek-v4-pro", model="deepseek-v4-pro") == (
        "deepseek-v4-pro"
    )
    assert format_llm_task_model_column(provider_name="通义千问", model="qwen-plus") == "qwen-plus"
    assert format_llm_task_model_column(provider_name="通义千问·qwen-plus", model="") == "qwen-plus"


def test_llm_task_model_column_from_meta_uses_provider_table(db):
    p = LLMProvider(
        name="智谱 GLM-4-Flash",
        api_base="https://example.com",
        model="glm-4-flash",
        api_key="k",
        enabled=True,
        is_default=False,
    )
    db.add(p)
    db.commit()
    label = llm_task_model_column_from_meta(db, {"provider_id": p.id, "model": "stale-model-id"})
    assert label == "glm-4-flash"
