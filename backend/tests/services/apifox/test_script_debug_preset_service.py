"""Apifox 脚本调试预设 · service 测试（项目级共享，按名 upsert）。"""

from app.routers.apifox.script_schemas import DebugPresetIn
from app.services.apifox import script_debug_preset_service as svc

PID = 1


def _in(name="p1", **kw):
    base = dict(phase="pre", variables={"a": "1"}, response_status=200, response_body="")
    base.update(kw)
    return DebugPresetIn(name=name, **base)


def test_upsert_creates_then_updates_same_name(db):
    svc.upsert_preset(db, PID, _in(variables={"a": "1"}), user_id=9)
    svc.upsert_preset(db, PID, _in(variables={"a": "2"}), user_id=9)  # 同名覆盖，不新增

    presets = svc.list_presets(db, PID)
    assert len(presets) == 1
    assert presets[0].variables == {"a": "2"}


def test_list_is_project_scoped(db):
    svc.upsert_preset(db, PID, _in(name="mine"), user_id=1)
    svc.upsert_preset(db, 2, _in(name="other"), user_id=1)  # 另一个项目

    names = [p.name for p in svc.list_presets(db, PID)]
    assert names == ["mine"]  # 只看本项目


def test_variables_and_response_round_trip(db):
    svc.upsert_preset(
        db, PID, _in(name="post", phase="post", variables={"x": "y"}, response_status=404, response_body='{"e":1}'),
        user_id=1,
    )

    p = svc.list_presets(db, PID)[0]
    assert p.phase == "post"
    assert p.variables == {"x": "y"}
    assert p.response_status == 404
    assert p.response_body == '{"e":1}'


def test_delete_removes_and_rejects_wrong_project(db):
    out = svc.upsert_preset(db, PID, _in(name="del"), user_id=1)

    assert svc.delete_preset(db, 999, out.id) is False  # 不属于该项目，不删
    assert svc.delete_preset(db, PID, out.id) is True
    assert svc.list_presets(db, PID) == []
