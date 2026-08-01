"""从仓库源码生成 AI 助手知识库 JSON。

用法（在 backend 目录）：
    python -m scripts.build_assistant_knowledge
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.assistant_knowledge import (
    KNOWLEDGE_JSON,
    build_knowledge_document,
    reload_knowledge_cache,
)


def main() -> None:
    payload = build_knowledge_document()
    KNOWLEDGE_JSON.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    reload_knowledge_cache()

    guides = len(payload.get("guides") or [])
    actions = len(payload.get("ui_actions") or [])
    sections = len(payload.get("sections") or {})
    print(f"exported {KNOWLEDGE_JSON} · guides={guides} · ui_actions={actions} · sections={sections}")


if __name__ == "__main__":
    main()
