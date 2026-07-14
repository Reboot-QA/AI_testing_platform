"""接口(endpoint)乐观锁保存冲突检测（G1 多 tab 并发编辑铺底）。

被测：endpoint_service.update_endpoint 的 version CAS。复用 versioning.bump_version。
"""

import pytest

from app.routers.apifox.schemas import EndpointUpdate
from app.services.apifox import endpoint_service
from app.services.apifox.errors import ConflictError


def test_endpoint_update_matching_version_increments(db, make_endpoint):
    ep = make_endpoint(name="e")
    assert ep.version == 1

    out = endpoint_service.update_endpoint(db, ep, EndpointUpdate(name="e2", expected_version=1))

    assert out.version == 2


def test_endpoint_update_stale_version_raises_conflict(db, make_endpoint):
    ep = make_endpoint(name="e")
    endpoint_service.update_endpoint(db, ep, EndpointUpdate(name="e2", expected_version=1))  # → v2

    with pytest.raises(ConflictError) as ei:
        endpoint_service.update_endpoint(db, ep, EndpointUpdate(name="e3", expected_version=1))

    assert ei.value.current_version == 2


def test_endpoint_update_without_version_backward_compat(db, make_endpoint):
    ep = make_endpoint(name="e")

    out = endpoint_service.update_endpoint(db, ep, EndpointUpdate(name="e2"))

    assert out.version == 2


def test_endpoint_concurrent_two_sessions_second_save_conflicts(db, make_endpoint):
    """两 session 各加载 v1，A 先存(→v2)，B 用旧 v1 存必须冲突（DB 级 CAS）。"""
    from app.database import SessionLocal
    from app.repositories.apifox import endpoint_repo

    ep = make_endpoint(name="e")  # v1
    session_b = SessionLocal()
    try:
        ep_b = endpoint_repo.get_endpoint(session_b, ep.id)
        ep_a = endpoint_repo.get_endpoint(db, ep.id)
        endpoint_service.update_endpoint(db, ep_a, EndpointUpdate(name="by-a", expected_version=1))  # → v2

        with pytest.raises(ConflictError) as ei:
            endpoint_service.update_endpoint(session_b, ep_b, EndpointUpdate(name="by-b", expected_version=1))
        assert ei.value.current_version == 2
    finally:
        session_b.close()
