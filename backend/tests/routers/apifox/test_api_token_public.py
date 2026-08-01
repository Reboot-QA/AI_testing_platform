"""通过 API 导入/导出（X-API-Token 免登录）· 回归。

被测：这两个端点设计上只认 X-API-Token、不需要 JWT，但曾被 main.py 的路由级
project_settings_permission（要 JWT + 菜单权限）误拦，带 token 也报 Not authenticated。
用 TestClient 打真实路由（不进 lifespan，手动建表 + 种数据）。
"""

from fastapi.testclient import TestClient

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.services.apifox import api_token_service

API = "/api/v1"

_MINIMAL_OPENAPI = (
    '{"openapi":"3.0.0","info":{"title":"t"},'
    '"paths":{"/ping":{"get":{"summary":"p","responses":{}}}}}'
)


def _seed_token() -> str:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(username="tok_u", hashed_password=get_password_hash("pw123456"), role="admin")
        db.add(user)
        db.flush()
        db.add(Project(id=1, name="token项目", owner_id=user.id))
        db.commit()
        return api_token_service.create_token(db, 1, "ci", user.id).token
    finally:
        db.close()


def test_import_via_token_no_jwt_required():
    # 带有效 token、无 JWT 应能导入，而非 401 Not authenticated
    token = _seed_token()
    client = TestClient(app)
    r = client.post(
        f"{API}/apifox/api/import",
        headers={"X-API-Token": token},
        json={"content": _MINIMAL_OPENAPI},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("created") == 1


def test_import_via_token_invalid_token_401():
    _seed_token()
    client = TestClient(app)
    r = client.post(
        f"{API}/apifox/api/import",
        headers={"X-API-Token": "afx_invalid"},
        json={"content": _MINIMAL_OPENAPI},
    )
    # token 依赖自身的 401（无效 token），而非 JWT 的 Not authenticated
    assert r.status_code == 401
    assert "API Token" in r.json().get("detail", "")
