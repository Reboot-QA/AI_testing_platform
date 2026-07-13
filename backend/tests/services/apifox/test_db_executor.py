"""db_executor.run_sql · 核心契约「全程不抛异常，转 error」（不依赖真实数据库）。

评审#2：run_service 的 db 步骤测试全程打桩 run_sql，此文件直接覆盖 executor 本身的健壮性。
"""

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.services.apifox import db_executor


def _conn(**kw):
    defaults = dict(host="127.0.0.1", port=1, db_type="mysql", database="d", username="u", password="")
    defaults.update(kw)
    return ApifoxEnvironmentDatabase(**defaults)


def test_run_sql_connection_failure_returns_error_not_raises():
    # 端口 1 必然拒绝，无需真实 MySQL；验证异常被转 error 而非外抛（去掉 try/except 即失败）
    result = db_executor.run_sql(_conn(), "SELECT 1")

    assert result["passed"] is False
    assert result["error"]
    assert result["rows"] == []


def test_run_sql_unsupported_db_type_returns_error():
    result = db_executor.run_sql(_conn(db_type="oracle"), "SELECT 1")

    assert result["passed"] is False
    assert "oracle" in result["error"]
