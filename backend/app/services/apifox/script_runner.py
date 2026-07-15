import importlib
import json
import subprocess
from typing import Any, Dict, List, Optional, Tuple


SAFE_PYTHON_BUILTINS = {
    "True": True,
    "False": False,
    "None": None,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "sorted": sorted,
    "zip": zip,
    "map": map,
    "filter": filter,
    "isinstance": isinstance,
    "any": any,
    "all": all,
}


NODE_RUNNER = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
const variables = input.variables;
const logs = [];
const console = {
  log: (...args) => logs.push(args.map((item) => String(item)).join(' ')),
};
try {
  const runner = new Function('variables', 'console', input.script);
  runner(variables, console);
  process.stdout.write(JSON.stringify({ ok: true, variables, logs }));
} catch (err) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(err), variables, logs }));
}
"""

POST_NODE_RUNNER = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
const variables = input.variables;
const response = input.response || { body: '', status: 0, headers: {} };
const logs = [];
const console = {
  log: (...args) => logs.push(args.map((item) => String(item)).join(' ')),
};
try {
  const runner = new Function('variables', 'console', 'response', input.script);
  runner(variables, console, response);
  process.stdout.write(JSON.stringify({ ok: true, variables, logs }));
} catch (err) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(err), variables, logs }));
}
"""


def _normalize_variables(variables: Dict[str, str]) -> Dict[str, str]:
    return {str(key): "" if value is None else str(value) for key, value in (variables or {}).items()}


def resolve_pre_script(meta: Dict[str, Any]) -> Tuple[str, str]:
    lang = (meta.get("pre_script_lang") or "javascript").lower()
    if lang in ("js",):
        lang = "javascript"
    if lang in ("py",):
        lang = "python"
    if lang not in ("javascript", "python"):
        lang = "javascript"

    stores = meta.get("pre_script_stores") or {}
    if isinstance(stores, dict):
        script = str(stores.get(lang) or "").strip()
        if script:
            return script, lang

    legacy = str(meta.get("pre_script") or "").strip()
    return legacy, lang


def run_pre_script(
    script: Optional[str],
    language: Optional[str],
    variables: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    if not script or not script.strip():
        return _normalize_variables(variables or {}), [], None

    lang = (language or "javascript").lower()
    current = _normalize_variables(variables or {})
    if lang in ("js", "javascript"):
        return _run_javascript_pre_script(script, current)
    if lang in ("py", "python"):
        return _run_python_pre_script(script, current)
    return current, [], f"不支持的脚本语言: {language}"


ALLOWED_PYTHON_MODULES = ("json", "time", "random", "hashlib", "base64", "re", "uuid", "faker")


def _build_allowed_modules() -> Dict[str, Any]:
    modules: Dict[str, Any] = {
        "json": json,
        "time": importlib.import_module("time"),
        "random": importlib.import_module("random"),
        "hashlib": importlib.import_module("hashlib"),
        "base64": importlib.import_module("base64"),
        "re": importlib.import_module("re"),
        "uuid": importlib.import_module("uuid"),
    }
    try:
        modules["faker"] = importlib.import_module("faker")
    except ImportError:
        pass
    return modules


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name not in ALLOWED_PYTHON_MODULES:
        raise ImportError(f"import {name} 不被允许")
    return importlib.import_module(name)

def _run_python_pre_script(script: str, variables: Dict[str, str]) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    logs: List[str] = []

    def _log(*args: Any) -> None:
        logs.append(" ".join(str(arg) for arg in args))

    allowed_modules = _build_allowed_modules()
    if "from faker import" in script or "import faker" in script:
        if "faker" not in allowed_modules:
            return variables, logs, "Python 脚本需要 Faker 库，请在后端执行 pip install Faker"

    namespace = {
        "variables": dict(variables),
        **allowed_modules,
        "console": type("Console", (), {"log": _log})(),
        "__builtins__": {**SAFE_PYTHON_BUILTINS, "print": _log, "__import__": _safe_import},
    }
    if "faker" in allowed_modules:
        try:
            from faker import Faker as FakerClass

            namespace["Faker"] = FakerClass
        except ImportError:
            pass

    try:
        exec(script, namespace)
    except Exception as exc:
        return variables, logs, f"Python 脚本执行失败: {exc}"

    updated = namespace.get("variables", variables)
    if not isinstance(updated, dict):
        return variables, logs, "Python 脚本未正确维护 variables 对象"

    return _normalize_variables(updated), logs, None


def _run_javascript_pre_script(script: str, variables: Dict[str, str]) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    payload = json.dumps({"variables": variables, "script": script}, ensure_ascii=False)
    try:
        completed = subprocess.run(
            ["node", "-e", NODE_RUNNER],
            input=payload,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return variables, [], "JavaScript 脚本需要安装 Node.js 并加入 PATH"
    except subprocess.TimeoutExpired:
        return variables, [], "JavaScript 脚本执行超时（5s）"

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if not stdout:
        message = stderr or "JavaScript 脚本执行失败"
        return variables, [], message

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        message = stderr or stdout or "JavaScript 脚本返回结果无法解析"
        return variables, [], message

    logs = [str(item) for item in result.get("logs") or []]
    updated = result.get("variables") if isinstance(result.get("variables"), dict) else variables
    if not result.get("ok", False):
        return _normalize_variables(updated), logs, result.get("error") or "JavaScript 脚本执行失败"

    return _normalize_variables(updated), logs, None


def _build_response_context(
    response_body: Optional[str],
    response_status: Optional[int],
    response_headers: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    headers = response_headers if isinstance(response_headers, dict) else {}
    body = response_body or ""
    status = int(response_status or 0)
    return {
        "body": body,
        "status": status,
        "headers": {str(key): "" if value is None else str(value) for key, value in headers.items()},
    }


def run_post_script(
    script: Optional[str],
    language: Optional[str],
    variables: Optional[Dict[str, str]] = None,
    response_body: Optional[str] = None,
    response_status: Optional[int] = None,
    response_headers: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    if not script or not script.strip():
        return _normalize_variables(variables or {}), [], None

    lang = (language or "javascript").lower()
    current = _normalize_variables(variables or {})
    response = _build_response_context(response_body, response_status, response_headers)
    if lang in ("js", "javascript"):
        return _run_javascript_post_script(script, current, response)
    if lang in ("py", "python"):
        return _run_python_post_script(script, current, response)
    return current, [], f"不支持的脚本语言: {language}"


def _run_python_post_script(
    script: str,
    variables: Dict[str, str],
    response: Dict[str, Any],
) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    logs: List[str] = []

    def _log(*args: Any) -> None:
        logs.append(" ".join(str(arg) for arg in args))

    allowed_modules = _build_allowed_modules()
    if "from faker import" in script or "import faker" in script:
        if "faker" not in allowed_modules:
            return variables, logs, "Python 脚本需要 Faker 库，请在后端执行 pip install Faker"

    namespace = {
        "variables": dict(variables),
        "response_body": response.get("body", ""),
        "response_status": response.get("status", 0),
        "response_headers": dict(response.get("headers") or {}),
        "response": dict(response),
        **allowed_modules,
        "console": type("Console", (), {"log": _log})(),
        "__builtins__": {**SAFE_PYTHON_BUILTINS, "print": _log, "__import__": _safe_import},
    }
    if "faker" in allowed_modules:
        try:
            from faker import Faker as FakerClass

            namespace["Faker"] = FakerClass
        except ImportError:
            pass

    try:
        exec(script, namespace)
    except Exception as exc:
        return variables, logs, f"Python 脚本执行失败: {exc}"

    updated = namespace.get("variables", variables)
    if not isinstance(updated, dict):
        return variables, logs, "Python 脚本未正确维护 variables 对象"

    return _normalize_variables(updated), logs, None


def _run_javascript_post_script(
    script: str,
    variables: Dict[str, str],
    response: Dict[str, Any],
) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    payload = json.dumps({"variables": variables, "script": script, "response": response}, ensure_ascii=False)
    try:
        completed = subprocess.run(
            ["node", "-e", POST_NODE_RUNNER],
            input=payload,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return variables, [], "JavaScript 脚本需要安装 Node.js 并加入 PATH"
    except subprocess.TimeoutExpired:
        return variables, [], "JavaScript 脚本执行超时（5s）"

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if not stdout:
        message = stderr or "JavaScript 脚本执行失败"
        return variables, [], message

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        message = stderr or stdout or "JavaScript 脚本返回结果无法解析"
        return variables, [], message

    logs = [str(item) for item in result.get("logs") or []]
    updated = result.get("variables") if isinstance(result.get("variables"), dict) else variables
    if not result.get("ok", False):
        return _normalize_variables(updated), logs, result.get("error") or "JavaScript 脚本执行失败"

    return _normalize_variables(updated), logs, None
