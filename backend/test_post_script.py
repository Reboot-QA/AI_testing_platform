import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.api_script_runner import run_post_script


def test_python_post_script_reads_response():
    script = """
import json
body = json.loads(response_body) if response_body else {}
variables['code'] = str(body.get('code', ''))
"""
    response_body = json.dumps({"code": 0, "msg": "ok"})
    updated, logs, error = run_post_script(
        script,
        "python",
        {},
        response_body,
        200,
        {"Content-Type": "application/json"},
    )
    assert error is None, error
    assert updated["code"] == "0"


if __name__ == "__main__":
    test_python_post_script_reads_response()
    print("OK")
