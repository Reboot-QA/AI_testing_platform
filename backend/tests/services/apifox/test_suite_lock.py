"""测试套件乐观锁保存冲突检测（与用例/场景/接口一致）。

被测：suite_service.update_suite 的 version 校验与自增。
"""

import pytest

from app.repositories.apifox import suite_repo
from app.routers.apifox.suite_schemas import SuiteCreate, SuiteUpdate
from app.services.apifox import suite_service
from app.services.apifox.errors import ConflictError


def _new_suite(db, name="s"):
    created = suite_service.create_suite(db, 1, SuiteCreate(name=name))
    return created, suite_repo.get_suite(db, created.id)


def test_suite_create_starts_at_version_1(db):
    created, _ = _new_suite(db)

    assert created.version == 1


def test_suite_update_matching_version_increments(db):
    _, suite = _new_suite(db)

    out = suite_service.update_suite(db, suite, SuiteUpdate(name="s2", expected_version=1))

    assert out.version == 2


def test_suite_update_stale_version_raises_conflict(db):
    _, suite = _new_suite(db)
    suite_service.update_suite(db, suite, SuiteUpdate(name="s2", expected_version=1))  # → v2

    with pytest.raises(ConflictError) as ei:
        suite_service.update_suite(db, suite, SuiteUpdate(name="s3", expected_version=1))  # 旧版本

    assert ei.value.current_version == 2


def test_suite_update_without_version_backward_compat(db):
    _, suite = _new_suite(db)

    out = suite_service.update_suite(db, suite, SuiteUpdate(name="s2"))  # 不传 expected_version

    assert out.version == 2  # 仍自增，但不做冲突校验


def test_suite_conflict_does_not_mutate(db):
    _, suite = _new_suite(db, name="orig")
    suite_service.update_suite(db, suite, SuiteUpdate(name="v2", expected_version=1))  # → v2

    with pytest.raises(ConflictError):
        suite_service.update_suite(db, suite, SuiteUpdate(name="nope", expected_version=1))

    assert suite.name == "v2"  # 冲突时不落任何改动
