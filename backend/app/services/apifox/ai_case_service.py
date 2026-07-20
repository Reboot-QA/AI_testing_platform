"""AI 生成接口测试用例 · service。

给定一个接口（方法/路径/参数/body/响应模型），让 LLM 按用户勾选的类别与数量
生成一组测试用例，构造成 CaseCreate 预览列表（不落库）返回给前端勾选后创建。

复用 ai_service 的 LLM 请求/错误管道；本模块只负责「接口用例」专属的 prompt 与解析。
"""

import json
import logging
from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint
from app.repositories.apifox import schema_repo
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


def _category_spec(categories: List[AiGenCategory]) -> str:
    lines = [
        f"  - {c.category}（{_CATEGORY_LABELS[c.category]}）："
        f"{f'最多 {c.count} 条' if c.count else _AUTO_QUANTITY}"
        for c in categories
        if c.category in _VALID_CATEGORIES
    ]
    return "\n".join(lines)


def build_user_prompt(context: str, categories: List[AiGenCategory]) -> str:
    return f"""{context}
请按下列类别与数量设计测试用例：
{_category_spec(categories)}

每条用例给出：
- name：用例名称（简体中文，含类别与场景，如「缺少必填参数 page 返回 400」）
- category：类别（positive/negative/boundary/security 之一）
- query/path_params/headers：对象，key 为参数名、value 为该用例使用的取值（只写需要覆盖的参数）
- body：请求体对象（若接口有 body）
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
        text = "" if val is None else str(val)
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
async def generate_cases(
    db: Session,
    endpoint: ApifoxEndpoint,
    categories: List[AiGenCategory],
    llm_config: dict,
) -> Tuple[List[CaseCreate], str]:
    base_spec = RequestSpec.model_validate_json(endpoint.request_spec or "{}")

    if llm_config["mock_mode"]:
        return _mock_cases(base_spec, categories), "mock"
    api_key = llm_config["api_key"]
    if not api_key:
        raise ValueError("当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    response_schema = None
    if endpoint.response_schema_id:
        schema = schema_repo.get_schema(db, endpoint.response_schema_id)
        response_schema = schema.json_schema if schema else None

    context = build_endpoint_context(endpoint, base_spec, response_schema)
    content = await call_llm_chat(
        api_base=llm_config["api_base"],
        api_key=api_key,
        model=llm_config["model"],
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=build_user_prompt(context, categories),
        read_timeout=_LLM_READ_TIMEOUT,
    )
    try:
        raw_cases = _parse_cases_payload(content)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"LLM 返回格式无法解析: {exc}") from exc
    cases = _build_cases(base_spec, raw_cases)
    if not cases:
        raise ValueError("LLM 未生成任何有效用例，请调整类别或重试")
    return cases, "llm"
