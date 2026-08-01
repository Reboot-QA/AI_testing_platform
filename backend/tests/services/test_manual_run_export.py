"""功能测试单报告导出：消费 ManualTestRunDetailOut，产出 Excel/Word/PDF。"""

from datetime import datetime

import pytest

from app.schemas import ManualTestRunCaseOut, ManualTestRunDetailOut
from app.services import manual_run_export_service as ex


def _report() -> ManualTestRunDetailOut:
    started = datetime(2026, 7, 15, 10, 0, 0)
    finished = datetime(2026, 7, 15, 10, 5, 30)
    case = ManualTestRunCaseOut(
        id=1,
        run_id=1,
        testcase_id=10,
        sort_order=1,
        testcase_sort_order=1,
        result="pass",
        actual_result="符合预期",
        remark="",
        executed_by=1,
        executor_name="测试员",
        executed_at=finished,
        case_title="登录成功",
        case_priority="P1",
        case_type="功能",
        preconditions="已注册账号",
        steps="输入账号密码并登录",
        expected_results="进入首页",
    )
    return ManualTestRunDetailOut(
        id=1,
        project_id=1,
        name="回归测试单",
        build_name="v1.0.0",
        description="冒烟",
        status="finished",
        executor_id=1,
        executor_name="测试员",
        total_count=1,
        passed_count=1,
        failed_count=0,
        blocked_count=0,
        skipped_count=0,
        pending_count=0,
        pass_rate=100.0,
        started_at=started,
        finished_at=finished,
        created_at=started,
        cases=[case],
    )


@pytest.mark.parametrize("fmt,ext", [("excel", "xlsx"), ("word", "docx"), ("pdf", "pdf")])
def test_export_binary_formats_nonempty(fmt, ext):
    content, _media, out_ext = ex.build_manual_run_export(_report(), fmt)

    assert out_ext == ext
    data = content.getvalue()
    assert len(data) > 0
    if ext in ("xlsx", "docx"):
        assert data[:2] == b"PK"


def test_export_invalid_format_raises():
    with pytest.raises(ValueError):
        ex.build_manual_run_export(_report(), "txt")


def test_filename_uses_run_name():
    name = ex.build_export_filename(_report(), "xlsx")

    assert "回归测试单" in name and name.endswith(".xlsx")
