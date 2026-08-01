"""Apifox 通知 · 展示模板（成功/失败两套，Telegram HTML + 邮件 HTML）。

单向依赖：notify_service → 本模块。本模块不碰 DB、不发送，只把结构化事件
`NotifyPayload` 渲染成各渠道文本。动态值一律 HTML 转义，防注入/破坏消息结构。
"""

from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import List, Optional, Tuple

# 结果 → 视觉
_EMOJI = {"success": "✅", "failure": "❌"}
_RESULT_LABEL = {"success": "成功", "failure": "失败"}
_BANNER_BG = {"success": "#16a34a", "failure": "#dc2626"}

# 行标签 → Telegram 前缀图标（未知标签无图标）
_ROW_ICON = {
    "项目": "📦",
    "目标": "🎯",
    "结果": "📊",
    "耗时": "⏱",
    "触发": "🚀",
    "时间": "🕐",
    "运行记录": "🔗",
    "任务": "🔗",
    "说明": "📝",
}


@dataclass
class NotifyPayload:
    """一条通知事件的结构化载荷（四个触发点填它，模板据此渲染）。"""

    event_type: str  # schedule | run | aigen | import_schedule
    result: str  # success | failure
    project_name: str
    scene: str  # 场景名，如「套件执行」「定时任务」「AI 生成任务」「定时导入」
    target_name: str = ""
    stats_text: Optional[str] = None  # 给定则直接用；否则按 passed/total 计算
    total: int = 0
    passed: int = 0
    failed: int = 0
    duration_ms: Optional[float] = None
    ref_id: Optional[int] = None
    ref_label: str = "运行记录"
    triggered_by: str = ""
    happened_at: Optional[datetime] = None
    extra: str = ""

    @property
    def is_success(self) -> bool:
        return self.result == "success"


def _fmt_duration(ms: Optional[float]) -> str:
    if ms is None:
        return ""
    return f"{int(ms)}ms" if ms < 1000 else f"{ms / 1000:.1f}s"


def _fmt_time(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _trigger_label(triggered_by: str) -> str:
    tb = (triggered_by or "").strip()
    if not tb or tb == "manual":
        return "手动"
    if tb.startswith("schedule:"):
        return "定时任务"
    return tb


def _stats(p: NotifyPayload) -> str:
    if p.stats_text:
        return p.stats_text
    if p.total <= 0:
        return ""
    rate = round(p.passed / p.total * 100) if p.total else 0
    line = f"{p.passed}/{p.total} 通过（{rate}%）"
    if p.failed:
        line += f"，{p.failed} 失败"
    return line


def _headline(p: NotifyPayload) -> str:
    return f"{p.scene}{_RESULT_LABEL.get(p.result, '')}"


def _rows(p: NotifyPayload) -> List[Tuple[str, str]]:
    """(标签, 值) 有序列表，空值行自动省略。"""
    rows: List[Tuple[str, str]] = [("项目", p.project_name)]
    if p.target_name:
        rows.append(("目标", p.target_name))
    stats = _stats(p)
    if stats:
        rows.append(("结果", stats))
    dur = _fmt_duration(p.duration_ms)
    if dur:
        rows.append(("耗时", dur))
    if p.triggered_by:
        rows.append(("触发", _trigger_label(p.triggered_by)))
    ts = _fmt_time(p.happened_at)
    if ts:
        rows.append(("时间", ts))
    if p.ref_id:
        rows.append((p.ref_label, f"#{p.ref_id}"))
    if p.extra:
        rows.append(("说明", p.extra))
    return [(k, v) for k, v in rows if v]


# ---------- 渲染 ----------
def render_subject(p: NotifyPayload) -> str:
    head = _headline(p)
    return f"【{head}】{p.target_name}" if p.target_name else f"【{head}】"


def render_telegram(p: NotifyPayload) -> str:
    """Telegram HTML parse_mode 文本（发送时须带 parse_mode=HTML）。"""
    emoji = _EMOJI.get(p.result, "")
    lines = [f"{emoji} <b>{escape(_headline(p))}</b>", "━━━━━━━━━━━━━━"]
    for label, value in _rows(p):
        icon = _ROW_ICON.get(label, "")
        prefix = f"{icon} " if icon else ""
        lines.append(f"{prefix}{escape(label)}：{escape(value)}")
    return "\n".join(lines)


def render_email_text(p: NotifyPayload) -> str:
    """邮件纯文本兜底（不含 HTML）。"""
    lines = [_headline(p), ""]
    lines += [f"{label}：{value}" for label, value in _rows(p)]
    return "\n".join(lines)


def render_email_html(p: NotifyPayload) -> str:
    """邮件 HTML（内联样式，邮件客户端不认外链 CSS）。"""
    banner = _BANNER_BG.get(p.result, "#4b5563")
    emoji = _EMOJI.get(p.result, "")
    row_html = "".join(
        f'<tr>'
        f'<td style="padding:8px 16px;color:#6b7280;font-size:13px;white-space:nowrap;'
        f'vertical-align:top;border-bottom:1px solid #f0f0f0;">{escape(label)}</td>'
        f'<td style="padding:8px 16px;color:#111827;font-size:14px;'
        f'border-bottom:1px solid #f0f0f0;">{escape(value)}</td>'
        f'</tr>'
        for label, value in _rows(p)
    )
    return (
        '<div style="max-width:520px;margin:0 auto;font-family:-apple-system,'
        'BlinkMacSystemFont,\'Segoe UI\',Roboto,\'Helvetica Neue\',Arial,sans-serif;'
        'border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">'
        f'<div style="background:{banner};color:#ffffff;padding:16px 20px;'
        f'font-size:16px;font-weight:600;">{emoji} {escape(_headline(p))}</div>'
        '<table style="width:100%;border-collapse:collapse;">'
        f'{row_html}</table>'
        '<div style="padding:10px 16px;color:#9ca3af;font-size:12px;">'
        '本邮件由 AI 测试平台自动发送，请勿直接回复。</div>'
        '</div>'
    )
