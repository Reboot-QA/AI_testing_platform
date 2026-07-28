import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.api_request_builder import prepare_case_request


def test_urlencoded_from_meta():
    headers = json.dumps(
        {
            "Content-Type": "application/x-www-form-urlencoded",
            "__meta": {
                "body_type": "urlencoded",
                "form_body": [
                    {"key": "accountChannel", "value": "AUTH_PHONE_PWD", "enabled": True},
                    {"key": "dataJson", "value": '{"phone":"17345555444"}', "enabled": True},
                ],
            },
        }
    )
    body = json.dumps([{"key": "accountChannel", "value": "AUTH_PHONE_PWD"}])
    method, url, hdrs, out_body, extra = prepare_case_request(headers, "/login", "POST", body, None)
    assert out_body
    assert "accountChannel=AUTH_PHONE_PWD" in out_body
    assert "dataJson=" in out_body


def test_form_data_from_meta():
    headers = json.dumps(
        {
            "__meta": {
                "body_type": "form-data",
                "form_body": [{"key": "foo", "value": "bar", "enabled": True}],
            }
        }
    )
    method, url, hdrs, out_body, extra = prepare_case_request(headers, "/login", "POST", "[]", None)
    assert extra.get("form_data") == {"foo": "bar"}


def test_json_object_body_fallback():
    login_json = json.dumps(
        {
            "accountChannel": "AUTH_PHONE_PWD",
            "dataJson": {"phone": "17345555444", "password": "secret"},
            "solidLetterPower": True,
        },
        ensure_ascii=False,
    )
    headers = json.dumps({"__meta": {"body_type": "urlencoded", "form_body": []}})
    method, url, hdrs, out_body, extra = prepare_case_request(headers, "/login", "POST", login_json, None)
    assert "accountChannel=AUTH_PHONE_PWD" in out_body
    assert "dataJson=" in out_body
    assert "17345555444" in out_body


if __name__ == "__main__":
    test_urlencoded_from_meta()
    test_form_data_from_meta()
    test_json_object_body_fallback()
    print("OK")
