"""pytest 基建 · 隔离 sqlite 临时库（不触碰 dev/prod MySQL）。

单测测的是 Python 业务逻辑（树读写/分组执行/计数），由 ORM 抽象，与库无关；
sqlite 仅为快、隔离、免依赖。必须在导入任何 app 模块之前设好 DATABASE_URL。
"""

import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="apifox_test_")
_db_file = os.path.join(_tmp_dir, "test.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"

import pytest  # noqa: E402

import app.models  # noqa: E402,F401  注册所有表到 Base.metadata
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models.apifox.case import ApifoxEndpointCase  # noqa: E402
from app.models.apifox.endpoint import ApifoxEndpoint  # noqa: E402


@pytest.fixture
def db():
    """每个测试一套干净 schema（drop+create），零共享可变状态。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_endpoint(db):
    def _make(project_id: int = 1, method: str = "GET", path: str = "/x", name: str = "ep"):
        ep = ApifoxEndpoint(project_id=project_id, name=name, method=method, path=path)
        db.add(ep)
        db.commit()
        db.refresh(ep)
        return ep

    return _make


@pytest.fixture
def make_case(db, make_endpoint):
    def _make(project_id: int = 1, name: str = "case", endpoint=None):
        ep = endpoint or make_endpoint(project_id=project_id, name=f"{name}-ep")
        c = ApifoxEndpointCase(project_id=project_id, endpoint_id=ep.id, name=name)
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    return _make
