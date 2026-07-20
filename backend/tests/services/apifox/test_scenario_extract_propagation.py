"""回归：后置提取的临时变量应在同场景后续步骤 {{var}} 可用。

c1 提取 token（临时）→ c2 请求头用 {{token}}，mock HTTP，校验 c2 实际请求头拿到 token。
"""

import json

import httpx

from app.models.apifox.endpoint import ApifoxEndpoint
from app.routers.apifox.scenario_schemas import ScenarioCreate, StepIn
from app.services.apifox import run_engine, run_service
from app.services.apifox import scenario_service as svc


def _ep(db, case):
    return db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == case.endpoint_id).first()


def test_temp_extract_propagates_to_next_step(db, make_case, monkeypatch):
    c1 = make_case(name="c1")
    ep1 = _ep(db, c1)
    ep1.path = "http://t.local/login"
    c1.post_processors = json.dumps(
        [{"kind": "extract", "var_name": "token", "source": "response_json", "path": "$.token", "scope": "temporary"}]
    )

    c2 = make_case(name="c2")
    ep2 = _ep(db, c2)
    ep2.path = "http://t.local/next"
    c2.request_spec = json.dumps({"headers": [{"key": "X-Token", "value": "{{token}}", "enabled": True}]})
    db.commit()

    out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="s",
            steps=[StepIn(type="case", ref_case_id=c1.id), StepIn(type="case", ref_case_id=c2.id)],
        ),
    )
    scenario = svc.repo.get_scenario(db, out.id)

    calls = []

    def _fake_send(plan, detail, **kw):
        calls.append(plan)
        detail["duration_ms"] = 1.0
        body = '{"token":"T"}' if "login" in plan["url"] else "{}"
        return httpx.Response(
            200, content=body.encode(), headers={"Content-Type": "application/json"},
            request=httpx.Request("GET", "http://t.local/"),
        )

    monkeypatch.setattr(run_engine, "_send_request", _fake_send)

    list(run_service.iter_scenario_run(db, scenario, None, "test", user_id=1))

    next_call = next(p for p in calls if "next" in p["url"])
    assert next_call["headers"].get("X-Token") == "T"
