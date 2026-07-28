"""删除环境/全局变量：先清本地值，避免外键约束报错、不留孤儿本地值（Confluence 7/24-#20）。"""

from app.models.apifox.variable import (
    ApifoxEnvironment,
    ApifoxEnvironmentVariable,
    ApifoxGlobalVariable,
)
from app.repositories.apifox import variable_repo as repo
from app.services.apifox import variable_service as svc


def _env_var(db):
    env = ApifoxEnvironment(project_id=1, name="dev")
    db.add(env)
    db.commit()
    db.refresh(env)
    var = ApifoxEnvironmentVariable(environment_id=env.id, key="token", remote_value="r")
    db.add(var)
    db.commit()
    db.refresh(var)
    return var


def test_delete_env_var_cleans_local_values(db):
    var = _env_var(db)
    repo.upsert_env_local(db, var.id, user_id=7, value="mine")  # 某用户的个人本地值
    db.commit()
    assert repo.get_env_local(db, var.id, 7) is not None

    svc.delete_env_var(db, var)  # 修复前：外键约束报错 / 留孤儿本地值

    assert repo.get_env_var(db, var.id) is None
    assert repo.get_env_local(db, var.id, 7) is None  # 本地值一并清除，无孤儿


def test_delete_global_var_cleans_local_values(db):
    var = ApifoxGlobalVariable(project_id=1, key="gk", remote_value="r")
    db.add(var)
    db.commit()
    db.refresh(var)
    repo.upsert_global_local(db, var.id, user_id=9, value="mine")
    db.commit()
    assert repo.get_global_local(db, var.id, 9) is not None

    svc.delete_global_var(db, var)

    assert repo.get_global_var(db, var.id) is None
    assert repo.get_global_local(db, var.id, 9) is None
