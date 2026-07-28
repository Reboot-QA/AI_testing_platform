"""离线导出 FastAPI OpenAPI spec 到 backend/openapi.json。

前端 `pnpm gen:api-types` 据此生成 src/api/schema.d.ts（零手写类型）。
纯反射，不连数据库；CI/本地均可直接跑：`python -m scripts.export_openapi`。
"""

import json
from pathlib import Path

from app.main import app

OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"


def main() -> None:
    spec = app.openapi()
    OUTPUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    paths = len(spec.get("paths", {}))
    schemas = len(spec.get("components", {}).get("schemas", {}))
    print(f"exported {OUTPUT} · paths={paths} · schemas={schemas}")


if __name__ == "__main__":
    main()
