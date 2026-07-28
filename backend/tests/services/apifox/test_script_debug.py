"""apifox 脚本独立调试（M6 迁移）。用 python 脚本（进程内执行，无 node 依赖）。"""

import pytest

from app.routers.apifox.script_schemas import ScriptDebugIn
from app.services.apifox import script_service


def test_debug_pre_script_sets_variable_and_logs():
    out = script_service.debug_script(ScriptDebugIn(
        phase="pre", lang="python",
        content="variables['token'] = 'abc'\nprint('hi')",
        variables={"a": "1"},
    ))

    assert out.status == "passed"
    assert out.variables["token"] == "abc"
    assert out.variables["a"] == "1"  # 已有变量保留
    assert "hi" in out.logs
    assert out.error_message is None


def test_debug_post_script_reads_response_context():
    # 读取 response_status/body：若误路由到 pre（无这些名字）会 NameError，真正守住 pre/post 分派
    out = script_service.debug_script(ScriptDebugIn(
        phase="post", lang="python",
        content="variables['st'] = str(response_status)\nvariables['bd'] = response_body",
        response_body='{"x":1}', response_status=200,
    ))

    assert out.status == "passed"
    assert out.variables["st"] == "200"
    assert out.variables["bd"] == '{"x":1}'


def test_debug_script_error_reports_failed():
    out = script_service.debug_script(ScriptDebugIn(
        phase="pre", lang="python", content="x = 1 / 0",
    ))

    assert out.status == "failed"
    assert out.error_message  # 执行失败带错误信息


def test_debug_empty_content_raises():
    with pytest.raises(ValueError):
        script_service.debug_script(ScriptDebugIn(phase="pre", lang="python", content="   "))
