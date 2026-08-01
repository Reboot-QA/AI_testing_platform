"""测试报告分页端点 · GET /apifox/projects/{pid}/runs/page（bug 回归：重试链把每页行数吃没了）。

被测：app/routers/apifox/runs.py 的 list_runs_page。用 TestClient 打真实路由（不进 lifespan，手动建表 + 种数据）。
"""

from fastapi.testclient import TestClient

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.apifox.run import ApifoxRun
from app.models.project import Project
from app.models.user import User

API = "/api/v1"
PAGE_SIZE = 5
RETRIES_PER_CHAIN = 2  # 每条链 1 次首跑 + 2 次重试 = 3 次尝试


def _seed(chain_count: int) -> None:
    """种 chain_count 条重试链，每条链 3 次尝试（首跑 + 2 次重试，末次通过）。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(username="rp_u", hashed_password=get_password_hash("pw123456"), role="admin")
        db.add(user)
        db.flush()
        db.add(Project(id=1, name="报告分页项目", owner_id=user.id))
        db.commit()
        for i in range(chain_count):
            head = ApifoxRun(
                project_id=1,
                target_type="scenario",
                target_id=i + 1,
                target_name=f"场景{i + 1}",
                status="failed",
            )
            db.add(head)
            db.flush()
            for attempt in range(2, 2 + RETRIES_PER_CHAIN):
                db.add(
                    ApifoxRun(
                        project_id=1,
                        target_type="scenario",
                        target_id=i + 1,
                        target_name=f"场景{i + 1}",
                        status="passed" if attempt == 1 + RETRIES_PER_CHAIN else "failed",
                        retry_of_run_id=head.id,
                        attempt=attempt,
                    )
                )
        db.commit()
    finally:
        db.close()


def _client_with_token() -> tuple[TestClient, dict]:
    client = TestClient(app)
    token = client.post(
        f"{API}/auth/login", data={"username": "rp_u", "password": "pw123456"}
    ).json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_page_returns_page_size_rows_and_counts_chains_not_attempts():
    chain_count = 12
    _seed(chain_count)
    client, headers = _client_with_token()

    body = client.get(
        f"{API}/apifox/projects/1/runs/page",
        params={"page": 1, "page_size": PAGE_SIZE, "target_types": "scenario,suite"},
        headers=headers,
    ).json()

    # 每页装满 page_size 行、总条数按链计（此前按尝试计：一页只剩 page_size/3 行、总数×3）
    assert len(body["items"]) == PAGE_SIZE
    assert body["total"] == chain_count
    # 行本身是最后一次尝试（整体结果），此前各次尝试挂在 retries 上供展开
    for item in body["items"]:
        assert item["attempt"] == 1 + RETRIES_PER_CHAIN
        assert item["status"] == "passed"
        assert [r["attempt"] for r in item["retries"]] == [1, 2]


def test_last_page_is_not_beyond_chain_count():
    _seed(6)
    client, headers = _client_with_token()

    last = client.get(
        f"{API}/apifox/projects/1/runs/page",
        params={"page": 2, "page_size": PAGE_SIZE},
        headers=headers,
    ).json()

    # 总数 6 → 2 页；末页只剩 1 行（按尝试分页时会多出 3 页空/半空页）
    assert len(last["items"]) == 1
    assert last["total"] == 6
