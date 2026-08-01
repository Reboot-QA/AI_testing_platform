from types import SimpleNamespace
from unittest.mock import ANY, patch

import pytest
from fastapi import HTTPException

from app.auth import ensure_menu_permission
from app.routers.hub_ai_tasks import _ensure_task_permission


def test_menu_permission_allows_granted_capability():
    with patch("app.services.permission_service.get_user_menu_keys", return_value={"testcases"}):
        ensure_menu_permission(SimpleNamespace(), SimpleNamespace(), "testcases")


def test_menu_permission_rejects_missing_capability():
    with patch("app.services.permission_service.get_user_menu_keys", return_value=set()):
        with pytest.raises(HTTPException) as error:
            ensure_menu_permission(SimpleNamespace(), SimpleNamespace(), "testcases")

    assert error.value.status_code == 403
    assert error.value.detail == "无权访问该模块"


@pytest.mark.parametrize(
    ("task_type", "menu_key"),
    [("requirement", "requirement_docs"), ("functional", "ai_generate")],
)
def test_hub_task_uses_its_own_capability(task_type: str, menu_key: str):
    with patch("app.routers.hub_ai_tasks.ensure_menu_permission") as ensure:
        _ensure_task_permission(SimpleNamespace(), SimpleNamespace(), task_type)

    ensure.assert_called_once_with(ANY, ANY, menu_key)


def test_hub_task_rejects_unknown_type():
    with pytest.raises(HTTPException) as error:
        _ensure_task_permission(SimpleNamespace(), SimpleNamespace(), "unknown")

    assert error.value.status_code == 400
