"""前后置处理器保存校验：未启用（未勾选）的项不参与校验（Confluence 7/23-#4）。

复现：加一个空的、未勾选的 database_script 后置项，保存/发送本不该报错
（执行时也会 `if not op.enabled: continue` 跳过），但校验漏了 enabled 判断而误报。
"""

import pytest

from app.routers.apifox.schemas import ProcessorRow
from app.services.apifox import sql_script_service


def test_validate_skips_disabled_empty_database_script(db):
    rows = [ProcessorRow(kind="database_script", enabled=False)]  # 空（无 sql_script_id）+ 未勾选
    sql_script_service.validate_processor_refs(db, project_id=1, rows=rows)  # 不应抛异常


def test_validate_enabled_empty_database_script_still_raises(db):
    rows = [ProcessorRow(kind="database_script", enabled=True)]  # 启用但没选脚本 → 仍拦
    with pytest.raises(ValueError, match="未选择 SQL 脚本"):
        sql_script_service.validate_processor_refs(db, project_id=1, rows=rows)
