"""Apifox 场景编排 · 业务层（步骤树校验 + 子场景防循环 + bulk replace + 展示字段回显）。

步骤为可嵌套树：控制步骤(group)用 children 承载子步骤，邻接表 parent_step_id 落库。
非法输入抛 ValueError（router 转 400）。写操作末尾 commit。权限在 router。
"""

import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep
from app.repositories.apifox import case_repo, endpoint_repo
from app.repositories.apifox import scenario_repo as repo
from app.routers.apifox.scenario_schemas import (
    ScenarioBrief,
    ScenarioCreate,
    ScenarioOut,
    ScenarioUpdate,
    StepIn,
    StepOut,
)
from app.services.apifox.run_engine import CONDITION_OPERATORS, MAX_LOOP_ITERATIONS

VALID_STEP_TYPES = {"case", "wait", "scenario", "group", "if", "else", "loop"}
# 可嵌套子步骤的容器型步骤
CONTAINER_STEP_TYPES = {"group", "if", "else", "loop"}
_MAX_NEST_DEPTH = 50


def _would_cycle(db: Session, root_id: int, ref_scenario_id: int) -> bool:
    """从 ref 场景沿子场景引用深度遍历，能回到 root 即成环。"""
    stack = [(ref_scenario_id, 0)]
    seen: set[int] = set()
    while stack:
        current, depth = stack.pop()
        if current == root_id:
            return True
        if current in seen or depth > _MAX_NEST_DEPTH:
            continue
        seen.add(current)
        for step in repo.list_steps(db, current):
            if step.type == "scenario" and step.ref_scenario_id:
                stack.append((step.ref_scenario_id, depth + 1))
    return False


def _validate_step(db: Session, scenario: ApifoxScenario, step: StepIn) -> None:
    if step.type not in VALID_STEP_TYPES:
        raise ValueError("无效的步骤类型")
    if step.children and step.type not in CONTAINER_STEP_TYPES:
        raise ValueError("仅容器型步骤（分组）可包含子步骤")
    if step.type == "case":
        if not step.ref_case_id:
            raise ValueError("用例步骤必须指定 ref_case_id")
        case = case_repo.get_case(db, step.ref_case_id)
        if not case or case.project_id != scenario.project_id:
            raise ValueError("引用的用例不存在或不属于该项目")
    elif step.type == "wait":
        if not step.wait_ms or step.wait_ms <= 0:
            raise ValueError("等待步骤必须指定大于 0 的 wait_ms")
    elif step.type == "scenario":
        if not step.ref_scenario_id:
            raise ValueError("子场景步骤必须指定 ref_scenario_id")
        if step.ref_scenario_id == scenario.id:
            raise ValueError("子场景不能引用自身")
        ref = repo.get_scenario(db, step.ref_scenario_id)
        if not ref or ref.project_id != scenario.project_id:
            raise ValueError("引用的子场景不存在或不属于该项目")
        if _would_cycle(db, scenario.id, step.ref_scenario_id):
            raise ValueError("子场景引用形成循环，请调整场景结构")
    elif step.type == "if":
        condition = (step.config or {}).get("condition") if step.config else None
        if not isinstance(condition, dict):
            raise ValueError("条件(if)步骤必须配置 condition")
        operator = str(condition.get("operator") or "")
        if operator not in CONDITION_OPERATORS:
            raise ValueError(f"条件操作符非法：{operator or '(空)'}")
    elif step.type == "loop":
        _validate_loop(step.config or {})


def _validate_loop(config: dict) -> None:
    mode = config.get("mode")
    if mode == "count":
        count = config.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or not 0 < count <= MAX_LOOP_ITERATIONS:
            raise ValueError(f"循环次数必须为 1~{MAX_LOOP_ITERATIONS} 的整数")
    elif mode == "list":
        if not config.get("list_var"):
            raise ValueError("列表循环必须指定 list_var（存 JSON 数组的变量名）")
    elif mode == "while":
        condition = config.get("condition")
        if not isinstance(condition, dict) or str(condition.get("operator") or "") not in CONDITION_OPERATORS:
            raise ValueError("while 循环必须配置合法 condition")
        max_iter = config.get("max_iterations")
        if not isinstance(max_iter, int) or isinstance(max_iter, bool) or not 0 < max_iter <= MAX_LOOP_ITERATIONS:
            raise ValueError(f"while 循环 max_iterations 必须为 1~{MAX_LOOP_ITERATIONS} 的整数")
    else:
        raise ValueError("循环模式非法（count/list/while）")


def _write_steps(
    db: Session,
    scenario: ApifoxScenario,
    steps: List[StepIn],
    parent_id: Optional[int] = None,
    depth: int = 0,
    parent_type: Optional[str] = None,
) -> None:
    """递归落库步骤树：先写父行拿到 id，再以其为 parent_id 写子步骤。"""
    if depth > _MAX_NEST_DEPTH:
        raise ValueError("步骤嵌套层级过深")
    else_count = 0
    for i, s in enumerate(steps):
        if s.type == "else":
            if parent_type != "if":
                raise ValueError("else 步骤只能作为条件(if)步骤的子步骤")
            else_count += 1
            if else_count > 1:
                raise ValueError("一个条件(if)步骤至多一个 else 分支")
        _validate_step(db, scenario, s)
        row = ApifoxScenarioStep(
            scenario_id=scenario.id,
            parent_step_id=parent_id,
            type=s.type,
            ref_case_id=s.ref_case_id if s.type == "case" else None,
            ref_scenario_id=s.ref_scenario_id if s.type == "scenario" else None,
            wait_ms=s.wait_ms if s.type == "wait" else None,
            config=json.dumps(s.config, ensure_ascii=False) if s.config else None,
            name=s.name,
            enabled=s.enabled,
            sort_order=i,
        )
        repo.add(db, row)  # flush 后 row.id 可用作子步骤 parent_id
        if s.children:
            _write_steps(
                db, scenario, s.children, parent_id=row.id, depth=depth + 1, parent_type=s.type
            )


def _step_out(
    db: Session,
    step: ApifoxScenarioStep,
    by_parent: Dict[Optional[int], List[ApifoxScenarioStep]],
) -> StepOut:
    out = StepOut(
        type=step.type,
        ref_case_id=step.ref_case_id,
        ref_scenario_id=step.ref_scenario_id,
        wait_ms=step.wait_ms,
        config=json.loads(step.config) if step.config else None,
        name=step.name,
        enabled=step.enabled,
        children=[_step_out(db, c, by_parent) for c in by_parent.get(step.id, [])],
    )
    if step.type == "case" and step.ref_case_id:
        case = case_repo.get_case(db, step.ref_case_id)
        if case:
            out.case_name = case.name
            endpoint = endpoint_repo.get_endpoint(db, case.endpoint_id)
            if endpoint:
                out.endpoint_method = endpoint.method
                out.endpoint_path = endpoint.path
    elif step.type == "scenario" and step.ref_scenario_id:
        ref = repo.get_scenario(db, step.ref_scenario_id)
        if ref:
            out.scenario_name = ref.name
    return out


def _out(db: Session, scenario: ApifoxScenario) -> ScenarioOut:
    by_parent = repo.group_steps_by_parent(db, scenario.id)
    return ScenarioOut(
        id=scenario.id,
        project_id=scenario.project_id,
        name=scenario.name,
        description=scenario.description,
        steps=[_step_out(db, s, by_parent) for s in by_parent.get(None, [])],
        sort_order=scenario.sort_order,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


def list_scenarios(db: Session, project_id: int) -> List[ScenarioBrief]:
    return [
        ScenarioBrief(
            id=s.id,
            name=s.name,
            description=s.description,
            step_count=len(repo.list_steps(db, s.id)),
            sort_order=s.sort_order,
        )
        for s in repo.list_scenarios(db, project_id)
    ]


def create_scenario(db: Session, project_id: int, data: ScenarioCreate) -> ScenarioOut:
    scenario = ApifoxScenario(project_id=project_id, name=data.name, description=data.description)
    repo.add(db, scenario)
    _write_steps(db, scenario, data.steps)
    db.commit()
    db.refresh(scenario)
    return _out(db, scenario)


def get_scenario_out(db: Session, scenario: ApifoxScenario) -> ScenarioOut:
    return _out(db, scenario)


def update_scenario(db: Session, scenario: ApifoxScenario, data: ScenarioUpdate) -> ScenarioOut:
    if data.name is not None:
        scenario.name = data.name
    if "description" in data.model_fields_set:
        scenario.description = data.description
    if data.sort_order is not None:
        scenario.sort_order = data.sort_order
    if data.steps is not None:
        repo.delete_steps(db, scenario.id)
        _write_steps(db, scenario, data.steps)
    db.commit()
    db.refresh(scenario)
    return _out(db, scenario)


def delete_scenario(db: Session, scenario: ApifoxScenario) -> None:
    refs = repo.count_scenario_refs(db, scenario.id)
    if refs:
        raise ValueError(f"场景被 {refs} 处其他场景作为子场景引用，请先解除引用再删除")
    repo.delete_steps(db, scenario.id)
    repo.delete(db, scenario)
    db.commit()
