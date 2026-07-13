"""Apifox · 数据库操作执行器（临时引擎连目标库执行任意 SQL；全程不抛异常，转 error）。

用 exec_driver_sql 把用户原样 SQL 直接下发 DBAPI（不经 SQLAlchemy 的 :name 绑定解析，
避免 SQL 里的冒号被误当参数）。engine 用完即 dispose，不复用平台连接池。带连接/读写超时防挂。
"""

import logging
from typing import Any, Dict
from urllib.parse import quote_plus

from sqlalchemy import create_engine

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 10
_RW_TIMEOUT = 30
_MAX_RETURN_ROWS = 200


def _build_url(conn: ApifoxEnvironmentDatabase) -> str:
    user = quote_plus(conn.username or "")
    pwd = quote_plus(conn.password or "")
    return f"mysql+pymysql://{user}:{pwd}@{conn.host}:{conn.port}/{conn.database or ''}"


def run_sql(conn: ApifoxEnvironmentDatabase, sql: str) -> Dict[str, Any]:
    """执行单条 SQL。SELECT 回结果集（截断 200 行），写操作提交并回 rowcount。

    返回 {passed, columns, rows, rowcount, error}。异常一律转 error，不外抛。
    """
    if conn.db_type != "mysql":
        return {"passed": False, "columns": [], "rows": [], "rowcount": 0,
                "error": f"暂不支持的数据库类型: {conn.db_type}"}
    engine = None
    try:
        engine = create_engine(
            _build_url(conn),
            connect_args={
                "connect_timeout": _CONNECT_TIMEOUT,
                "read_timeout": _RW_TIMEOUT,
                "write_timeout": _RW_TIMEOUT,
            },
        )
        with engine.begin() as connection:  # begin(): 成功自动提交（写操作生效）
            result = connection.exec_driver_sql(sql)
            if result.returns_rows:
                columns = list(result.keys())
                rows = [dict(r._mapping) for r in result.fetchmany(_MAX_RETURN_ROWS)]
                return {"passed": True, "columns": columns, "rows": rows,
                        "rowcount": len(rows), "error": None}
            return {"passed": True, "columns": [], "rows": [], "rowcount": result.rowcount,
                    "error": None}
    except Exception as exc:  # noqa: BLE001 - 执行类工具需健壮，任何驱动/网络异常转 error
        logger.warning("数据库步骤 SQL 执行失败 [%s@%s]: %s", conn.database, conn.host, exc)
        return {"passed": False, "columns": [], "rows": [], "rowcount": 0, "error": str(exc)}
    finally:
        if engine is not None:
            engine.dispose()


def test_connection(conn: ApifoxEnvironmentDatabase) -> Dict[str, Any]:
    """连通性探测：执行 SELECT 1。"""
    return run_sql(conn, "SELECT 1")
