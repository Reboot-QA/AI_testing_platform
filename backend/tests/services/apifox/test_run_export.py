"""apifox 运行报告导出：消费 RunOut，产出 Excel/Word/PDF/JSON。

覆盖迁移关键点：target_name/steps 字段适配、dict headers 美化、各格式非空。
"""

import json
from datetime import datetime

import pytest

from app.routers.apifox.run_schemas import RunOut, RunStepOut
from app.services.apifox import run_export_service as ex


def _report() -> RunOut:
    step = RunStepOut(
        id=1, step_type="case", case_name="登录", method="POST", url="/login",
        status="passed", duration_ms=123.0, response_status=200,
        request_headers={"Content-Type": "application/json"}, request_body='{"a":1}',
        response_headers={"X": "y"}, response_body='{"ok":true}',
        assertion_results=[
            {"type": "status_code", "passed": True, "message": "200", "expected": "200", "actual": "200"}
        ],
    )
    return RunOut(
        id=1, project_id=1, target_type="case", target_id=1, target_name="登录用例",
        status="passed", total_count=1, passed_count=1, failed_count=0, pass_rate=100.0,
        duration_ms=123.0, triggered_by="manual", started_at=datetime(2026, 7, 15, 10, 0),
        steps=[step],
    )


@pytest.mark.parametrize("fmt,ext", [("excel", "xlsx"), ("word", "docx"), ("pdf", "pdf")])
def test_export_binary_formats_nonempty(fmt, ext):
    content, _media, out_ext = ex.build_run_export([_report()], fmt)

    assert out_ext == ext
    data = content.getvalue()
    assert len(data) > 0
    if ext in ("xlsx", "docx"):
        assert data[:2] == b"PK"  # openxml 是 zip 容器


def test_export_json_carries_apifox_fields():
    content, _media, ext = ex.build_run_export([_report()], "json")

    assert ext == "json"
    data = json.loads(content)
    assert data["target_name"] == "登录用例"
    assert data["steps"][0]["case_name"] == "登录"


def test_export_invalid_format_raises():
    with pytest.raises(ValueError):
        ex.build_run_export([_report()], "txt")


def test_filename_uses_target_name():
    name = ex.build_export_filename([_report()], "xlsx")

    assert "登录用例" in name and name.endswith(".xlsx")


def test_pretty_json_text_formats_dict_headers():
    from app.services.apifox.run_export_common import _pretty_json_text

    out = _pretty_json_text({"Content-Type": "application/json"})

    assert '"Content-Type": "application/json"' in out  # dict 被美化为 JSON，非 Python repr


def test_pretty_json_text_empty_dict_is_dash():
    from app.services.apifox.run_export_common import _pretty_json_text

    assert _pretty_json_text({}) == "-"
