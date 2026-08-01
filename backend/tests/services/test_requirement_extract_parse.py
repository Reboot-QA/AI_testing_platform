from app.services import ai_service as svc


def test_parse_requirements_salvages_truncated_tail():
    content = '{"requirements":[{"title":"a","description":"d1","req_type":"functional","priority":"P1"},{"title":"b","desc'

    items = svc._parse_requirements_response(content)

    assert len(items) == 1
    assert items[0]["title"] == "a"


def test_parse_requirements_salvages_missing_comma():
    content = '{"requirements":[{"title":"a","description":"d1","req_type":"functional","priority":"P1"} {"title":"b","description":"d2","req_type":"functional","priority":"P2"}]}'

    items = svc._parse_requirements_response(content)

    assert [item["title"] for item in items] == ["a", "b"]
