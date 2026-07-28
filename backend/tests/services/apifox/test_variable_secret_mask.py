"""密文变量对外脱敏：VariableOut 不返回明文；运行时解析仍读真值（Confluence #11 / WYSIWYG）。"""

from app.models.apifox.variable import (
    ApifoxEnvironment,
    ApifoxEnvironmentVariable,
    ApifoxGlobalVariable,
)
from app.repositories.apifox import variable_repo as repo
from app.services.apifox import variable_service as svc
from app.services.apifox import variables as resolver


def _env(db):
    env = ApifoxEnvironment(project_id=1, name="dev")
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


def test_secret_env_var_masked_in_output(db):
    env = _env(db)
    db.add(ApifoxEnvironmentVariable(
        environment_id=env.id, key="pwd", remote_value="s3cr3t", is_secret=True
    ))
    db.commit()

    row = svc.list_env_vars(db, env.id, user_id=1)[0]
    assert row.remote_value == svc.SECRET_MASK
    assert row.effective_value == svc.SECRET_MASK  # 有效值也不泄明文


def test_non_secret_env_var_not_masked(db):
    env = _env(db)
    db.add(ApifoxEnvironmentVariable(
        environment_id=env.id, key="host", remote_value="api.local", is_secret=False
    ))
    db.commit()

    row = svc.list_env_vars(db, env.id, user_id=1)[0]
    assert row.remote_value == "api.local"


def test_secret_local_value_masked(db):
    env = _env(db)
    var = ApifoxEnvironmentVariable(
        environment_id=env.id, key="pwd", remote_value="remote", is_secret=True
    )
    db.add(var)
    db.commit()
    db.refresh(var)
    repo.upsert_env_local(db, var.id, user_id=7, value="mine")
    db.commit()

    row = svc.list_env_vars(db, env.id, user_id=7)[0]
    assert row.local_value == svc.SECRET_MASK
    assert row.effective_value == svc.SECRET_MASK


def test_secret_global_var_masked(db):
    db.add(ApifoxGlobalVariable(project_id=1, key="token", remote_value="glpat-x", is_secret=True))
    db.commit()

    row = svc.list_global_vars(db, project_id=1, user_id=1)[0]
    assert row.remote_value == svc.SECRET_MASK


def test_runtime_resolution_uses_real_value_not_mask(db):
    """脱敏只作用于展示 DTO：执行引擎解析变量拿到的仍是真值（所配即所发）。"""
    env = _env(db)
    var = ApifoxEnvironmentVariable(
        environment_id=env.id, key="pwd", remote_value="s3cr3t", is_secret=True
    )
    db.add(var)
    db.commit()

    resolved = resolver.resolve_env_vars(db, env.id, user_id=1)
    assert resolved["pwd"] == "s3cr3t"  # 非掩码
