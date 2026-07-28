"""Apifox 式「自动生成的默认请求头」定义（单一事实来源，前端展示 + 引擎注入共用）。

两类：
- 固定值（computed=False）：用户未显式配置该头时注入发送，用户配了以用户为准（override）。
- 计算类（computed=True）：仅供前端展示「发送时自动生成」，实际由 httpx/引擎按请求内容生成
  （Host 从 URL、Content-Length/Content-Type 从 body、Cookie 从 cookie 配置），本模块不注入静态值。

Accept-Encoding 刻意只用 gzip, deflate（不含 br）：保证 httpx 无需额外解码依赖即可解压响应。
"""

from typing import Dict, List, TypedDict

_COMPUTED_PLACEHOLDER = "<在发送请求时计算>"


class DefaultHeader(TypedDict):
    name: str
    value: str
    computed: bool
    description: str


DEFAULT_HEADERS: List[DefaultHeader] = [
    # —— 固定值：未配置则注入发送 ——
    {"name": "User-Agent", "value": "DB-testlab/1.0.0", "computed": False, "description": "客户端标识"},
    {"name": "Accept", "value": "*/*", "computed": False, "description": "可接受的响应内容类型"},
    {
        "name": "Accept-Encoding",
        "value": "gzip, deflate",
        "computed": False,
        "description": "可接受的响应压缩方式",
    },
    {"name": "Connection", "value": "keep-alive", "computed": False, "description": "复用底层连接"},
    # —— 计算类：发送时按请求内容自动生成 ——
    {"name": "Host", "value": _COMPUTED_PLACEHOLDER, "computed": True, "description": "由请求 URL 自动生成"},
    {
        "name": "Content-Type",
        "value": _COMPUTED_PLACEHOLDER,
        "computed": True,
        "description": "由请求体类型自动生成（有 body 时）",
    },
    {
        "name": "Content-Length",
        "value": _COMPUTED_PLACEHOLDER,
        "computed": True,
        "description": "由请求体长度自动生成",
    },
    {
        "name": "Cookie",
        "value": _COMPUTED_PLACEHOLDER,
        "computed": True,
        "description": "由 Cookie 配置自动生成",
    },
]

# 供引擎注入的固定默认（name -> value）
FIXED_DEFAULT_HEADERS: Dict[str, str] = {
    h["name"]: h["value"] for h in DEFAULT_HEADERS if not h["computed"]
}


def apply_default_headers(headers: Dict[str, str]) -> None:
    """就地注入固定默认头：仅当用户未配置同名头（大小写不敏感）时添加。"""
    existing = {k.lower() for k in headers}
    for name, value in FIXED_DEFAULT_HEADERS.items():
        if name.lower() not in existing:
            headers[name] = value
