"""JS 脚本预置库（对齐 Postman 内置库：CryptoJS/lodash/uuid 等）注入验证。

依赖 node + script_libs/node_modules（Docker 里由镜像装、本地需 cd backend/script_libs && npm i）。
任一缺失则跳过。
"""

import shutil
from pathlib import Path

import pytest

from app.routers.apifox.script_schemas import ScriptDebugIn
from app.services.apifox import script_service

_LIBS = Path(__file__).resolve().parents[3] / "script_libs" / "node_modules"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not _LIBS.exists(),
    reason="需要 node 且已安装 script_libs 预置库",
)


def _debug(content, phase="pre", **kw):
    return script_service.debug_script(ScriptDebugIn(lang="javascript", phase=phase, content=content, **kw))


def test_cryptojs_global_available():
    out = _debug("variables['h'] = CryptoJS.MD5('abc').toString()")

    assert out.error_message is None
    assert out.variables["h"] == "900150983cd24fb0d6963f7d28e17f72"


def test_cryptojs_hmac_and_require_form():
    # 全局 CryptoJS 与 require('crypto-js') 两种写法都应可用（对齐 Postman）
    out = _debug(
        "const C = require('crypto-js');\n"
        "variables['g'] = CryptoJS.HmacSHA256('data', 'key').toString();\n"
        "variables['r'] = C.HmacSHA256('data', 'key').toString();"
    )

    assert out.error_message is None
    assert out.variables["g"] == out.variables["r"]
    assert len(out.variables["g"]) == 64


def test_lodash_and_uuid_globals():
    out = _debug(
        "variables['c'] = JSON.stringify(_.chunk([1,2,3,4], 2));\n"
        "variables['u'] = String(uuid.v4().length);"
    )

    assert out.error_message is None
    assert out.variables["c"] == "[[1,2],[3,4]]"
    assert out.variables["u"] == "36"
