"""项目成员 · service + 访问条件测试。

覆盖：增删查、重复拒绝、候选人排除成员；以及成员获得跨部门访问、is_project_manager 判定。
"""

import pytest
from fastapi import HTTPException

from app.models.project import Project
from app.models.user import User
from app.services import project_member_service as svc
from app.services.project_access_service import (
    accessible_projects_query,
    is_project_manager,
)


def _user(db, username, role="tester", department_id=None):
    u = User(username=username, hashed_password="x", role=role, department_id=department_id)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _project(db, owner_id, department_id=None, name="项目A"):
    p = Project(name=name, owner_id=owner_id, department_id=department_id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------- 成员 CRUD ----------
def test_add_list_remove_member(db):
    owner = _user(db, "owner")
    proj = _project(db, owner.id)
    molley = _user(db, "molley")

    svc.add_member(db, proj.id, molley.id, actor_id=owner.id)
    members = svc.list_members(db, proj.id)
    assert [m.username for m in members] == ["molley"]

    assert svc.remove_member(db, proj.id, molley.id) is True
    assert svc.list_members(db, proj.id) == []


def test_add_duplicate_member_rejected(db):
    owner = _user(db, "owner")
    proj = _project(db, owner.id)
    molley = _user(db, "molley")
    svc.add_member(db, proj.id, molley.id, actor_id=owner.id)

    with pytest.raises(HTTPException) as exc:
        svc.add_member(db, proj.id, molley.id, actor_id=owner.id)
    assert exc.value.status_code == 400


def test_add_nonexistent_user_404(db):
    owner = _user(db, "owner")
    proj = _project(db, owner.id)

    with pytest.raises(HTTPException) as exc:
        svc.add_member(db, proj.id, 9999, actor_id=owner.id)
    assert exc.value.status_code == 404


def test_candidates_exclude_existing_members(db):
    owner = _user(db, "owner")
    proj = _project(db, owner.id)
    molley = _user(db, "molley")
    _user(db, "bob")
    svc.add_member(db, proj.id, molley.id, actor_id=owner.id)

    names = {c.username for c in svc.list_candidates(db, proj.id, keyword=None)}
    assert "bob" in names and "molley" not in names  # 已是成员的排除


# ---------- 访问条件（bug2 回归：跨部门成员应能进项目） ----------
def test_member_gains_cross_department_access(db):
    owner = _user(db, "owner", department_id=1)
    proj = _project(db, owner.id, department_id=1)
    molley = _user(db, "molley", department_id=2)  # 不同部门

    before = accessible_projects_query(db, molley).all()
    assert proj.id not in [p.id for p in before]  # 加成员前：跨部门看不到

    svc.add_member(db, proj.id, molley.id, actor_id=owner.id)

    after = accessible_projects_query(db, molley).all()
    assert proj.id in [p.id for p in after]  # 加成员后：可见


def test_is_project_manager(db):
    owner = _user(db, "owner")
    admin = _user(db, "admin", role="admin")
    proj = _project(db, owner.id)
    member = _user(db, "molley", department_id=2)
    svc.add_member(db, proj.id, member.id, actor_id=owner.id)

    assert is_project_manager(owner, proj) is True
    assert is_project_manager(admin, proj) is True
    assert is_project_manager(member, proj) is False  # 成员不是管理者
