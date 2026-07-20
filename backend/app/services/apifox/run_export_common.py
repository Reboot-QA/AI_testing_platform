"""Apifox 运行报告导出 · 公共格式化。迁移自老 api_run_export_service，G2b 删老拷贝。"""

import json
from datetime import datetime
from typing import Any, Iterable, List, Optional

from app.routers.apifox.run_schemas import RunOut

STATUS_LABELS = {
    "passed": "通过",
    "failed": "失败",
    "running": "执行中",
    "skipped": "跳过",
}


def _format_dt(value: Optional[datetime]) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_report_time(value: Optional[datetime]) -> str:
    if not value:
        return ""
    return value.strftime("%Y%m%d%H%M%S")


def _format_duration(ms: Optional[float]) -> str:
    if ms is None:
        return ""
    if ms < 1000:
        return f"{int(round(ms))}ms"
    return f"{ms / 1000:.2f}s"


def _pretty_json_text(text: Any) -> str:
    # apifox RunStepOut 的 headers 是 dict、body 是 JSON 文本，统一美化
    if isinstance(text, (dict, list)):
        return json.dumps(text, ensure_ascii=False, indent=2) if text else "-"
    raw = str(text or "").strip()
    if not raw:
        return "-"
    try:
        return json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return raw


def _format_assertions(results: Iterable[Any]) -> str:
    lines = []
    for item in results:
        if hasattr(item, "model_dump"):
            data = item.model_dump()
        elif isinstance(item, dict):
            data = item
        else:
            continue
        status = "通过" if data.get("passed") else "失败"
        message = data.get("message") or data.get("type") or ""
        expected = data.get("expected")
        actual = data.get("actual")
        lines.append(f"[{status}] {message} | 期望: {expected} | 实际: {actual}")
    return "\n".join(lines) if lines else "-"


def _report_summary_rows(report: RunOut) -> List[List[str]]:
    return [
        ["报告时间", _format_report_time(report.started_at)],
        ["测试套件", report.target_name or "-"],
        ["执行结果", STATUS_LABELS.get(report.status, report.status)],
        ["通过率", f"{report.pass_rate}%"],
        ["通过 / 失败 / 总数", f"{report.passed_count} / {report.failed_count} / {report.total_count}"],
        ["总耗时", _format_duration(report.duration_ms)],
        ["触发方式", report.triggered_by or "-"],
        ["开始时间", _format_dt(report.started_at)],
        ["结束时间", _format_dt(report.finished_at)],
    ]


def _assertion_table_rows(step) -> List[List[str]]:
    rows = []
    for item in step.assertion_results or []:
        if hasattr(item, "model_dump"):
            data = item.model_dump()
        elif isinstance(item, dict):
            data = item
        else:
            continue
        rows.append(
            [
                str(data.get("type") or ""),
                str(data.get("message") or ""),
                str(data.get("expected") if data.get("expected") is not None else "-"),
                str(data.get("actual") if data.get("actual") is not None else "-"),
                "通过" if data.get("passed") else "失败",
            ]
        )
    return rows

