"""Apifox 场景编排 · 数据访问层（场景 + 步骤 + 引用计数）。不含业务校验；不提交事务。"""

from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxFolder
from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep


def list_scenarios(db: Session, project_id: int) -> List[ApifoxScenario]:
    return (
        db.query(ApifoxScenario)
        .filter(ApifoxScenario.project_id == project_id)
        .order_by(ApifoxScenario.sort_order, ApifoxScenario.id)
        .all()
    )


# ---------- 场景文件夹（复用 apifox_folders，kind='scenario'，单层） ----------
def list_scenario_folders(db: Session, project_id: int) -> List[ApifoxFolder]:
    return (
        db.query(ApifoxFolder)
        .filter(ApifoxFolder.project_id == project_id, ApifoxFolder.kind == "scenario")
        .order_by(ApifoxFolder.sort_order, ApifoxFolder.id)
        .all()
    )


def get_scenario_folder(db: Session, folder_id: int) -> Optional[ApifoxFolder]:
    return (
        db.query(ApifoxFolder)
        .filter(ApifoxFolder.id == folder_id, ApifoxFolder.kind == "scenario")
        .first()
    )


def count_folder_scenarios(db: Session, folder_id: int) -> int:
    return db.query(ApifoxScenario).filter(ApifoxScenario.folder_id == folder_id).count()


def clear_folder_on_scenarios(db: Session, folder_id: int) -> None:
    """把该文件夹下场景移到未分组（删文件夹前调用）。"""
    db.query(ApifoxScenario).filter(ApifoxScenario.folder_id == folder_id).update(
        {ApifoxScenario.folder_id: None}, synchronize_session=False
    )


def get_scenario(db: Session, scenario_id: int) -> Optional[ApifoxScenario]:
    return db.query(ApifoxScenario).filter(ApifoxScenario.id == scenario_id).first()


def list_scenarios_by_ids(db: Session, ids: List[int]) -> List[ApifoxScenario]:
    if not ids:
        return []
    return db.query(ApifoxScenario).filter(ApifoxScenario.id.in_(ids)).all()


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj) -> None:
    db.delete(obj)


def list_steps(db: Session, scenario_id: int) -> List[ApifoxScenarioStep]:
    return (
        db.query(ApifoxScenarioStep)
        .filter(ApifoxScenarioStep.scenario_id == scenario_id)
        .order_by(ApifoxScenarioStep.sort_order, ApifoxScenarioStep.id)
        .all()
    )


def group_steps_by_parent(
    db: Session, scenario_id: int
) -> Dict[Optional[int], List[ApifoxScenarioStep]]:
    """场景全部步骤按 parent_step_id 分桶（各桶内保持 list_steps 的 sort_order 序）。

    步骤树的邻接表还原点：顶层步骤在 key=None 桶，group 子步骤在 key=父步骤id 桶。
    """
    by_parent: Dict[Optional[int], List[ApifoxScenarioStep]] = defaultdict(list)
    for step in list_steps(db, scenario_id):
        by_parent[step.parent_step_id].append(step)
    return by_parent


def delete_steps(db: Session, scenario_id: int) -> None:
    db.query(ApifoxScenarioStep).filter(ApifoxScenarioStep.scenario_id == scenario_id).delete(
        synchronize_session=False
    )


def count_scenario_refs(db: Session, scenario_id: int) -> int:
    """该场景被多少个其他场景的步骤作为子场景引用。"""
    return (
        db.query(ApifoxScenarioStep)
        .filter(ApifoxScenarioStep.ref_scenario_id == scenario_id)
        .count()
    )


def count_case_refs(db: Session, case_id: int) -> int:
    """该用例被多少个场景步骤引用。"""
    return (
        db.query(ApifoxScenarioStep)
        .filter(ApifoxScenarioStep.ref_case_id == case_id)
        .count()
    )


def list_scenarios_referencing_case(db: Session, case_id: int) -> List[ApifoxScenario]:
    """步骤引用了该用例的场景（去重）——供 swagger 更新时的引用告警。"""
    return (
        db.query(ApifoxScenario)
        .join(ApifoxScenarioStep, ApifoxScenarioStep.scenario_id == ApifoxScenario.id)
        .filter(ApifoxScenarioStep.ref_case_id == case_id)
        .distinct()
        .all()
    )
