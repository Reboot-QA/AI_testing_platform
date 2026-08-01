"""字段长度上限常量（单一事实来源，前端 src/constants/limits.ts 与之对齐）。

标题（name/title 等展示名）、接口路径与描述（description）的长度上限统一在此定义，
apifox 各写入 schema（Create/Update）引用，避免 100/500 魔数散落。
"""

from typing import Optional

# 标题/名称上限（apifox 主实体展示名 name/title）
TITLE_MAX_LEN = 100

# 接口路径上限（对齐 apifox_endpoints.path 的 String(500)）
PATH_MAX_LEN = 500

# 描述上限（apifox 各实体 description，DB 仍为 Text，仅入参校验）
DESC_MAX_LEN = 500

# 数据模型(Schema)名称上限：按测试要求收窄到 50（区别于通用标题 100）
MODEL_NAME_MAX_LEN = 50

# 需求点 / 功能用例标题上限（与 apifox 通用标题 100 区分）
REQ_CASE_TITLE_MAX_LEN = 60

# 手工测试单「版本/构建」上限
BUILD_NAME_MAX_LEN = 30


def normalize_req_case_title(title: str, *, default: str = "") -> str:
    """去首尾空白并截断至上限（AI / Mock / 导入等自动写入路径）。"""
    clean = (title or default).strip()
    return clean[:REQ_CASE_TITLE_MAX_LEN]


def normalize_requirement_point_ref(title: str) -> Optional[str]:
    """用例导入「需求点」列：可选，非空则截断至上限。"""
    clean = (title or "").strip()
    if not clean or clean in {"未关联需求", "-"}:
        return None
    return normalize_req_case_title(clean)


def validate_req_case_title(title: str, *, field_label: str = "标题") -> str:
    """人工录入 / 导入等路径：超长则抛 ValueError。"""
    clean = (title or "").strip()
    if not clean:
        raise ValueError(f"{field_label}不能为空")
    if len(clean) > REQ_CASE_TITLE_MAX_LEN:
        raise ValueError(f"{field_label}不能超过 {REQ_CASE_TITLE_MAX_LEN} 字")
    return clean


def validate_build_name(value: Optional[str], *, field_label: str = "版本/构建") -> Optional[str]:
    """手工测试单版本号：可选，非空则校验长度。"""
    if value is None:
        return None
    clean = value.strip()
    if not clean:
        return None
    if len(clean) > BUILD_NAME_MAX_LEN:
        raise ValueError(f"{field_label}不能超过 {BUILD_NAME_MAX_LEN} 个字符")
    return clean
