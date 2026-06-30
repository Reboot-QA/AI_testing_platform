import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.api_request_builder import iter_data_drive_variable_sets, prepare_case_request


def test_variables_in_json_body_and_headers():
    headers = json.dumps(
        {
            "X-Token": "{{token}}",
            "__meta": {
                "body_type": "json",
                "variables": [
                    {"key": "phone", "value": "17341587465", "enabled": True},
                    {"key": "password", "value": "secret123", "enabled": True},
                    {"key": "token", "value": "abc-token", "enabled": True},
                    {"key": "disabled", "value": "ignored", "enabled": False},
                ],
            },
        }
    )
    body = json.dumps(
        {
            "dataJson": {"phone": "{{phone}}", "password": "{{password}}"},
            "deviceNo": "{{unknown}}",
        },
        ensure_ascii=False,
    )
    method, url, hdrs, out_body, extra = prepare_case_request(headers, "/login", "POST", body, None)
    assert hdrs["X-Token"] == "abc-token"
    parsed = json.loads(out_body)
    assert parsed["dataJson"]["phone"] == "17341587465"
    assert parsed["dataJson"]["password"] == "secret123"
    assert parsed["deviceNo"] == "{{unknown}}"


def test_variables_in_urlencoded_form():
    headers = json.dumps(
        {
            "__meta": {
                "body_type": "urlencoded",
                "form_body": [
                    {"key": "phone", "value": "{{phone}}", "enabled": True},
                ],
                "variables": [{"key": "phone", "value": "13800138000", "enabled": True}],
            }
        }
    )
    method, url, hdrs, out_body, extra = prepare_case_request(headers, "/login", "POST", "[]", None)
    assert "phone=13800138000" in out_body


def test_variables_in_query_and_path():
    headers = json.dumps(
        {
            "__meta": {
                "query": [{"key": "q", "value": "{{keyword}}", "enabled": True}],
                "path_vars": [{"key": "id", "value": "{{userId}}", "enabled": True}],
                "variables": [
                    {"key": "keyword", "value": "hello", "enabled": True},
                    {"key": "userId", "value": "42", "enabled": True},
                ],
            }
        }
    )
    method, url, hdrs, out_body, extra = prepare_case_request(headers, "/users/{id}", "GET", "", None)
    assert url.endswith("/users/42?q=hello")


def test_data_drive_iterations():
    headers = json.dumps(
        {
            "__meta": {
                "variables": [
                    {"key": "phone", "value": "default-phone", "enabled": True},
                    {"key": "password", "value": "default-pass", "enabled": True},
                ],
                "data_drive": {
                    "enabled": True,
                    "rows": [
                        {
                            "enabled": True,
                            "name": "账号A",
                            "values": {"phone": "13800138000", "password": "pass-a"},
                        },
                        {
                            "enabled": True,
                            "name": "账号B",
                            "values": {"phone": "13900139000"},
                        },
                    ],
                },
            }
        }
    )
    body = '{"phone":"{{phone}}","password":"{{password}}"}'
    sets = iter_data_drive_variable_sets(json.loads(headers)["__meta"])
    assert len(sets) == 2
    assert sets[0][0] == "账号A"
    assert sets[0][1]["phone"] == "13800138000"
    assert sets[1][1]["password"] == "default-pass"

    method, url, hdrs, out_body, extra = prepare_case_request(
        headers, "/login", "POST", body, None, variables=sets[1][1]
    )
    parsed = json.loads(out_body)
    assert parsed["phone"] == "13900139000"
    assert parsed["password"] == "default-pass"


if __name__ == "__main__":
    test_variables_in_json_body_and_headers()
    test_variables_in_urlencoded_form()
    test_variables_in_query_and_path()
    test_data_drive_iterations()
    print("OK")
