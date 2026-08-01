"""数据库提取列 → 变量：需同时兼容 dict（运行路径 _Op）与 Pydantic DbExtractRow（调试路径）。

调试 debug_send 传的 pre_processors 是 ProcessorRow，其 db_extracts 为 List[DbExtractRow]
（Pydantic 对象非 dict）；_extract_db_columns 原只认 dict → 调试下 DB 提取被静默跳过，
{{变量}} 取不到值（SQL 仍执行、控制台有输出，故有迷惑性）。
"""

from app.routers.apifox.schemas import DbExtractRow
from app.services.apifox.run_engine import _extract_db_columns

FIRST_ROW = {"id": 1, "status": "active"}


def test_extract_handles_pydantic_dbextractrow():
    variables: dict = {}
    rows = [DbExtractRow(var_name="data_status", column="status", scope="global")]

    results, scoped = _extract_db_columns(rows, FIRST_ROW, variables)

    assert variables["data_status"] == "active"  # 调试路径 Pydantic 对象也应提取到内存变量
    assert results[0]["passed"] is True
    assert scoped == [{"key": "data_status", "value": "active", "scope": "global"}]


def test_extract_handles_dict_rows_unchanged():
    variables: dict = {}
    rows = [{"var_name": "s", "column": "status", "scope": "temporary"}]

    _extract_db_columns(rows, FIRST_ROW, variables)

    assert variables["s"] == "active"  # 运行路径 dict 行为不变
