"""Apifox 执行引擎 · 场景流程控制纯函数（循环迭代序列 / 条件求值）。

loop_iterations 预算 count/list 两模式的每轮变量注入（while 由编排层逐轮求值）；
evaluate_condition 求值场景条件（{{var}} 插值 + 复用操作符比较）。
依赖底层 variables（插值）与 operators（比较），无副作用、不落库。
"""

import json
from typing import Any, Dict, List, Tuple

from app.services.apifox.operators import _apply_operator
from app.services.apifox.variables import VARIABLE_PATTERN, apply_vars

# 循环步骤(loop)硬上限：三种模式都兜底，防死循环/超大 count 拖垮执行
MAX_LOOP_ITERATIONS = 1000


def loop_iterations(config: Dict[str, Any], variables: Dict[str, str]) -> List[Dict[str, str]]:
    """count/list 模式的每轮变量注入列表（while 由编排层逐轮求值，不走这里）。

    count：注入 index_var（0 基）；list：解析 list_var（JSON 数组）注入 item_var+index_var，
    非字符串元素 JSON 序列化。无效/缺失 → []；超硬上限 → 截断。
    """
    mode = config.get("mode")
    index_var = str(config.get("index_var") or "index")
    if mode == "count":
        try:
            n = int(config.get("count") or 0)
        except (TypeError, ValueError):
            n = 0
        n = max(0, min(n, MAX_LOOP_ITERATIONS))
        return [{index_var: str(i)} for i in range(n)]
    if mode == "list":
        item_var = str(config.get("item_var") or "item")
        raw = variables.get(str(config.get("list_var") or ""), "")
        try:
            items = json.loads(raw) if raw else []
        except (ValueError, TypeError):
            items = []
        if not isinstance(items, list):
            items = []
        result: List[Dict[str, str]] = []
        for i, it in enumerate(items[:MAX_LOOP_ITERATIONS]):
            val = it if isinstance(it, str) else json.dumps(it, ensure_ascii=False)
            result.append({item_var: val, index_var: str(i)})
        return result
    return []


def evaluate_condition(condition: Dict[str, Any], variables: Dict[str, str]) -> Tuple[bool, str]:
    """求值场景条件 {left, operator, right}：left/right 先 {{var}} 插值再按操作符比较。

    exists：left 插值后为非空且不含未解析 {{...}} 占位符时视为存在（即变量确有值）。
    其余操作符复用 _apply_operator（left 作 actual、right 作 expected）。
    """
    raw_left = str(condition.get("left") or "")
    left = apply_vars(raw_left, variables)
    operator = str(condition.get("operator") or "eq")
    if operator == "exists":
        unresolved = bool(VARIABLE_PATTERN.search(left))
        exists = bool(left) and not unresolved
        return exists, f"{raw_left} {'存在' if exists else '不存在'}"
    right = apply_vars(str(condition.get("right") or ""), variables)
    return _apply_operator(left, right, operator)
