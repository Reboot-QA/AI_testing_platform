"""退出登录端点 · POST /auth/logout（bug 回归：用户退出没有调用接口）。

被测：app/routers/auth.py 的 logout 端点。用 TestClient 打真实路由（不进 lifespan，手动建表 + 种用户）。
"""

from fastapi.testclient import TestClient

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.user import User

API = "/api/v1/auth"


def _seed_user(username: str = "logout_u", password: str = "pw123456") -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.add(User(username=username, hashed_password=get_password_hash(password), role="admin"))
        db.commit()
    finally:
        db.close()


def test_logout_requires_auth_and_returns_ok():
    _seed_user()
    client = TestClient(app)

    token = client.post(
        f"{API}/login", data={"username": "logout_u", "password": "pw123456"}
    ).json()["access_token"]

    # 带 token → 200（退出由后端接口处理，供审计/会话钩子）
    ok = client.post(f"{API}/logout", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200

    # 无 token → 401（必须是鉴权端点）
    unauth = client.post(f"{API}/logout")
    assert unauth.status_code == 401
