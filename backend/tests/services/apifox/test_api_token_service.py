"""Apifox 项目级 API Token · 生成/校验/吊销。"""

from app.services.apifox import api_token_service as svc


def test_generate_token_has_prefix_and_entropy():
    a = svc.generate_token()
    b = svc.generate_token()

    assert a.startswith("afx_") and len(a) > 20
    assert a != b


def test_create_list_and_resolve(db):
    created = svc.create_token(db, project_id=1, name="CI", created_by=7)

    tokens = svc.list_tokens(db, 1)
    assert [t.id for t in tokens] == [created.id]

    resolved = svc.resolve_token(db, created.token)
    assert resolved is not None and resolved.project_id == 1
    assert resolved.last_used_at is not None  # 命中即记录使用时间


def test_resolve_invalid_and_revoked(db):
    created = svc.create_token(db, project_id=1, name="X", created_by=None)

    assert svc.resolve_token(db, "afx_nope") is None

    svc.revoke_token(db, created)
    assert svc.resolve_token(db, created.token) is None  # 吊销后失效
    assert svc.list_tokens(db, 1) == []  # 列表不含已吊销
