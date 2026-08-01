"""AI 助手知识库：从导航树、OpenAPI、前端问答与 UI 锚点组装，并按问题检索相关片段。"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.constants.assistant_workspace import (
    ANSWER_RULES,
    DOMAIN_LABELS,
    FEATURE_NOTES,
    HUB_HOME_NAV,
    SECTION_LABELS,
    WORKSPACE_DOMAINS,
)
from app.constants.menus import MENU_DEFINITIONS

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
KNOWLEDGE_JSON = BACKEND_ROOT / "app" / "data" / "assistant_knowledge.json"
OPENAPI_JSON = BACKEND_ROOT / "openapi.json"
ASSISTANT_GUIDES_TS = REPO_ROOT / "frontend" / "src" / "constants" / "assistantGuides.ts"
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

# 助手需要感知的 OpenAPI 标签（用户向能力，不含纯内部运维）
USER_FACING_API_TAGS = {
    "认证",
    "项目",
    "需求",
    "用例",
    "AI生成",
    "AI助手",
    "测试执行",
    "接口自动化v2",
    "接口自动化v2·执行",
    "接口自动化v2·测试报告",
    "接口自动化v2·定时任务",
    "接口自动化v2·测试场景",
    "接口自动化v2·测试套件",
    "接口自动化v2·接口",
    "接口自动化v2·接口用例",
    "接口自动化v2·数据模型",
    "接口自动化v2·回收站",
    "接口自动化v2·工作台",
    "接口自动化v2·AI生成任务",
    "系统设置",
    "用户管理",
    "部门",
}

_ASSISTANT_GUIDE_BLOCK = re.compile(
    r"\{\s*text:\s*'(?P<text>[^']+)',\s*permissions:\s*\[(?P<perms>[^\]]*)\],\s*answer:\s*`(?P<answer>[\s\S]*?)`\s*,?\s*\}",
    re.MULTILINE,
)
_DATA_ASSISTANT = re.compile(r'data-assistant="([^"]+)"')


def _format_workspace_tree() -> str:
    lines = [
        "## 信息架构（与 Hub / 项目工作区 UI 一致，勿使用已废弃旧菜单名）",
        "- **Hub 首页** `/hub`：左侧 **首页 / 项目 / 动态**；有权限时可见 **系统**。",
        "- **项目工作区** `/hub/workspace/{项目ID}`：左侧全局栏 **需求 / 功能 / 自动化 / AI任务 / 设置**。",
        "- URL 使用具名子路径，例如 `/hub/workspace/:projectId/requirements/points`。",
        "",
        "### Hub 首页导航",
    ]
    for item in HUB_HOME_NAV:
        lines.append(f"- **{item['label']}**：{item['path']}")

    for domain_key, groups in WORKSPACE_DOMAINS.items():
        domain_label = DOMAIN_LABELS.get(domain_key, domain_key)
        lines.append("")
        lines.append(f"### {domain_label}域")
        for group in groups:
            prefix = f"- **{group['title']}** → " if group.get("title") else "- "
            leaves = group.get("items") or []
            leaf_text = "、".join(f"**{leaf['label']}**" for leaf in leaves)
            lines.append(f"{prefix}{leaf_text}")
    return "\n".join(lines)


def _format_feature_notes() -> str:
    lines = ["## 功能要点"]
    lines.extend(f"- {note}" for note in FEATURE_NOTES)
    return "\n".join(lines)


def _format_system_menus() -> str:
    lines = ["## 系统管理菜单（Hub → 系统）"]
    for item in MENU_DEFINITIONS:
        if item.get("group") not in {"system", "logs"}:
            continue
        parent = item.get("parent_label")
        label = item["label"]
        if parent:
            lines.append(f"- **{parent} → {label}**（`{item['path']}`）")
        else:
            lines.append(f"- **{label}**（`{item['path']}`）")
    return "\n".join(lines)


def _summarize_openapi() -> str:
    if not OPENAPI_JSON.is_file():
        return ""
    try:
        spec = json.loads(OPENAPI_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    tag_map: Dict[str, List[str]] = {}
    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, detail in methods.items():
            if method.startswith("x-") or not isinstance(detail, dict):
                continue
            tags = detail.get("tags") or ["未分类"]
            tag = tags[0]
            if tag not in USER_FACING_API_TAGS:
                continue
            summary = (detail.get("summary") or "").strip()
            entry = f"{method.upper()} {path}"
            if summary:
                entry += f" — {summary}"
            tag_map.setdefault(tag, [])
            if entry not in tag_map[tag]:
                tag_map[tag].append(entry)

    if not tag_map:
        return ""

    lines = ["## 后端 API 能力摘要（供理解平台能力边界，勿向用户背诵路径）"]
    for tag in sorted(tag_map.keys()):
        lines.append(f"### {tag}")
        for entry in tag_map[tag][:8]:
            lines.append(f"- {entry}")
        if len(tag_map[tag]) > 8:
            lines.append(f"- …共 {len(tag_map[tag])} 个接口")
    return "\n".join(lines)


def parse_assistant_guides_from_ts(source: Optional[str] = None) -> List[Dict[str, Any]]:
    text = source
    if text is None:
        if not ASSISTANT_GUIDES_TS.is_file():
            return []
        text = ASSISTANT_GUIDES_TS.read_text(encoding="utf-8")

    guides: List[Dict[str, Any]] = []
    for match in _ASSISTANT_GUIDE_BLOCK.finditer(text):
        perms_raw = match.group("perms")
        permissions = [p.strip().strip("'\"") for p in perms_raw.split(",") if p.strip()]
        guides.append(
            {
                "text": match.group("text"),
                "permissions": permissions,
                "answer": match.group("answer").strip(),
            }
        )
    return guides


def scan_ui_assistant_actions() -> List[Dict[str, str]]:
    if not FRONTEND_SRC.is_dir():
        return []
    seen: Dict[str, str] = {}
    for vue_file in FRONTEND_SRC.rglob("*.vue"):
        try:
            content = vue_file.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = vue_file.relative_to(FRONTEND_SRC).as_posix()
        for key in _DATA_ASSISTANT.findall(content):
            seen.setdefault(key, rel)
    return [{"key": key, "file": path} for key, path in sorted(seen.items())]


def _format_guides(guides: List[Dict[str, Any]]) -> str:
    if not guides:
        return ""
    lines = ["## 常见问答（与前端快捷问题一致）"]
    for guide in guides:
        lines.append(f"### Q: {guide['text']}")
        lines.append(guide["answer"])
        lines.append("")
    return "\n".join(lines).strip()


def _format_ui_actions(actions: List[Dict[str, str]]) -> str:
    if not actions:
        return ""
    lines = ["## 页面 UI 锚点（data-assistant，供理解关键按钮位置）"]
    for item in actions:
        lines.append(f"- `{item['key']}`（{item['file']}）")
    return "\n".join(lines)


def build_knowledge_document() -> Dict[str, Any]:
    guides = parse_assistant_guides_from_ts()
    ui_actions = scan_ui_assistant_actions()
    sections = {
        "workspace": _format_workspace_tree(),
        "features": _format_feature_notes(),
        "system_menus": _format_system_menus(),
        "guides": _format_guides(guides),
        "api_summary": _summarize_openapi(),
        "ui_actions": _format_ui_actions(ui_actions),
        "answer_rules": "\n".join(f"- {rule}" for rule in ANSWER_RULES),
    }
    return {
        "version": 1,
        "guides": guides,
        "ui_actions": ui_actions,
        "sections": sections,
    }


def build_knowledge_chunks(data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    payload = data or build_knowledge_document()
    sections = payload.get("sections") or {}
    chunks: List[Dict[str, Any]] = []

    def add_chunk(chunk_id: str, keywords: List[str], content: str) -> None:
        text = (content or "").strip()
        if not text:
            return
        chunks.append({"id": chunk_id, "keywords": keywords, "content": text})

    add_chunk(
        "workspace",
        ["hub", "首页", "项目", "工作区", "需求", "功能", "自动化", "动态", "菜单", "导航", "入口"],
        sections.get("workspace", ""),
    )
    add_chunk(
        "features",
        ["需求", "用例", "导入", "覆盖", "追加", "评审", "执行", "报告", "环境", "生成"],
        sections.get("features", ""),
    )
    add_chunk(
        "system",
        ["系统", "权限", "用户", "部门", "全局设置", "大模型", "管理员", "日志"],
        sections.get("system_menus", ""),
    )
    add_chunk(
        "api",
        ["接口", "api", "自动化", "场景", "套件", "定时", "报告"],
        sections.get("api_summary", ""),
    )
    add_chunk(
        "ui",
        ["按钮", "添加", "新建", "创建", "表单", "提交"],
        sections.get("ui_actions", ""),
    )

    for index, guide in enumerate(payload.get("guides") or []):
        text = guide.get("text") or ""
        answer = guide.get("answer") or ""
        tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text + answer)
        keywords = list(dict.fromkeys(tokens))[:24]
        add_chunk(f"guide_{index}", keywords, f"### Q: {text}\n{answer}")

    add_chunk("rules", ["回答", "规范"], "## 回答要求\n" + sections.get("answer_rules", ""))
    return chunks


def _tokenize_for_match(text: str) -> set[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_]{2,}", (text or "").lower())
    stop = {"如何", "怎么", "什么", "可以", "是否", "请问", "帮助"}
    return {t for t in tokens if t not in stop}


def rank_chunks_for_question(question: str, chunks: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    if not question.strip():
        return chunks[:limit]

    q_tokens = _tokenize_for_match(question)
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for chunk in chunks:
        score = 0
        content_lower = chunk["content"].lower()
        for token in q_tokens:
            if token in content_lower:
                score += 2
            for kw in chunk.get("keywords") or []:
                if token in kw.lower() or kw.lower() in token:
                    score += 3
        if chunk["id"] == "rules":
            score += 1
        if chunk["id"] == "workspace" and any(k in question for k in ("在哪", "入口", "路径", "菜单")):
            score += 2
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    if not scored:
        return chunks[:limit]
    return [item[1] for item in scored[:limit]]


@lru_cache(maxsize=1)
def load_knowledge_payload() -> Dict[str, Any]:
    if KNOWLEDGE_JSON.is_file():
        try:
            return json.loads(KNOWLEDGE_JSON.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return build_knowledge_document()


def reload_knowledge_cache() -> None:
    load_knowledge_payload.cache_clear()
    get_knowledge_chunks.cache_clear()


@lru_cache(maxsize=1)
def get_knowledge_chunks() -> Tuple[Dict[str, Any], ...]:
    payload = load_knowledge_payload()
    return tuple(build_knowledge_chunks(payload))


def find_guide_answer(question: str, guides: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    items = guides if guides is not None else (load_knowledge_payload().get("guides") or [])
    text = question.strip()
    for guide in items:
        if guide.get("text") == text:
            return guide.get("answer")
    for guide in items:
        guide_text = guide.get("text") or ""
        if guide_text and guide_text in text:
            return guide.get("answer")
    if "报告" in text and re.search(r"查看|打开|帮我|看|进入", text):
        return (
            "**查看测试报告**\n\n"
            "1. 进入 **项目工作区** → 左侧 **自动化**。\n"
            "2. 在左侧树打开 **测试报告**。\n"
            "3. 点击列表中的记录或 **查看**，在抽屉中查看步骤明细、通过率，并可导出。"
        )
    return None


def build_assistant_system_prompt(user_question: Optional[str] = None) -> str:
    chunks = list(get_knowledge_chunks())
    selected = rank_chunks_for_question(user_question or "", chunks, limit=6)

    body = "\n\n".join(chunk["content"] for chunk in selected)
    return (
        "你是「AI 质量平台」的智能助手，熟悉本平台的项目 / 需求 / 用例 / 接口自动化等操作。\n"
        "用户也可能提问其它领域问题，请如实、简洁作答。当问题与本平台相关时，优先结合下文知识片段给出可执行步骤。\n\n"
        f"{body}"
    )


def section_labels_for_page_context() -> Dict[str, str]:
    return dict(SECTION_LABELS)


def domain_labels_for_page_context() -> Dict[str, str]:
    return dict(DOMAIN_LABELS)
