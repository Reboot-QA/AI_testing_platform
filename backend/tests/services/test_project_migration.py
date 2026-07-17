"""项目成员表幂等列迁移（回归：演示库残留最小 project_members 表缺 created_by → 1054）。"""

import os
import tempfile

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.services import project_migration


def _engine(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="projmig_")
    dbfile = os.path.join(tmp, "m.db").replace("\\", "/")
    eng = create_engine(f"sqlite:///{dbfile}")
    monkeypatch.setattr(project_migration, "engine", eng)
    return eng


def test_migrate_adds_missing_columns_idempotent(monkeypatch):
    eng = _engine(monkeypatch)
    # 复现：只有 project_id/user_id 的历史残留表
    with eng.begin() as c:
        c.execute(text("CREATE TABLE project_members (id INTEGER PRIMARY KEY, project_id INTEGER, user_id INTEGER)"))
    db = Session(eng)

    project_migration.migrate_project_members_columns(db)
    project_migration.migrate_project_members_columns(db)  # 再跑一次应无操作

    cols = {c["name"] for c in inspect(eng).get_columns("project_members")}
    assert "created_by" in cols
    assert "created_at" in cols
    db.close()


def test_migrate_noop_when_table_absent(monkeypatch):
    eng = _engine(monkeypatch)
    db = Session(eng)

    project_migration.migrate_project_members_columns(db)  # 无表：安全跳过，不报错

    assert "project_members" not in inspect(eng).get_table_names()
    db.close()
