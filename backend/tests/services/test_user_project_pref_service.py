"""用户项目偏好（置顶/排序）服务测试：排序语义 + 保存越权隔离 + upsert。"""

from app.models.project import Project
from app.models.user import User
from app.models.user_project_pref import UserProjectPref
from app.services.user_project_pref_service import order_cards, save_order


def _pref(db, user_id, project_id, pinned=False, sort_order=0):
    db.add(UserProjectPref(user_id=user_id, project_id=project_id, pinned=pinned, sort_order=sort_order))
    db.commit()


def test_order_cards_puts_pinned_first_then_sort_order(db):
    _pref(db, user_id=1, project_id=10, pinned=True, sort_order=5)
    _pref(db, user_id=1, project_id=20, pinned=False, sort_order=1)
    # 30 无偏好
    cards = [{"id": 30}, {"id": 20}, {"id": 10}]  # 乱序输入

    result = order_cards(db, user_id=1, cards=cards)

    assert [c["id"] for c in result] == [10, 20, 30]  # 置顶(10) → sort_order(20) → 无偏好(30)
    assert {c["id"]: c["pinned"] for c in result} == {10: True, 20: False, 30: False}


def test_order_cards_no_pref_keeps_input_order(db):
    cards = [{"id": 3}, {"id": 1}, {"id": 2}]

    result = order_cards(db, user_id=1, cards=cards)

    assert [c["id"] for c in result] == [3, 1, 2]
    assert all(c["pinned"] is False for c in result)


def test_save_order_assigns_index_as_sort_order(db):
    admin = User(username="admin", hashed_password="x", role="admin")
    db.add(admin)
    db.flush()
    p1 = Project(name="P1", owner_id=admin.id)
    p2 = Project(name="P2", owner_id=admin.id)
    p3 = Project(name="P3", owner_id=admin.id)
    db.add_all([p1, p2, p3])
    db.commit()

    save_order(db, admin, [
        {"project_id": p3.id, "pinned": True},
        {"project_id": p1.id, "pinned": False},
        {"project_id": p2.id, "pinned": False},
    ])

    prefs = {r.project_id: r for r in db.query(UserProjectPref).filter_by(user_id=admin.id).all()}
    assert (prefs[p3.id].sort_order, prefs[p3.id].pinned) == (0, True)
    assert prefs[p1.id].sort_order == 1
    assert prefs[p2.id].sort_order == 2


def test_save_order_ignores_inaccessible_project(db):
    member = User(username="member", hashed_password="x", role="tester", department_id=1)
    other = User(username="other", hashed_password="x", role="tester", department_id=2)
    db.add_all([member, other])
    db.flush()
    mine = Project(name="mine", owner_id=member.id, department_id=1)
    foreign = Project(name="foreign", owner_id=other.id, department_id=2)
    db.add_all([mine, foreign])
    db.commit()

    save_order(db, member, [
        {"project_id": mine.id, "pinned": True},
        {"project_id": foreign.id, "pinned": True},  # 越权：非本人非同部门
    ])

    saved = {r.project_id for r in db.query(UserProjectPref).filter_by(user_id=member.id).all()}
    assert mine.id in saved
    assert foreign.id not in saved


def test_save_order_upserts_without_duplicate(db):
    admin = User(username="admin", hashed_password="x", role="admin")
    db.add(admin)
    db.flush()
    p1 = Project(name="P1", owner_id=admin.id)
    p2 = Project(name="P2", owner_id=admin.id)
    db.add_all([p1, p2])
    db.commit()

    save_order(db, admin, [{"project_id": p1.id, "pinned": False}, {"project_id": p2.id, "pinned": False}])
    save_order(db, admin, [{"project_id": p2.id, "pinned": True}, {"project_id": p1.id, "pinned": False}])

    rows = db.query(UserProjectPref).filter_by(user_id=admin.id).all()
    assert len(rows) == 2  # 未产生重复行
    prefs = {r.project_id: r for r in rows}
    assert (prefs[p2.id].sort_order, prefs[p2.id].pinned) == (0, True)
    assert prefs[p1.id].sort_order == 1
