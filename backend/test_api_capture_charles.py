import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.api_capture_service import parse_capture_text, parse_curl_capture, parse_raw_http_capture


def test_charles_multiline_curl():
    charles_curl = (
        "curl -H 'Content-Type: application/json' \\\n"
        "  -H 'Authorization: Bearer token123' \\\n"
        "  -X POST \\\n"
        "  --data-raw '{\"username\":\"admin\"}' \\\n"
        "  'https://api.example.com/v1/login'"
    )
    result = parse_curl_capture(charles_curl)
    assert result["method"] == "POST"
    assert result["base_url"] == "https://api.example.com"
    assert result["path"] == "/v1/login"
    assert "admin" in result["body"]
    assert result["source"] == "charles_curl"


def test_charles_copy_request():
    charles_raw = (
        "POST /v1/login HTTP/1.1\n"
        "Host: api.example.com\n"
        "Content-Type: application/json\n"
        "Accept: */*\n"
        "User-Agent: Charles\n"
        "\n"
        '{"username":"admin"}'
    )
    result = parse_raw_http_capture(charles_raw)
    assert result["method"] == "POST"
    assert result["base_url"] == "https://api.example.com"
    assert result["path"] == "/v1/login"
    assert result["source"] == "charles_raw"


def test_charles_curl_url_at_end():
    text = (
        'curl -H "Host: www.example.com" -H "Content-Type: application/json" '
        '-d \'{"k":1}\' "https://www.example.com/api/foo?bar=1"'
    )
    result = parse_capture_text(text)
    assert result["base_url"] == "https://www.example.com"
    assert result["path"] == "/api/foo?bar=1"
    assert result["method"] == "POST"


def test_curl_body_not_confused_by_device_type_header():
    text = (
        'curl -H "Host: tp.example.com" -H "X-Device-Type: " -H "X-Device-Code: " '
        '-H "Content-Type: application/json" '
        '--data-binary "{\\"phone\\":\\"17345555444\\",\\"password\\":\\"secret\\"}" '
        '"https://tp.example.com/api/login"'
    )
    result = parse_curl_capture(text)
    assert result["method"] == "POST"
    assert "17345555444" in result["body"]
    assert "secret" in result["body"]
    assert "evice-Type" not in result["body"]


if __name__ == "__main__":
    test_charles_multiline_curl()
    test_charles_copy_request()
    test_charles_curl_url_at_end()
    test_curl_body_not_confused_by_device_type_header()
    print("ALL PASSED")
