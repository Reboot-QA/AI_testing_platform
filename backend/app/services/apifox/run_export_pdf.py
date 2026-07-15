"""Apifox 运行报告导出 · PDF。"""

import glob
import os
import platform
from io import BytesIO
from typing import Any, List
from xml.sax.saxutils import escape

from app.routers.apifox.run_schemas import RunOut
from app.services.apifox.run_export_common import (
    STATUS_LABELS,
    _assertion_table_rows,
    _format_duration,
    _format_report_time,
    _pretty_json_text,
    _report_summary_rows,
)


def _ensure_reportlab() -> None:
    try:
        import reportlab  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("PDF 导出依赖 reportlab，请执行 pip install -r requirements.txt 并重启后端") from exc


def _pdf_font_candidates() -> List[str]:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    if platform.system() == "Darwin":
        candidates.extend(
            [
                "/System/Library/Fonts/PingFang.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
        )
    for pattern in (
        "/usr/share/fonts/**/NotoSansCJK*.ttc",
        "/usr/share/fonts/**/NotoSansSC*.otf",
        "/usr/share/fonts/**/wqy-microhei*.ttc",
    ):
        candidates.extend(glob.glob(pattern, recursive=True))
    seen = set()
    unique: List[str] = []
    for path in candidates:
        normalized = os.path.normpath(path)
        if normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def _register_pdf_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    registered = set(pdfmetrics.getRegisteredFontNames())
    if "ReportCJK" in registered:
        return "ReportCJK"
    if "STSong-Light" in registered:
        return "STSong-Light"

    for path in _pdf_font_candidates():
        if not os.path.exists(path):
            continue
        try:
            font_name = "ReportCJK"
            if path.lower().endswith(".ttc"):
                pdfmetrics.registerFont(TTFont(font_name, path, subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont(font_name, path))
            return font_name
        except Exception:
            continue

    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _pdf_code_text(text: Any, limit: int = 12000) -> str:
    pretty = _pretty_json_text(text)
    if len(pretty) <= limit:
        return pretty
    return f"{pretty[:limit]}\n... (内容过长，PDF 中已截断)"


def _pdf_escape(text: Any) -> str:
    raw = str(text if text is not None else "-").replace("\x00", "")
    return escape(raw).replace("\n", "<br/>")


def _build_pdf_styles(font_name: str):
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "heading2": ParagraphStyle(
            "ReportHeading2",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=14,
            leading=18,
            spaceBefore=8,
            spaceAfter=8,
        ),
        "heading3": ParagraphStyle(
            "ReportHeading3",
            parent=base["Heading3"],
            fontName=font_name,
            fontSize=12,
            leading=16,
            spaceBefore=6,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            spaceAfter=6,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "ReportCode",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            leftIndent=12,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "table": ParagraphStyle(
            "ReportTable",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9,
            leading=12,
            wordWrap="CJK",
        ),
    }


def _pdf_table(rows: List[List[str]], col_widths: List[float], styles) -> Any:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    wrapped = [
        [Paragraph(_pdf_escape(cell), styles["table"]) for cell in row]
        for row in rows
    ]
    table = Table(wrapped, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("FONTNAME", (0, 0), (-1, -1), styles["table"].fontName),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _append_report_pdf(story: List[Any], report: RunOut, styles) -> None:
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer

    story.append(Paragraph("接口自动化测试报告", styles["title"]))
    story.append(
        Paragraph(
            _pdf_escape(f"报告时间：{_format_report_time(report.started_at)}    套件：{report.target_name or '-'}"),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("报告摘要", styles["heading2"]))
    story.append(
        _pdf_table(
            [["项目", "内容"], *_report_summary_rows(report)],
            [4.2 * cm, 12.5 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("用例执行明细", styles["heading2"]))

    for index, step in enumerate(report.steps, start=1):
        status = STATUS_LABELS.get(step.status, step.status)
        story.append(Paragraph(_pdf_escape(f"{index}. {step.case_name}（{status}）"), styles["heading3"]))
        story.append(
            Paragraph(
                _pdf_escape(
                    f"方法：{step.method}    耗时：{_format_duration(step.duration_ms)}    "
                    f"响应状态：{step.response_status if step.response_status is not None else '-'}"
                ),
                styles["body"],
            )
        )
        story.append(Paragraph(_pdf_escape(f"请求 URL：{step.url}"), styles["body"]))
        if step.error_message:
            story.append(Paragraph(_pdf_escape(f"错误信息：{step.error_message}"), styles["body"]))

        for title, content in [
            ("请求头", step.request_headers),
            ("请求体", step.request_body),
            ("响应头", step.response_headers),
            ("响应体", step.response_body),
        ]:
            story.append(Paragraph(_pdf_escape(title), styles["body"]))
            story.append(Paragraph(_pdf_escape(_pdf_code_text(content)), styles["code"]))

        assertion_rows = _assertion_table_rows(step)
        if assertion_rows:
            story.append(Paragraph("断言结果", styles["body"]))
            story.append(
                _pdf_table(
                    [["类型", "说明", "期望", "实际", "结果"], *assertion_rows],
                    [2.2 * cm, 4.5 * cm, 2.8 * cm, 2.8 * cm, 1.8 * cm],
                    styles,
                )
            )
        story.append(Spacer(1, 0.2 * cm))


def build_run_export_pdf(reports: List[RunOut]) -> BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

    buffer = BytesIO()
    font_name = _register_pdf_font()
    styles = _build_pdf_styles(font_name)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=36,
        title="接口自动化测试报告",
    )

    story: List[Any] = []
    for index, report in enumerate(reports):
        if index > 0:
            story.append(PageBreak())
        _append_report_pdf(story, report, styles)
    story.append(Spacer(1, 12))
    try:
        doc.build(story)
    except Exception as exc:
        raise RuntimeError(f"PDF 生成失败: {exc}") from exc
    buffer.seek(0)
    return buffer

