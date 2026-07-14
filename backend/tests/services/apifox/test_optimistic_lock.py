"""G1 多人协同 · 用例/场景乐观锁保存冲突检测。

被测：case_service.update_case / scenario_service.update_scenario 的 version 校验与自增。
"""

import pytest

from app.routers.apifox.case_schemas import CaseUpdate
from app.routers.apifox.scenario_schemas import ScenarioCreate, ScenarioUpdate
from app.services.apifox import case_service, scenario_service
from app.services.apifox.errors import ConflictError


# ---------- 用例 ----------
def test_case_update_matching_version_increments(db, make_case):
    case = make_case(name="c")
    assert case.version == 1

    out = case_service.update_case(db, case, CaseUpdate(name="c2", expected_version=1))

    assert out.version == 2


def test_case_update_stale_version_raises_conflict(db, make_case):
    case = make_case(name="c")
    case_service.update_case(db, case, CaseUpdate(name="c2", expected_version=1))  # → v2

    with pytest.raises(ConflictError) as ei:
        case_service.update_case(db, case, CaseUpdate(name="c3", expected_version=1))  # 旧版本

    assert ei.value.current_version == 2


def test_case_update_without_version_backward_compat(db, make_case):
    case = make_case(name="c")

    out = case_service.update_case(db, case, CaseUpdate(name="c2"))  # 不传 expected_version

    assert out.version == 2  # 仍自增，但不做冲突校验


def test_case_conflict_does_not_mutate(db, make_case):
    case = make_case(name="orig")
    case_service.update_case(db, case, CaseUpdate(name="v2", expected_version=1))  # → v2

    with pytest.raises(ConflictError):
        case_service.update_case(db, case, CaseUpdate(name="should-not-apply", expected_version=1))

    assert case.name == "v2"  # 冲突时不落任何改动


# ---------- 场景 ----------
def _scenario(db):
    return scenario_service.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[]))


def test_scenario_update_matching_version_increments(db):
    out = _scenario(db)
    assert out.version == 1
    scenario = scenario_service.repo.get_scenario(db, out.id)

    updated = scenario_service.update_scenario(db, scenario, ScenarioUpdate(name="s2", expected_version=1))

    assert updated.version == 2


def test_scenario_update_stale_version_raises_conflict(db):
    out = _scenario(db)
    scenario = scenario_service.repo.get_scenario(db, out.id)
    scenario_service.update_scenario(db, scenario, ScenarioUpdate(name="s2", expected_version=1))  # → v2

    with pytest.raises(ConflictError) as ei:
        scenario_service.update_scenario(db, scenario, ScenarioUpdate(name="s3", expected_version=1))

    assert ei.value.current_version == 2


def test_scenario_update_without_version_backward_compat(db):
    out = _scenario(db)
    scenario = scenario_service.repo.get_scenario(db, out.id)

    updated = scenario_service.update_scenario(db, scenario, ScenarioUpdate(name="s2"))

    assert updated.version == 2
