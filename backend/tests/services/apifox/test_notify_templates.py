"""Apifox 通知模板 · 纯渲染单测（无 DB、无网络）。

覆盖：主题、Telegram HTML 转义/emoji、统计行计算与覆盖、空值行省略、耗时格式、
邮件 HTML 结果色/纯文本兜底不转义。
"""

import pytest

from app.services.apifox.notify_templates import (
    NotifyPayload,
    render_email_html,
    render_email_text,
    render_subject,
    render_telegram,
)


def _p(**kw):
    base = dict(
        event_type="run", result="failure", project_name="P", scene="套件执行",
        target_name="登录", total=12, passed=9, failed=3, ref_id=7,
    )
    base.update(kw)
    return NotifyPayload(**base)


def test_subject_has_headline_and_target():
    assert render_subject(_p(result="success", scene="套件执行")) == "【套件执行成功】登录"


def test_subject_without_target():
    assert render_subject(_p(target_name="")) == "【套件执行失败】"


def test_telegram_escapes_dynamic_values():
    tg = render_telegram(_p(target_name="<script>alert(1)</script>", project_name="a&b"))

    assert "&lt;script&gt;" in tg and "<script>" not in tg
    assert "a&amp;b" in tg


def test_telegram_header_bold_and_emoji():
    assert render_telegram(_p(result="success")).startswith("✅ <b>套件执行成功</b>")
    assert render_telegram(_p(result="failure")).startswith("❌ <b>套件执行失败</b>")


def test_stats_computed_from_counts():
    assert "9/12 通过（75%），3 失败" in render_telegram(_p(passed=9, total=12, failed=3))


def test_stats_all_passed_no_fail_suffix():
    tg = render_telegram(_p(result="success", passed=12, total=12, failed=0))
    assert "12/12 通过（100%）" in tg and "失败" not in tg


def test_stats_text_overrides_counts():
    tg = render_telegram(_p(stats_text="8/10 个接口生成成功，2 个失败", total=10, passed=8, failed=2))
    assert "8/10 个接口生成成功，2 个失败" in tg


def test_optional_rows_omitted_when_empty():
    # 无 duration/triggered_by/happened_at/target → 这些行不出现
    tg = render_telegram(_p(target_name="", duration_ms=None, triggered_by="", happened_at=None))
    assert "耗时" not in tg and "触发" not in tg and "时间" not in tg and "目标" not in tg


@pytest.mark.parametrize("ms,expected", [(0, "0ms"), (999, "999ms"), (1000, "1.0s"), (8100, "8.1s")])
def test_duration_format(ms, expected):
    assert f"耗时：{expected}" in render_telegram(_p(duration_ms=ms))


def test_trigger_label_mapping():
    assert "触发：手动" in render_telegram(_p(triggered_by="manual"))
    assert "触发：定时任务" in render_telegram(_p(triggered_by="schedule:5"))


def test_email_html_banner_color_by_result():
    assert "#16a34a" in render_email_html(_p(result="success"))
    assert "#dc2626" in render_email_html(_p(result="failure"))


def test_email_html_escapes_values():
    html = render_email_html(_p(target_name="<b>x</b>"))
    assert "&lt;b&gt;x&lt;/b&gt;" in html


def test_email_text_is_plain_unescaped():
    text = render_email_text(_p(target_name="<b>x</b>"))
    assert "<b>x</b>" in text  # 纯文本不转义
    assert "<div" not in text and "<td" not in text  # 不含 HTML 结构
