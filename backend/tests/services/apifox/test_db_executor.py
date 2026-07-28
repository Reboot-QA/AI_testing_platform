"""数据库执行器 · 连通性探测与不支持类型兜底（测试连接按钮依赖）。"""

from types import SimpleNamespace

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.services.apifox import db_executor


def test_test_connection_probes_select_1(monkeypatch):
    seen = {}

    def fake_run_sql(conn, sql):
        seen["sql"] = sql
        return {"passed": True, "columns": [], "rows": [], "rowcount": 0, "error": None}

    monkeypatch.setattr(db_executor, "run_sql", fake_run_sql)

    result = db_executor.test_connection(SimpleNamespace())

    assert result["passed"] is True
    assert seen["sql"] == "SELECT 1"  # 探测语句固定


def test_run_sql_rejects_non_mysql():
    conn = ApifoxEnvironmentDatabase(db_type="postgres", host="h", port=5432, database="d")

    result = db_executor.run_sql(conn, "SELECT 1")

    assert result["passed"] is False
    assert "暂不支持" in result["error"]  # 仅 MySQL，其它类型明确报错而非连接失败


def test_run_sql_unreachable_host_returns_error(monkeypatch):
    """不可达/驱动异常统一转 error，不外抛（测试连接失败要能拿到原因）。"""

    def boom(*a, **k):
        raise OSError("Can't connect to MySQL server")

    monkeypatch.setattr(db_executor, "create_engine", boom)
    conn = ApifoxEnvironmentDatabase(db_type="mysql", host="10.255.255.1", port=3306, database="d")

    result = db_executor.run_sql(conn, "SELECT 1")

    assert result["passed"] is False
    assert "MySQL" in result["error"]
