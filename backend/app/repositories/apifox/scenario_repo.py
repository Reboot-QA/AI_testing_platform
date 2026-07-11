"""Apifox 场景编排 · 数据访问层（场景 + 步骤 + 引用计数）。不含业务校验；不提交事务。"""

from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep


def list_scenarios(db: Session, project_id: int) -> List[ApifoxScenario]:
    return (
        db.query(ApifoxScenario)
        .filter(ApifoxScenario.project_id == project_id)
        .order_by(ApifoxScenario.sort_order, ApifoxScenario.id)
        .all()
    )


def get_scenario(db: Session, scenario_id: int) -> Optional[ApifoxScenario]:
    return db.query(ApifoxScenario).filter(ApifoxScenario.id == scenario_id).first()


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
