"""Apifox 执行引擎 · 操作符比较底座。

_apply_operator 被断言评估（run_engine.evaluate_assertions）与场景条件
（flow_control.evaluate_condition）共用，为无外部依赖的纯比较逻辑。
CONDITION_OPERATORS 为场景条件步骤可用的操作符白名单（复用断言操作符语义）。
"""

import re
from typing import Any, Optional, Tuple

_NUMERIC_OPS = {"gt", "gte", "lt", "lte"}

# 场景条件步骤(if)可用操作符（复用断言操作符语义）
CONDITION_OPERATORS = {"eq", "neq", "contains", "not_contains", "gt", "gte", "lt", "lte", "regex", "exists"}


def _apply_operator(actual: Any, expected: Optional[str], operator: str) -> Tuple[bool, str]:
    """按操作符比较（actual 可为数字/布尔/None，expected 为字符串）。返回 (通过, 说明)。"""
    op = operator or "eq"
    a_str = "" if actual is None else str(actual)
    e_str = "" if expected is None else str(expected)
    if op == "exists":
        return actual is not None, f"值{'存在' if actual is not None else '不存在'}"
    if op in _NUMERIC_OPS:
        try:
            a_num, e_num = float(actual), float(e_str)
        except (TypeError, ValueError):
            return False, f"非数值无法比较：{a_str}"
        passed = {"gt": a_num > e_num, "gte": a_num >= e_num, "lt": a_num < e_num, "lte": a_num <= e_num}[op]
        sym = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[op]
        return passed, f"{a_num} {sym if passed else '!' + sym} {e_num}"
    if op == "regex":
        try:
            passed = re.search(e_str, a_str) is not None
        except re.error:
            return False, f"正则无效：{e_str}"
        return passed, f"{'匹配' if passed else '不匹配'}正则 {e_str}"
    if op == "contains":
        return e_str in a_str, f"{'包含' if e_str in a_str else '不包含'} \"{e_str}\""
    if op == "not_contains":
        return e_str not in a_str, f"{'不包含' if e_str not in a_str else '包含'} \"{e_str}\""
    if op == "neq":
        return a_str != e_str, f"{a_str} {'!=' if a_str != e_str else '=='} {e_str}"
    return a_str == e_str, f"{a_str} {'==' if a_str == e_str else '!='} {e_str}"  # eq（字符串宽松等价）
