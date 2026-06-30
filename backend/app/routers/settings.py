import httpx
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from app.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas import (
    LLMGenerateOptionsOut,
    LLMProviderCreate,
    LLMProviderOut,
    LLMProviderUpdate,
    LLMSettingsOut,
    LLMTestRequest,
    LLMTestResponse,
    MockModeUpdate,
)
from app.services.settings_service import (
    build_test_config,
    create_llm_provider,
    delete_llm_provider,
    get_llm_settings_out,
    list_llm_provider_options,
    set_active_provider,
    update_llm_provider,
    update_mock_mode,
)

router = APIRouter(prefix="/settings", tags=["系统管理"])


@router.get("/llm/options", response_model=LLMGenerateOptionsOut)
def get_llm_options(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return list_llm_provider_options(db)


@router.get("/llm", response_model=LLMSettingsOut)
def get_llm_settings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return get_llm_settings_out(db)


@router.put("/llm/mock", response_model=LLMSettingsOut)
def update_mock_mode_api(
    data: MockModeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return update_mock_mode(db, data.mock_mode)


@router.get("/llm/providers", response_model=List[LLMProviderOut])
def list_providers(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return get_llm_settings_out(db)["providers"]


@router.post("/llm/providers", response_model=LLMProviderOut)
def create_provider(
    data: LLMProviderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return create_llm_provider(
        db,
        name=data.name,
        api_base=data.api_base,
        model=data.model,
        api_key=data.api_key or "",
        enabled=data.enabled,
        is_default=data.is_default,
    )


@router.put("/llm/providers/{provider_id}", response_model=LLMProviderOut)
def update_provider(
    provider_id: int,
    data: LLMProviderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    provider = update_llm_provider(
        db,
        provider_id,
        name=data.name,
        api_base=data.api_base,
        model=data.model,
        api_key=data.api_key,
        enabled=data.enabled,
        is_default=data.is_default,
    )
    if not provider:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return provider


@router.delete("/llm/providers/{provider_id}")
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    if not delete_llm_provider(db, provider_id):
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return {"message": "删除成功"}


@router.put("/llm/providers/{provider_id}/activate", response_model=LLMProviderOut)
def activate_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    provider = set_active_provider(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return provider


@router.post("/llm/test", response_model=LLMTestResponse)
async def test_llm_connection(
    data: LLMTestRequest = LLMTestRequest(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    config = build_test_config(
        db,
        provider_id=data.provider_id,
        api_base=data.api_base,
        api_key=data.api_key,
        model=data.model,
        mock_mode=data.mock_mode,
    )
    if config["mock_mode"]:
        return LLMTestResponse(success=False, message="当前为 Mock 模式，请先关闭 Mock 模式后再测试")
    if not config["api_key"]:
        return LLMTestResponse(success=False, message="未配置 API Key")

    url = f"{config['api_base'].rstrip('/')}/chat/completions"
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
        "stream": False,
    }
    if "bigmodel.cn" in config["api_base"]:
        payload["tools"] = [{"type": "web_search", "web_search": {"enable": False}}]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {config['api_key']}"},
                json=payload,
            )
            response.raise_for_status()
            return LLMTestResponse(success=True, message="连接成功，LLM 服务可用")
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:200] if exc.response.text else str(exc)
        return LLMTestResponse(success=False, message=f"HTTP {exc.response.status_code}: {detail}")
    except Exception as exc:
        return LLMTestResponse(success=False, message=f"连接失败: {exc}")
