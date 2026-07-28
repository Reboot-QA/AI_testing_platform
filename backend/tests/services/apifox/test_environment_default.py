"""环境默认值规则（回归 bug：默认环境）。

- 项目内首个环境自动设为默认（此前需显式勾选，导致一个默认都没有）。
- 删除默认环境后，若仍有其它环境，自动补选一个新默认（保证 >=1 环境时恒有唯一默认）。
"""

from app.models.apifox.variable import ApifoxEnvironment
from app.routers.apifox.variable_schemas import EnvironmentCreate
from app.services.apifox.variable_service import (
    create_environment,
    delete_environment,
    list_environments,
)

PID = 1


def _create(db, name, is_default=False):
    return create_environment(db, PID, EnvironmentCreate(name=name, is_default=is_default))


def _defaults(db):
    return [e for e in list_environments(db, PID) if e.is_default]


def test_first_environment_auto_becomes_default(db):
    env = _create(db, "dev")

    assert env.is_default is True


def test_second_environment_not_auto_default(db):
    _create(db, "dev")

    second = _create(db, "prod")

    assert second.is_default is False
    assert len(_defaults(db)) == 1


def test_explicit_default_on_second_clears_first(db):
    _create(db, "dev")

    _create(db, "prod", is_default=True)

    envs = {e.name: e for e in list_environments(db, PID)}
    assert envs["prod"].is_default is True
    assert envs["dev"].is_default is False
    assert len(_defaults(db)) == 1


def test_delete_default_promotes_another(db):
    first = _create(db, "dev")
    _create(db, "prod")

    delete_environment(db, db.get(ApifoxEnvironment, first.id))

    remaining = _defaults(db)
    assert len(remaining) == 1
    assert remaining[0].name == "prod"


def test_delete_non_default_keeps_default(db):
    _create(db, "dev")
    second = _create(db, "prod")

    delete_environment(db, db.get(ApifoxEnvironment, second.id))

    remaining = _defaults(db)
    assert len(remaining) == 1
    assert remaining[0].name == "dev"
