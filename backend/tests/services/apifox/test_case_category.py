"""单接口用例分类（对齐 Apifox：正向/逆向/边界值/安全性/其他）· 读写与校验。"""

import pytest

from app.repositories.apifox import case_repo
from app.routers.apifox.case_schemas import CaseCreate, CaseUpdate
from app.services.apifox import case_service as svc


def _create(db, endpoint, category="other", name="c"):
    return svc.create_case(db, endpoint.project_id, endpoint.id, CaseCreate(name=name, category=category))


def test_create_persists_category(db, make_endpoint):
    out = _create(db, make_endpoint(), category="positive")

    assert out.category == "positive"


def test_create_defaults_to_other(db, make_endpoint):
    ep = make_endpoint()

    out = svc.create_case(db, ep.project_id, ep.id, CaseCreate(name="c"))

    assert out.category == "other"


def test_invalid_category_rejected(db, make_endpoint):
    with pytest.raises(ValueError, match="非法用例分类"):
        _create(db, make_endpoint(), category="bogus")


def test_update_changes_category(db, make_endpoint):
    out = _create(db, make_endpoint(), category="other")
    case = case_repo.get_case(db, out.id)

    updated = svc.update_case(db, case, CaseUpdate(category="security", expected_version=out.version))

    assert updated.category == "security"


def test_update_invalid_category_rejected(db, make_endpoint):
    out = _create(db, make_endpoint())
    case = case_repo.get_case(db, out.id)

    with pytest.raises(ValueError, match="非法用例分类"):
        svc.update_case(db, case, CaseUpdate(category="nope", expected_version=out.version))


def test_list_cases_returns_category(db, make_endpoint):
    ep = make_endpoint()
    _create(db, ep, category="boundary", name="b")

    briefs = svc.list_cases(db, ep.id)

    assert [b.category for b in briefs] == ["boundary"]
