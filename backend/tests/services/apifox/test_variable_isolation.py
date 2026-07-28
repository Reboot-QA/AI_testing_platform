"""个人「本地值」按用户隔离：A 设的本地值 B 看不到，只共享远程值（Confluence 7/24-#18）。"""

from app.models.apifox.variable import (
    ApifoxEnvironment,
    ApifoxEnvironmentVariable,
    ApifoxGlobalVariable,
)
from app.services.apifox import variable_service as svc


def _env_var(db):
    env = ApifoxEnvironment(project_id=1, name="dev")
    db.add(env)
    db.commit()
    db.refresh(env)
    var = ApifoxEnvironmentVariable(environment_id=env.id, key="token", remote_value="shared")
    db.add(var)
    db.commit()
    db.refresh(var)
    return env, var


def test_env_local_value_isolated_between_users(db):
    env, var = _env_var(db)
    svc.set_env_local(db, var, user_id=1, value="A-private")  # 用户 A 设本地值

    row_b = svc.list_env_vars(db, env.id, user_id=2)[0]  # 用户 B 查看
    assert row_b.local_value is None  # 看不到 A 的本地值
    assert row_b.effective_value == "shared"  # 只落到共享远程值

    row_a = svc.list_env_vars(db, env.id, user_id=1)[0]  # 用户 A 查看
    assert row_a.local_value == "A-private"  # A 能看到自己的
    assert row_a.effective_value == "A-private"


def test_global_local_value_isolated_between_users(db):
    var = ApifoxGlobalVariable(project_id=1, key="g", remote_value="shared")
    db.add(var)
    db.commit()
    db.refresh(var)
    svc.set_global_local(db, var, user_id=1, value="A-private")

    row_b = svc.list_global_vars(db, project_id=1, user_id=2)[0]
    assert row_b.local_value is None
    assert row_b.effective_value == "shared"
