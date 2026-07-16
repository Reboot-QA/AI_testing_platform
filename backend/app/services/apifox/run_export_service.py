"""Apifox 运行报告导出 · 入口（Excel/Word/PDF/JSON 分发 + 文件名）。"""

import json
from typing import Any, List, Tuple
from urllib.parse import quote

from app.routers.apifox.run_schemas import RunOut
from app.services.apifox.run_export_common import STATUS_LABELS, _format_report_time  # noqa: F401
from app.services.apifox.run_export_excel import build_run_export_excel
from app.services.apifox.run_export_pdf import _ensure_reportlab, build_run_export_pdf
from app.services.apifox.run_export_word import build_run_export_word

EXPORT_MEDIA_TYPES = {
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "json": "application/json; charset=utf-8",
}


EXPORT_EXTENSIONS = {
    "excel": "xlsx",
    "word": "docx",
    "pdf": "pdf",
    "json": "json",
}


SUPPORTED_EXPORT_FORMATS = set(EXPORT_MEDIA_TYPES)


def build_content_disposition(filename: str, fallback: str = "report.xlsx") -> str:
    encoded = quote(filename, safe="")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'


def build_export_filename(reports: List[RunOut], ext: str) -> str:
    if len(reports) == 1:
        report = reports[0]
        suite = (report.target_name or "report").replace("/", "_").replace("\\", "_")
        time_token = _format_report_time(report.started_at)
        return f"测试报告_{time_token}_{suite}.{ext}"
    return f"测试报告_批量导出_{len(reports)}条.{ext}"


def build_run_export(
    reports: List[RunOut], export_format: str
) -> Tuple[Any, str, str]:
    normalized = (export_format or "excel").lower()
    if normalized not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError("不支持的导出格式")

    if normalized == "excel":
        return build_run_export_excel(reports), EXPORT_MEDIA_TYPES["excel"], EXPORT_EXTENSIONS["excel"]
    if normalized == "word":
        return build_run_export_word(reports), EXPORT_MEDIA_TYPES["word"], EXPORT_EXTENSIONS["word"]
    if normalized == "pdf":
        _ensure_reportlab()
        return build_run_export_pdf(reports), EXPORT_MEDIA_TYPES["pdf"], EXPORT_EXTENSIONS["pdf"]
    content = build_run_export_json(reports, single=len(reports) == 1)
    return content, EXPORT_MEDIA_TYPES["json"], EXPORT_EXTENSIONS["json"]


def build_run_export_json(reports: List[RunOut], *, single: bool = False) -> bytes:
    payload = reports[0].model_dump(mode="json") if single and len(reports) == 1 else [
        report.model_dump(mode="json") for report in reports
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

