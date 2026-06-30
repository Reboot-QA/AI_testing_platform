import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import httpx

from app.services.api_response_extract import apply_response_extractors


def test_extract_json_path_from_body():
    response = httpx.Response(
        200,
        json={"code": 9999, "msg": "error", "data": {"token": "abc123"}},
    )
    extractors = [
        {"key": "login_code", "source": "body", "path": "$.code", "enabled": True},
        {"key": "token", "source": "body", "path": "$.data.token", "enabled": True},
    ]
    extracted, results = apply_response_extractors(extractors, response)
    assert extracted["login_code"] == "9999"
    assert extracted["token"] == "abc123"
    assert all(item["passed"] for item in results)


def test_extract_header():
    response = httpx.Response(200, headers={"X-Trace-Id": "trace-001"}, content=b"{}")
    extractors = [{"key": "trace_id", "source": "header", "path": "X-Trace-Id", "enabled": True}]
    extracted, results = apply_response_extractors(extractors, response)
    assert extracted["trace_id"] == "trace-001"


def test_extract_missing_path():
    response = httpx.Response(200, json={"code": 0})
    extractors = [{"key": "missing", "source": "body", "path": "$.data.token", "enabled": True}]
    extracted, results = apply_response_extractors(extractors, response)
    assert "missing" not in extracted
    assert results[0]["passed"] is False


def test_extract_null_and_false():
    response = httpx.Response(200, json={"flag": False, "empty": None, "code": 0})
    extractors = [
        {"key": "flag", "source": "body", "path": "$.flag", "enabled": True},
        {"key": "empty", "source": "body", "path": "$.empty", "enabled": True},
        {"key": "code", "source": "body", "path": "$.code", "enabled": True},
    ]
    extracted, results = apply_response_extractors(extractors, response)
    assert extracted["flag"] == "false"
    assert extracted["empty"] == ""
    assert extracted["code"] == "0"
    assert all(item["passed"] for item in results)


if __name__ == "__main__":
    test_extract_json_path_from_body()
    test_extract_header()
    test_extract_missing_path()
    test_extract_null_and_false()
    print("OK")
