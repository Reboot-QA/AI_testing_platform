"""Apifox 环境·变量 · 数据访问层（环境 / 环境变量 / 环境变量本地值 / 全局变量 / 全局本地值）。

不含业务校验与权限；不提交事务（由 service commit）。local 值 upsert：value=None 视为清除（删行）。
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.variable import (
    ApifoxEnvironment,
    ApifoxEnvironmentServer,
    ApifoxEnvironmentVariable,
    ApifoxEnvironmentVarLocal,
    ApifoxGlobalVariable,
    ApifoxGlobalVarLocal,
)


# ---------- environments ----------
def list_environments(db: Session, project_id: int) -> List[ApifoxEnvironment]:
    return (
        db.query(ApifoxEnvironment)
        .filter(ApifoxEnvironment.project_id == project_id)
        .order_by(ApifoxEnvironment.sort_order, ApifoxEnvironment.id)
        .all()
    )


def get_environment(db: Session, env_id: int) -> Optional[ApifoxEnvironment]:
    return db.query(ApifoxEnvironment).filter(ApifoxEnvironment.id == env_id).first()


# ---------- environment servers（命名前置 URL） ----------
def list_servers(db: Session, environment_id: int) -> List[ApifoxEnvironmentServer]:
    return (
        db.query(ApifoxEnvironmentServer)
        .filter(ApifoxEnvironmentServer.environment_id == environment_id)
        .order_by(ApifoxEnvironmentServer.sort_order, ApifoxEnvironmentServer.id)
        .all()
    )


def get_server(db: Session, server_id: int) -> Optional[ApifoxEnvironmentServer]:
    return db.query(ApifoxEnvironmentServer).filter(ApifoxEnvironmentServer.id == server_id).first()


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj) -> None:
    db.delete(obj)


# ---------- environment variables ----------
def list_env_vars(db: Session, environment_id: int) -> List[ApifoxEnvironmentVariable]:
    return (
        db.query(ApifoxEnvironmentVariable)
        .filter(ApifoxEnvironmentVariable.environment_id == environment_id)
        .order_by(ApifoxEnvironmentVariable.sort_order, ApifoxEnvironmentVariable.id)
        .all()
    )


def get_env_var(db: Session, var_id: int) -> Optional[ApifoxEnvironmentVariable]:
    return db.query(ApifoxEnvironmentVariable).filter(ApifoxEnvironmentVariable.id == var_id).first()


def get_env_local(db: Session, var_id: int, user_id: int) -> Optional[ApifoxEnvironmentVarLocal]:
    return (
        db.query(ApifoxEnvironmentVarLocal)
        .filter(
            ApifoxEnvironmentVarLocal.environment_variable_id == var_id,
            ApifoxEnvironmentVarLocal.user_id == user_id,
        )
        .first()
    )


def upsert_env_local(db: Session, var_id: int, user_id: int, value: Optional[str]) -> None:
    row = get_env_local(db, var_id, user_id)
    if value is None:
        if row:
            db.delete(row)
        return
    if row:
        row.local_value = value
    else:
        db.add(
            ApifoxEnvironmentVarLocal(
                environment_variable_id=var_id, user_id=user_id, local_value=value
            )
        )


# ---------- global variables ----------
def list_global_vars(db: Session, project_id: int) -> List[ApifoxGlobalVariable]:
    return (
        db.query(ApifoxGlobalVariable)
        .filter(ApifoxGlobalVariable.project_id == project_id)
        .order_by(ApifoxGlobalVariable.sort_order, ApifoxGlobalVariable.id)
        .all()
    )


def get_global_var(db: Session, var_id: int) -> Optional[ApifoxGlobalVariable]:
    return db.query(ApifoxGlobalVariable).filter(ApifoxGlobalVariable.id == var_id).first()


def get_global_local(db: Session, var_id: int, user_id: int) -> Optional[ApifoxGlobalVarLocal]:
    return (
        db.query(ApifoxGlobalVarLocal)
        .filter(
            ApifoxGlobalVarLocal.global_variable_id == var_id,
            ApifoxGlobalVarLocal.user_id == user_id,
        )
        .first()
    )


def upsert_global_local(db: Session, var_id: int, user_id: int, value: Optional[str]) -> None:
    row = get_global_local(db, var_id, user_id)
    if value is None:
        if row:
            db.delete(row)
        return
    if row:
        row.local_value = value
    else:
        db.add(ApifoxGlobalVarLocal(global_variable_id=var_id, user_id=user_id, local_value=value))
