"""AI 生成接口测试用例 · service。

给定一个接口（方法/路径/参数/body/响应模型），让 LLM 按用户勾选的类别与数量
生成一组测试用例，构造成 CaseCreate 预览列表（不落库）返回给前端勾选后创建。

复用 ai_service 的 LLM 请求/错误管道；本模块只负责「接口用例」专属的 prompt 与解析。
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint
from app.repositories.apifox import case_repo, schema_repo
from app.routers.apifox.case_schemas import AiGenCategory, CaseCreate
from app.routers.apifox.schemas import AssertionRow, KvRow, RequestSpec
from app.services.ai_service import call_llm_chat

logger = logging.getLogger(__name__)

_CATEGORY_LABELS = {
    "positive": "正向（合法输入，预期成功）",
    "negative": "逆向（非法/缺失/错误类型输入，预期返回错误）",
    "boundary": "边界值（空值/零/负数/最大长度/超长/Unicode/临界值）",
    "security": "安全性（SQL 注入、越权、异常字符、超大 payload）",
}
_VALID_CATEGORIES = set(_CATEGORY_LABELS)
_ASSERTION_TYPES = {"status_code", "json_path", "header", "contains", "response_time"}
_ASSERTION_OPERATORS = {
    "eq", "neq", "contains", "not_contains", "gt", "gte", "lt", "lte", "regex", "exists",
}

# AI 用例生成永远走后台任务，用户不阻塞，给 LLM 更长时间（默认 120s 对复杂接口/多条易超时）
_LLM_READ_TIMEOUT = 240.0

_SYSTEM_PROMPT = (
    "你是资深接口测试设计专家。根据给定的 HTTP 接口定义，为指定的测试类别设计测试用例。"
    "每条用例需给出请求参数取值与断言。只输出 JSON，不要任何解释文字。"
)


# ---------- 上下文（把接口结构描述给 LLM） ----------
def _kv_lines(title: str, rows: List[KvRow]) -> str:
    active = [r for r in rows if (r.key or "").strip()]
    if not active:
        return ""
    lines = [
        f"  - {r.key}（类型 {r.type or 'string'}{'，必填' if r.enabled else ''}）"
        f"{'：' + r.desc if r.desc else ''}"
        for r in active
    ]
    return f"{title}:\n" + "\n".join(lines) + "\n"


def build_endpoint_context(
    endpoint: ApifoxEndpoint, spec: RequestSpec, response_json_schema: Optional[str]
) -> str:
    parts = [f"接口：{endpoint.method} {endpoint.path}", f"名称：{endpoint.name}"]
    if endpoint.description:
        parts.append(f"说明：{endpoint.description}")
    ctx = "\n".join(parts) + "\n"
    ctx += _kv_lines("Query 参数", spec.query)
    ctx += _kv_lines("Path 参数", spec.path_params)
    ctx += _kv_lines("Header", spec.headers)
    if spec.body.type == "json" and spec.body.raw.strip():
        ctx += f"请求体(JSON 示例):\n{spec.body.raw.strip()[:1500]}\n"
    elif spec.body.form:
        ctx += _kv_lines("表单字段", spec.body.form)
    if response_json_schema and response_json_schema.strip():
        ctx += f"响应模型(JSON Schema，用于设计断言):\n{response_json_schema.strip()[:1500]}\n"
    return ctx


_AUTO_QUANTITY = "数量由你按接口参数个数与错误路径复杂度自行决定（建议 2-6 条，简单接口可更少）"


def _category_spec(
    categories: List[AiGenCategory], existing_by_cat: Optional[dict] = None
) -> str:
    """按类别拼生成要求；对「该类别已有用例」的类别追加针对性提示（避免同方向重复）。"""
    existing_by_cat = existing_by_cat or {}
    lines: List[str] = []
    for c in categories:
        if c.category not in _VALID_CATEGORIES:
            continue
        qty = f"最多 {c.count} 条" if c.count else _AUTO_QUANTITY
        line = f"  - {c.category}（{_CATEGORY_LABELS[c.category]}）：{qty}"
        covered = existing_by_cat.get(c.category)
        if covered:
            names = "、".join(f"「{n}」" for n in covered[:20])
            line += (
                f"\n    ⚠ 该类别已有 {len(covered)} 条用例：{names}；"
                "只补充与这些**测试方向不同**的新用例，已覆盖的方向不要重复；"
                "若该类别已无新方向可覆盖，则不生成该类别。"
            )
        lines.append(line)
    return "\n".join(lines)


def _group_by_category(existing: List[Tuple[str, str]]) -> dict:
    by_cat: dict = {}
    for name, cat in existing:
        by_cat.setdefault(cat, []).append(name)
    return by_cat


def build_user_prompt(
    context: str,
    categories: List[AiGenCategory],
    existing_cases: Optional[List[Tuple[str, str]]] = None,
) -> str:
    existing_by_cat = _group_by_category(existing_cases or [])
    return f"""{context}
请按下列类别与数量设计测试用例（标注「已有用例」的类别请只补充未覆盖的新方向，不要重复）：
{_category_spec(categories, existing_by_cat)}

每条用例给出：
- name：用例名称（简体中文，含类别与场景，如「缺少必填参数 page 返回 400」）
- category：类别（positive/negative/boundary/security 之一）
- query/path_params/headers：对象，key 为参数名、value 为该用例使用的取值（只写需要覆盖的参数）
- body：请求体对象（若接口有 body）
- ⚠ 若本用例要故意「不传某参数」（如必选参数缺失、缺少用户名等负向场景），必须把该参数的
  value 显式设为 null 表示不传，**不要省略、也不要给空字符串**——省略会沿用接口默认值，达不到「缺失」的测试意图。
- assertions：断言数组，每项 {{"type","path","operator","expected"}}；
  type 取 status_code/json_path/header/contains/response_time；
  json_path 用 $.xxx 表达式；正向至少断言状态码 200，逆向断言对应错误码（如 400/401/403/422）。

严格按 JSON 输出：{{"cases":[...]}}，不要输出多余文字。"""


# ---------- 解析 LLM 响应 → CaseCreate ----------
def _salvage_case_objects(text: str) -> List[dict]:
    """LLM JSON 畸形/被截断时，逐个救回完整的用例对象。

    从 cases 数组内起扫，括号配平（string-aware，忽略字符串内的花括号）提取每个平衡的
    顶层对象；缺逗号→各自仍平衡照样提取，尾部被截断→丢弃未闭合的最后一个。
    """
    key = text.find('"cases"')
    bracket = text.find("[", key) if key >= 0 else text.find("[")
    scan = text[bracket + 1:] if bracket >= 0 else text

    objects: List[dict] = []
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(scan):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    obj = json.loads(scan[start:i + 1])
                except json.JSONDecodeError:
                    obj = None
                if isinstance(obj, dict):
                    objects.append(obj)
                start = -1
    return objects


def _parse_cases_payload(content: str) -> List[dict]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    text = text.strip()

    data: Any = None
    try:
        data = json.loads(text)  # 优先整体解析：兼容顶层对象与顶层数组
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")  # 再试：截取首尾大括号
        if 0 <= start < end:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                data = None

    if data is not None:
        cases = data.get("cases") if isinstance(data, dict) else data
        if isinstance(cases, list):
            return [c for c in cases if isinstance(c, dict)]  # 可能为空，交上层判断

    # 兜底：整体解析失败（LLM 输出畸形/截断）时逐个救回完整用例，避免整批丢弃
    salvaged = _salvage_case_objects(text)
    if salvaged:
        return salvaged
    raise ValueError("LLM 返回不含可解析的用例 JSON")


def _apply_kv(rows: List[KvRow], values: Any) -> None:
    if not isinstance(values, dict):
        return
    by_key = {r.key: r for r in rows}
    for key, val in values.items():
        # null 表示「本用例不传该参数」（必选参数缺失/缺少某字段的负向用例）：禁用该行、不新增
        if val is None:
            if key in by_key:
                by_key[key].enabled = False
            continue
        text = str(val)
        if key in by_key:
            by_key[key].value = text
            by_key[key].enabled = True
        else:
            rows.append(KvRow(key=str(key), value=text, enabled=True))


def _build_assertion(item: Any) -> Optional[AssertionRow]:
    if not isinstance(item, dict):
        return None
    a_type = item.get("type", "status_code")
    if a_type not in _ASSERTION_TYPES:
        return None
    operator = item.get("operator", "eq")
    if operator not in _ASSERTION_OPERATORS:
        operator = "eq"
    expected = item.get("expected")
    return AssertionRow(
        type=a_type,
        path=item.get("path"),
        operator=operator,
        expected=None if expected is None else str(expected),
    )


def _build_case(base_spec: RequestSpec, item: Any) -> Optional[CaseCreate]:
    if not isinstance(item, dict):
        return None
    name = (item.get("name") or "").strip()
    if not name:
        return None
    category = item.get("category")
    if category not in _VALID_CATEGORIES:
        category = "other"

    spec = base_spec.model_copy(deep=True)
    _apply_kv(spec.query, item.get("query"))
    _apply_kv(spec.path_params, item.get("path_params"))
    _apply_kv(spec.headers, item.get("headers"))
    body = item.get("body")
    if body is not None:
        if spec.body.type in ("none", ""):
            spec.body.type = "json"
        if spec.body.type == "json":
            if isinstance(body, dict):
                # 剔除值为 null 的键：表达「本用例不传该字段」（缺失字段负向用例），等价于不发送
                cleaned = {k: v for k, v in body.items() if v is not None}
                spec.body.raw = json.dumps(cleaned, ensure_ascii=False)
            else:
                spec.body.raw = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        elif spec.body.type in ("form-data", "urlencoded") and isinstance(body, dict):
            _apply_kv(spec.body.form, body)

    assertions = [a for a in (_build_assertion(x) for x in item.get("assertions") or []) if a]
    return CaseCreate(name=name[:200], category=category, request_spec=spec, assertions=assertions)


def _build_cases(base_spec: RequestSpec, raw_cases: List[dict]) -> List[CaseCreate]:
    out: List[CaseCreate] = []
    for item in raw_cases:
        try:
            case = _build_case(base_spec, item)
        except (ValueError, TypeError) as exc:
            logger.warning("AI 用例构造失败，跳过一条: %s", exc)
            continue
        if case:
            out.append(case)
    return out


# ---------- Mock ----------
_MOCK_AUTO_COUNT = 3  # 自动模式下 mock 每类的样例条数


def _mock_cases(base_spec: RequestSpec, categories: List[AiGenCategory]) -> List[CaseCreate]:
    out: List[CaseCreate] = []
    for cat in categories:
        if cat.category not in _VALID_CATEGORIES:
            continue
        label = _CATEGORY_LABELS[cat.category].split("（")[0]
        expected_status = "200" if cat.category == "positive" else "400"
        for i in range(cat.count or _MOCK_AUTO_COUNT):
            item = {
                "name": f"[{label}] 示例用例 {i + 1}",
                "category": cat.category,
                "assertions": [{"type": "status_code", "operator": "eq", "expected": expected_status}],
            }
            case = _build_case(base_spec, item)
            if case:
                out.append(case)
    return out


# ---------- 入口 ----------
@dataclass
class GenPlan:
    """一次生成的输入：DB 读取阶段产出，供纯异步 LLM 阶段并发消费（不再持有 db）。"""

    mode: str  # 'mock' | 'llm'
    base_spec: RequestSpec
    categories: List[AiGenCategory]
    user_prompt: Optional[str] = None  # 全类别单次 prompt（兼容 run_gen_plan）
    context: str = ""  # 接口上下文，按类别分批生成时复用
    existing_cases: Optional[List[Tuple[str, str]]] = None


def build_gen_plan(
    db: Session, endpoint: ApifoxEndpoint, categories: List[AiGenCategory], llm_config: dict
) -> GenPlan:
    """同步阶段：读接口/响应模型/已有用例，拼好提示词。并发扇出前逐接口调用。"""
    base_spec = RequestSpec.model_validate_json(endpoint.request_spec or "{}")
    if llm_config["mock_mode"]:
        return GenPlan(mode="mock", base_spec=base_spec, categories=categories)
    if not llm_config["api_key"]:
        raise ValueError("当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    response_schema = None
    if endpoint.response_schema_id:
        schema = schema_repo.get_schema(db, endpoint.response_schema_id)
        response_schema = schema.json_schema if schema else None
    context = build_endpoint_context(endpoint, base_spec, response_schema)
    existing_cases = [(c.name, c.category) for c in case_repo.list_cases(db, endpoint.id)]
    return GenPlan(
        mode="llm",
        base_spec=base_spec,
        categories=categories,
        context=context,
        existing_cases=existing_cases,
        user_prompt=build_user_prompt(context, categories, existing_cases),
    )


def _mock_cases_iter(
    base_spec: RequestSpec, categories: List[AiGenCategory]
) -> List[CaseCreate]:
    """Mock 逐条产出（与 _mock_cases 相同集合，供增量回调）。"""
    return _mock_cases(base_spec, categories)


async def run_gen_plan_incremental(
    plan: GenPlan,
    llm_config: dict,
    on_batch: Callable[[List[CaseCreate]], None],
) -> Tuple[List[CaseCreate], str]:
    """按类别分批生成；每批解析成功后 on_batch（worker 写库 → 前端轮询可见）。"""
    accumulated: List[CaseCreate] = []

    def _emit(batch: List[CaseCreate]) -> None:
        if not batch:
            return
        accumulated.extend(batch)
        on_batch(batch)

    if plan.mode == "mock":
        for case in _mock_cases_iter(plan.base_spec, plan.categories):
            _emit([case])
        if not accumulated:
            raise ValueError("Mock 未生成任何用例")
        return accumulated, "mock"

    context = plan.context
    if not context.strip():
        raise ValueError("生成计划缺少接口上下文")
    existing = plan.existing_cases or []

    for cat in plan.categories:
        if cat.category not in _VALID_CATEGORIES:
            continue
        user_prompt = build_user_prompt(context, [cat], existing)
        content = await call_llm_chat(
            api_base=llm_config["api_base"],
            api_key=llm_config["api_key"],
            model=llm_config["model"],
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            read_timeout=_LLM_READ_TIMEOUT,
        )
        try:
            raw_cases = _parse_cases_payload(content)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("类别 %s 生成解析失败，跳过: %s", cat.category, exc)
            continue
        batch = _build_cases(plan.base_spec, raw_cases)
        _emit(batch)

    if not accumulated:
        raise ValueError("LLM 未生成任何有效用例，请调整类别或重试")
    return accumulated, "llm"


async def run_gen_plan(plan: GenPlan, llm_config: dict) -> Tuple[List[CaseCreate], str]:
    """纯异步阶段：不碰 DB；批量模式（测试/直接调用）。"""
    return await run_gen_plan_incremental(plan, llm_config, lambda _b: None)


async def generate_cases(
    db: Session,
    endpoint: ApifoxEndpoint,
    categories: List[AiGenCategory],
    llm_config: dict,
) -> Tuple[List[CaseCreate], str]:
    """单接口生成（构建计划 + 执行），供直接调用与测试；批量走 build_gen_plan/run_gen_plan。"""
    return await run_gen_plan(build_gen_plan(db, endpoint, categories, llm_config), llm_config)
