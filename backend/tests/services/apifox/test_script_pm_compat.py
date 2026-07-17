"""apifox JS 脚本 · Postman/Apifox 风格 pm.* 兼容层（回归 bug：pm is not defined）。

依赖本机 node，缺失则整文件跳过（与执行引擎一致，无 node 时 JS 脚本本就不可用）。
"""

import shutil

import pytest

from app.routers.apifox.script_schemas import ScriptDebugIn
from app.services.apifox import script_service

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="需要本机 node 才能跑 JS 脚本")


def _debug(**kw):
    return script_service.debug_script(ScriptDebugIn(lang="javascript", **kw))


# ---------- pm.variables / environment（bug 复现：此前 pm 未注入直接 ReferenceError） ----------
def test_pm_variables_get_set_and_environment_alias():
    out = _debug(
        phase="pre",
        content="pm.variables.set('a', 'A'); pm.environment.set('b', pm.variables.get('a') + '2')",
        variables={},
    )

    assert out.error_message is None
    assert out.status == "passed"
    assert out.variables["a"] == "A"
    assert out.variables["b"] == "A2"


# ---------- pm.response.json / code + pm.test + pm.expect ----------
def test_pm_response_and_test_and_expect_pass():
    content = (
        "const data = pm.response.json();\n"
        "pm.test('status 200', () => pm.expect(pm.response.code).to.equal(200));\n"
        "pm.test('has x', () => pm.expect(data.x).to.eql(1));\n"
        "variables['x'] = String(data.x);"
    )

    out = _debug(phase="post", content=content, response_body='{"x":1}', response_status=200)

    assert out.status == "passed"
    assert out.variables["x"] == "1"
    assert any("✓ status 200" in log for log in out.logs)
    assert any("✓ has x" in log for log in out.logs)


# ---------- pm.test 内断言失败：记入日志但不中断脚本（Postman 语义） ----------
def test_pm_test_failure_is_recorded_not_thrown():
    out = _debug(
        phase="post",
        content="pm.test('will fail', () => pm.expect(1).to.equal(2)); variables['done'] = '1'",
        response_body="{}",
        response_status=200,
    )

    assert out.status == "passed"  # 断言失败不算脚本执行失败
    assert out.variables["done"] == "1"
    assert any("✗ will fail" in log for log in out.logs)


# ---------- pm.response.to.have.status 链式断言 ----------
def test_pm_response_to_have_status():
    out = _debug(
        phase="post",
        content="pm.response.to.have.status(200); variables['ok'] = '1'",
        response_body="{}",
        response_status=200,
    )

    assert out.status == "passed"
    assert out.variables["ok"] == "1"


# ---------- 回归：原生 variables/console API 不受影响 ----------
def test_native_variables_api_still_works():
    out = _debug(phase="pre", content="variables['k'] = 'v'; console.log('hi')", variables={})

    assert out.status == "passed"
    assert out.variables["k"] == "v"
    assert "hi" in out.logs
