from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import settings as env_settings
from app.models.llm_provider import LLMProvider
from app.models.system_setting import SystemSetting

MOCK_MODE_KEY = "llm_mock_mode"

PRESET_PROVIDERS = [
    {
        "name": "智谱 GLM-4-Flash（免费）",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    {
        "name": "硅基流动 Qwen2.5-7B",
        "api_base": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
    },
    {
        "name": "DeepSeek Chat",
        "api_base": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
]


def _get_setting(db: Session, key: str) -> Optional[str]:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else None


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))


def mask_api_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:3]}****{key[-4:]}"


def _provider_to_dict(provider: LLMProvider) -> dict:
    return {
        "id": provider.id,
        "name": provider.name,
        "api_base": provider.api_base,
        "model": provider.model,
        "enabled": provider.enabled,
        "is_default": provider.is_default,
        "api_key_configured": bool(provider.api_key),
        "api_key_masked": mask_api_key(provider.api_key),
        "created_at": provider.created_at,
    }


def _get_mock_mode(db: Session) -> bool:
    mock_raw = _get_setting(db, MOCK_MODE_KEY)
    if mock_raw is None:
        return env_settings.llm_mock_mode
    return mock_raw.lower() in ("true", "1", "yes")


def _set_mock_mode(db: Session, mock_mode: bool) -> None:
    _set_setting(db, MOCK_MODE_KEY, "true" if mock_mode else "false")


def _clear_default(db: Session) -> None:
    for provider in db.query(LLMProvider).filter(LLMProvider.is_default.is_(True)).all():
        provider.is_default = False


def _get_default_provider(db: Session) -> Optional[LLMProvider]:
    provider = (
        db.query(LLMProvider)
        .filter(LLMProvider.is_default.is_(True), LLMProvider.enabled.is_(True))
        .first()
    )
    if provider:
        return provider
    return db.query(LLMProvider).filter(LLMProvider.enabled.is_(True)).order_by(LLMProvider.id).first()


def _migrate_legacy_settings(db: Session) -> None:
    if db.query(LLMProvider).first():
        return

    legacy_base = _get_setting(db, "llm_api_base")
    legacy_key = _get_setting(db, "llm_api_key")
    legacy_model = _get_setting(db, "llm_model")

    if legacy_base is not None:
        provider = LLMProvider(
            name="默认模型",
            api_base=legacy_base or env_settings.llm_api_base,
            api_key=legacy_key or env_settings.llm_api_key,
            model=legacy_model or env_settings.llm_model,
            enabled=True,
            is_default=True,
        )
        db.add(provider)
        db.commit()
        return

    for index, preset in enumerate(PRESET_PROVIDERS):
        db.add(
            LLMProvider(
                name=preset["name"],
                api_base=preset["api_base"],
                model=preset["model"],
                api_key=env_settings.llm_api_key if index == 0 and env_settings.llm_api_key else "",
                enabled=True,
                is_default=index == 0,
            )
        )
    _set_mock_mode(db, env_settings.llm_mock_mode)
    db.commit()


def init_llm_settings_from_env(db: Session) -> None:
    _migrate_legacy_settings(db)
    if _get_setting(db, MOCK_MODE_KEY) is None:
        _set_mock_mode(db, env_settings.llm_mock_mode)
        db.commit()


def list_llm_providers(db: Session) -> List[dict]:
    init_llm_settings_from_env(db)
    providers = db.query(LLMProvider).order_by(LLMProvider.id).all()
    return [_provider_to_dict(item) for item in providers]


def get_llm_settings_out(db: Session) -> dict:
    init_llm_settings_from_env(db)
    providers = list_llm_providers(db)
    default_provider = _get_default_provider(db)
    return {
        "mock_mode": _get_mock_mode(db),
        "active_provider_id": default_provider.id if default_provider else None,
        "providers": providers,
    }


def get_provider_config(db: Session, provider_id: int) -> Optional[dict]:
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        return None
    return {
        "id": provider.id,
        "name": provider.name,
        "api_base": provider.api_base,
        "api_key": provider.api_key,
        "model": provider.model,
        "enabled": provider.enabled,
        "mock_mode": _get_mock_mode(db),
    }


def get_effective_llm_config(db: Session, provider_id: Optional[int] = None) -> dict:
    init_llm_settings_from_env(db)
    mock_mode = _get_mock_mode(db)

    provider = None
    if provider_id:
        provider = (
            db.query(LLMProvider)
            .filter(LLMProvider.id == provider_id, LLMProvider.enabled.is_(True))
            .first()
        )
    if not provider:
        provider = _get_default_provider(db)

    if not provider:
        return {
            "provider_id": None,
            "provider_name": None,
            "api_base": env_settings.llm_api_base,
            "api_key": env_settings.llm_api_key,
            "model": env_settings.llm_model,
            "mock_mode": mock_mode,
        }

    return {
        "provider_id": provider.id,
        "provider_name": provider.name,
        "api_base": provider.api_base,
        "api_key": provider.api_key,
        "model": provider.model,
        "mock_mode": mock_mode,
    }


def list_llm_provider_options(db: Session) -> dict:
    init_llm_settings_from_env(db)
    default_provider = _get_default_provider(db)
    providers = (
        db.query(LLMProvider)
        .filter(LLMProvider.enabled.is_(True))
        .order_by(LLMProvider.id)
        .all()
    )
    return {
        "mock_mode": _get_mock_mode(db),
        "active_provider_id": default_provider.id if default_provider else None,
        "providers": [
            {
                "id": item.id,
                "name": item.name,
                "model": item.model,
                "is_default": item.is_default,
                "api_key_configured": bool(item.api_key),
            }
            for item in providers
        ],
    }


def create_llm_provider(
    db: Session,
    *,
    name: str,
    api_base: str,
    model: str,
    api_key: str = "",
    enabled: bool = True,
    is_default: bool = False,
) -> dict:
    init_llm_settings_from_env(db)
    if is_default:
        _clear_default(db)
    provider = LLMProvider(
        name=name.strip(),
        api_base=api_base.strip(),
        model=model.strip(),
        api_key=api_key.strip(),
        enabled=enabled,
        is_default=is_default or db.query(LLMProvider).count() == 0,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return _provider_to_dict(provider)


def update_llm_provider(
    db: Session,
    provider_id: int,
    *,
    name: Optional[str] = None,
    api_base: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    enabled: Optional[bool] = None,
    is_default: Optional[bool] = None,
) -> Optional[dict]:
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        return None

    if name is not None:
        provider.name = name.strip()
    if api_base is not None:
        provider.api_base = api_base.strip()
    if model is not None:
        provider.model = model.strip()
    if api_key is not None and api_key.strip():
        provider.api_key = api_key.strip()
    if enabled is not None:
        provider.enabled = enabled
    if is_default is not None and is_default:
        _clear_default(db)
        provider.is_default = True

    db.commit()
    db.refresh(provider)
    return _provider_to_dict(provider)


def delete_llm_provider(db: Session, provider_id: int) -> bool:
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        return False

    was_default = provider.is_default
    db.delete(provider)
    db.commit()

    if was_default:
        next_provider = db.query(LLMProvider).filter(LLMProvider.enabled.is_(True)).order_by(LLMProvider.id).first()
        if next_provider:
            next_provider.is_default = True
            db.commit()
    return True


def set_active_provider(db: Session, provider_id: int) -> Optional[dict]:
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        return None
    _clear_default(db)
    provider.is_default = True
    provider.enabled = True
    db.commit()
    db.refresh(provider)
    return _provider_to_dict(provider)


def update_mock_mode(db: Session, mock_mode: bool) -> dict:
    init_llm_settings_from_env(db)
    _set_mock_mode(db, mock_mode)
    db.commit()
    return get_llm_settings_out(db)


def build_test_config(
    db: Session,
    *,
    provider_id: Optional[int] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    mock_mode: Optional[bool] = None,
) -> dict:
    stored = get_effective_llm_config(db)
    if provider_id:
        provider_config = get_provider_config(db, provider_id)
        if provider_config:
            stored = {
                **stored,
                "api_base": provider_config["api_base"],
                "api_key": provider_config["api_key"],
                "model": provider_config["model"],
            }

    resolved_key = api_key.strip() if api_key and api_key.strip() else stored["api_key"]
    return {
        "api_base": api_base or stored["api_base"],
        "api_key": resolved_key,
        "model": model or stored["model"],
        "mock_mode": mock_mode if mock_mode is not None else stored["mock_mode"],
    }
