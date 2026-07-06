import json
from datetime import datetime
from io import BytesIO
from typing import Any, Iterable, List, Optional
from urllib.parse import quote

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from app.schemas import ApiTestRunDetailOut

STATUS_LABELS = {
    "passed": "通过",
    "failed": "失败",
    "running": "执行中",
    "skipped": "跳过",
}


def build_content_disposition(filename: str, fallback: str = "report.xlsx") -> str:
    encoded = quote(filename, safe="")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'


def _format_dt(value: Optional[datetime]) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(ms: float) -> str:
    if ms is None:
        return ""
    if ms < 1000:
        return f"{int(round(ms))}ms"
    return f"{ms / 1000:.2f}s"


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
    return "\n".join(lines)


def _autosize_row(ws, row_num: int, min_height: int = 18, max_height: int = 120) -> None:
    max_lines = 1
    for cell in ws[row_num]:
        if cell.value is None:
            continue
        text = str(cell.value)
        col_width = ws.column_dimensions[get_column_letter(cell.column)].width or 10
        chars_per_line = max(int(col_width * 1.2), 10)
        lines = 0
        for part in text.split("\n"):
            lines += max(1, (len(part) + chars_per_line - 1) // chars_per_line)
        max_lines = max(max_lines, lines)
    ws.row_dimensions[row_num].height = min(max(min_height, max_lines * 15), max_height)


def _configure_sheet(ws, column_widths: dict) -> None:
    header_font = Font(bold=True)
    for col_idx, header in enumerate(ws[1], start=1):
        header.font = header_font
        header.alignment = Alignment(horizontal="center", vertical="center")
    for column, width in column_widths.items():
        ws.column_dimensions[column].width = width
    ws.row_dimensions[1].height = 20


def _apply_multiline_cell(ws, row_num: int, column: int, value: Any) -> None:
    cell = ws.cell(row_num, column, value if value is not None else "")
    cell.alignment = Alignment(vertical="top", wrap_text=True)


def build_run_export_excel(reports: List[ApiTestRunDetailOut]) -> BytesIO:
    wb = Workbook()

    summary_ws = wb.active
    summary_ws.title = "报告摘要"
    summary_headers = [
        "报告 ID",
        "套件",
        "结果",
        "通过率",
        "通过数",
        "失败数",
        "总数",
        "耗时",
        "触发方式",
        "开始时间",
        "结束时间",
    ]
    summary_ws.append(summary_headers)
    _configure_sheet(
        summary_ws,
        {
            "A": 10,
            "B": 24,
            "C": 10,
            "D": 10,
            "E": 8,
            "F": 8,
            "G": 8,
            "H": 10,
            "I": 12,
            "J": 20,
            "K": 20,
        },
    )

    for report in reports:
        row_num = summary_ws.max_row + 1
        summary_ws.cell(row_num, 1, report.id)
        summary_ws.cell(row_num, 2, report.suite_name)
        summary_ws.cell(row_num, 3, STATUS_LABELS.get(report.status, report.status))
        summary_ws.cell(row_num, 4, f"{report.pass_rate}%")
        summary_ws.cell(row_num, 5, report.passed_count)
        summary_ws.cell(row_num, 6, report.failed_count)
        summary_ws.cell(row_num, 7, report.total_count)
        summary_ws.cell(row_num, 8, _format_duration(report.duration_ms))
        summary_ws.cell(row_num, 9, report.triggered_by or "")
        summary_ws.cell(row_num, 10, _format_dt(report.started_at))
        summary_ws.cell(row_num, 11, _format_dt(report.finished_at))

    detail_ws = wb.create_sheet("用例明细")
    detail_headers = [
        "报告 ID",
        "套件",
        "序号",
        "用例名称",
        "方法",
        "URL",
        "结果",
        "耗时",
        "响应状态",
        "错误信息",
        "断言结果",
        "请求头",
        "请求体",
        "响应头",
        "响应体",
    ]
    detail_ws.append(detail_headers)
    _configure_sheet(
        detail_ws,
        {
            "A": 10,
            "B": 20,
            "C": 8,
            "D": 22,
            "E": 10,
            "F": 36,
            "G": 10,
            "H": 10,
            "I": 10,
            "J": 24,
            "K": 28,
            "L": 24,
            "M": 24,
            "N": 24,
            "O": 32,
        },
    )

    for report in reports:
        for index, step in enumerate(report.step_results, start=1):
            row_num = detail_ws.max_row + 1
            detail_ws.cell(row_num, 1, report.id)
            detail_ws.cell(row_num, 2, report.suite_name)
            detail_ws.cell(row_num, 3, index)
            detail_ws.cell(row_num, 4, step.case_name)
            detail_ws.cell(row_num, 5, step.method)
            _apply_multiline_cell(detail_ws, row_num, 6, step.url)
            detail_ws.cell(row_num, 7, STATUS_LABELS.get(step.status, step.status))
            detail_ws.cell(row_num, 8, _format_duration(step.duration_ms))
            detail_ws.cell(row_num, 9, step.response_status if step.response_status is not None else "")
            _apply_multiline_cell(detail_ws, row_num, 10, step.error_message or "")
            _apply_multiline_cell(detail_ws, row_num, 11, _format_assertions(step.assertion_results))
            _apply_multiline_cell(detail_ws, row_num, 12, step.request_headers or "")
            _apply_multiline_cell(detail_ws, row_num, 13, step.request_body or "")
            _apply_multiline_cell(detail_ws, row_num, 14, step.response_headers or "")
            _apply_multiline_cell(detail_ws, row_num, 15, step.response_body or "")
            _autosize_row(detail_ws, row_num)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def build_run_export_json(reports: List[ApiTestRunDetailOut], *, single: bool = False) -> bytes:
    payload = reports[0].model_dump(mode="json") if single and len(reports) == 1 else [
        report.model_dump(mode="json") for report in reports
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def build_export_filename(reports: List[ApiTestRunDetailOut], ext: str) -> str:
    if len(reports) == 1:
        report = reports[0]
        suite = (report.suite_name or "report").replace("/", "_").replace("\\", "_")
        return f"测试报告_{report.id}_{suite}.{ext}"
    return f"测试报告_批量导出_{len(reports)}条.{ext}"
