"""project_members 残留表纠正迁移（回归：成员接口 500）。

演示库残留的旧表列不全、id 非自增 → SELECT created_by 报 1054、INSERT 报 id 无默认值。
空表按模型重建；非空表只补列保数据。
"""

import os
import tempfile

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.services import project_migration


def _engine(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="projmig_")
    dbfile = os.path.join(tmp, "m.db").replace("\\", "/")
    eng = create_engine(f"sqlite:///{dbfile}")
    monkeypatch.setattr(project_migration, "engine", eng)
    return eng


def test_empty_residual_table_rebuilt_to_correct_schema(monkeypatch):
    eng = _engine(monkeypatch)
    # 残留最小表：缺 created_by/created_at、id 非自增，且为空
    with eng.begin() as c:
        c.execute(text("CREATE TABLE project_members (id INTEGER, project_id INTEGER, user_id INTEGER)"))
    db = Session(eng)

    project_migration.migrate_project_members_columns(db)

    cols = {c["name"] for c in inspect(eng).get_columns("project_members")}
    assert {"created_by", "created_at"} <= cols
    # 重建后能按模型正常插入（自增 id 生效）
    m = ProjectMember(project_id=1, user_id=2, created_by=9)
    db.add(m)
    db.commit()
    db.refresh(m)
    assert m.id is not None
    db.close()


def test_nonempty_table_keeps_data_and_adds_columns(monkeypatch):
    eng = _engine(monkeypatch)
    with eng.begin() as c:
        c.execute(text("CREATE TABLE project_members (id INTEGER PRIMARY KEY, project_id INTEGER, user_id INTEGER)"))
        c.execute(text("INSERT INTO project_members (id, project_id, user_id) VALUES (1, 5, 7)"))
    db = Session(eng)

    project_migration.migrate_project_members_columns(db)

    cols = {c["name"] for c in inspect(eng).get_columns("project_members")}
    assert {"created_by", "created_at"} <= cols
    got = db.execute(text("SELECT project_id, user_id FROM project_members WHERE id=1")).first()
    assert tuple(got) == (5, 7)  # 非空表不重建，数据保留
    db.close()


def test_migrate_noop_when_table_absent(monkeypatch):
    eng = _engine(monkeypatch)
    db = Session(eng)

    project_migration.migrate_project_members_columns(db)  # 无表：安全跳过

    assert "project_members" not in inspect(eng).get_table_names()
    db.close()
