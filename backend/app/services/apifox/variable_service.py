"""Apifox 环境·变量 · 业务层（归属校验 + 行级增改删 + per-user 本地值叠加）。

有效值 = 当前用户本地值 若存在 else 远程值。唯一 key 冲突抛 ValueError（router 转 400）。
写操作末尾 commit。不做权限判定（router 用 project_access_service）。执行时变量合并留 P4。
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.variable import (
    ApifoxEnvironment,
    ApifoxEnvironmentVariable,
    ApifoxGlobalVariable,
)
from app.repositories.apifox import variable_repo as repo
from app.routers.apifox.variable_schemas import (
    EnvironmentCreate,
    EnvironmentOut,
    EnvironmentUpdate,
    VariableCreate,
    VariableOut,
    VariableUpdate,
)


# ---------- environments ----------
def _env_out(env: ApifoxEnvironment) -> EnvironmentOut:
    return EnvironmentOut(
        id=env.id,
        project_id=env.project_id,
        name=env.name,
        base_url=env.base_url,
        is_default=env.is_default,
        sort_order=env.sort_order,
    )


def _clear_other_defaults(db: Session, project_id: int, keep_id: int | None) -> None:
    for e in repo.list_environments(db, project_id):
        if e.id != keep_id and e.is_default:
            e.is_default = False


def list_environments(db: Session, project_id: int) -> List[EnvironmentOut]:
    return [_env_out(e) for e in repo.list_environments(db, project_id)]


def create_environment(db: Session, project_id: int, data: EnvironmentCreate) -> EnvironmentOut:
    env = ApifoxEnvironment(
        project_id=project_id, name=data.name, base_url=data.base_url, is_default=data.is_default
    )
    repo.add(db, env)
    if data.is_default:
        _clear_other_defaults(db, project_id, env.id)
    db.commit()
    db.refresh(env)
    return _env_out(env)


def update_environment(
    db: Session, env: ApifoxEnvironment, data: EnvironmentUpdate
) -> EnvironmentOut:
    if data.name is not None:
        env.name = data.name
    if "base_url" in data.model_fields_set:
        env.base_url = data.base_url
    if data.sort_order is not None:
        env.sort_order = data.sort_order
    if data.is_default is not None:
        env.is_default = data.is_default
        if data.is_default:
            _clear_other_defaults(db, env.project_id, env.id)
    db.commit()
    db.refresh(env)
    return _env_out(env)


def delete_environment(db: Session, env: ApifoxEnvironment) -> None:
    for var in repo.list_env_vars(db, env.id):
        repo.delete(db, var)  # 连带删环境变量（本地值由 FK 悬挂风险——见下 cleanup）
    repo.delete(db, env)
    db.commit()


# ---------- 环境变量 ----------
def _env_var_out(db: Session, var: ApifoxEnvironmentVariable, user_id: int) -> VariableOut:
    local = repo.get_env_local(db, var.id, user_id)
    local_value = local.local_value if local else None
    return VariableOut(
        id=var.id,
        key=var.key,
        remote_value=var.remote_value,
        local_value=local_value,
        effective_value=local_value if local else var.remote_value,
        is_secret=var.is_secret,
        enabled=var.enabled,
        sort_order=var.sort_order,
    )


def list_env_vars(db: Session, environment_id: int, user_id: int) -> List[VariableOut]:
    return [_env_var_out(db, v, user_id) for v in repo.list_env_vars(db, environment_id)]


def create_env_var(
    db: Session, environment_id: int, data: VariableCreate, user_id: int
) -> VariableOut:
    if any(v.key == data.key for v in repo.list_env_vars(db, environment_id)):
        raise ValueError("变量名已存在")
    var = ApifoxEnvironmentVariable(
        environment_id=environment_id,
        key=data.key,
        remote_value=data.remote_value,
        is_secret=data.is_secret,
        enabled=data.enabled,
    )
    repo.add(db, var)
    db.commit()
    db.refresh(var)
    return _env_var_out(db, var, user_id)


def update_env_var(
    db: Session, var: ApifoxEnvironmentVariable, data: VariableUpdate, user_id: int
) -> VariableOut:
    if data.key is not None and data.key != var.key:
        if any(
            v.key == data.key and v.id != var.id
            for v in repo.list_env_vars(db, var.environment_id)
        ):
            raise ValueError("变量名已存在")
        var.key = data.key
    if "remote_value" in data.model_fields_set:
        var.remote_value = data.remote_value
    if data.is_secret is not None:
        var.is_secret = data.is_secret
    if data.enabled is not None:
        var.enabled = data.enabled
    if data.sort_order is not None:
        var.sort_order = data.sort_order
    db.commit()
    db.refresh(var)
    return _env_var_out(db, var, user_id)


def delete_env_var(db: Session, var: ApifoxEnvironmentVariable) -> None:
    repo.delete(db, var)
    db.commit()


def set_env_local(
    db: Session, var: ApifoxEnvironmentVariable, user_id: int, value: str | None
) -> VariableOut:
    repo.upsert_env_local(db, var.id, user_id, value)
    db.commit()
    return _env_var_out(db, var, user_id)


# ---------- 全局变量 ----------
def _global_var_out(db: Session, var: ApifoxGlobalVariable, user_id: int) -> VariableOut:
    local = repo.get_global_local(db, var.id, user_id)
    local_value = local.local_value if local else None
    return VariableOut(
        id=var.id,
        key=var.key,
        remote_value=var.remote_value,
        local_value=local_value,
        effective_value=local_value if local else var.remote_value,
        is_secret=var.is_secret,
        enabled=var.enabled,
        sort_order=var.sort_order,
    )


def list_global_vars(db: Session, project_id: int, user_id: int) -> List[VariableOut]:
    return [_global_var_out(db, v, user_id) for v in repo.list_global_vars(db, project_id)]


def create_global_var(
    db: Session, project_id: int, data: VariableCreate, user_id: int
) -> VariableOut:
    if any(v.key == data.key for v in repo.list_global_vars(db, project_id)):
        raise ValueError("变量名已存在")
    var = ApifoxGlobalVariable(
        project_id=project_id,
        key=data.key,
        remote_value=data.remote_value,
        is_secret=data.is_secret,
        enabled=data.enabled,
    )
    repo.add(db, var)
    db.commit()
    db.refresh(var)
    return _global_var_out(db, var, user_id)


def update_global_var(
    db: Session, var: ApifoxGlobalVariable, data: VariableUpdate, user_id: int
) -> VariableOut:
    if data.key is not None and data.key != var.key:
        if any(
            v.key == data.key and v.id != var.id
            for v in repo.list_global_vars(db, var.project_id)
        ):
            raise ValueError("变量名已存在")
        var.key = data.key
    if "remote_value" in data.model_fields_set:
        var.remote_value = data.remote_value
    if data.is_secret is not None:
        var.is_secret = data.is_secret
    if data.enabled is not None:
        var.enabled = data.enabled
    if data.sort_order is not None:
        var.sort_order = data.sort_order
    db.commit()
    db.refresh(var)
    return _global_var_out(db, var, user_id)


def delete_global_var(db: Session, var: ApifoxGlobalVariable) -> None:
    repo.delete(db, var)
    db.commit()


def set_global_local(
    db: Session, var: ApifoxGlobalVariable, user_id: int, value: str | None
) -> VariableOut:
    repo.upsert_global_local(db, var.id, user_id, value)
    db.commit()
    return _global_var_out(db, var, user_id)
