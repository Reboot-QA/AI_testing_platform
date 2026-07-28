"""Git 私有仓库 raw 文件导入：PAT 鉴权头拼装 + fetch_source 透传。"""

import httpx

from app.services.apifox import import_service


def test_git_token_headers_covers_github_and_gitlab():
    headers = import_service.git_token_headers("tok123")

    assert headers["Authorization"] == "Bearer tok123"  # GitHub raw
    assert headers["PRIVATE-TOKEN"] == "tok123"  # GitLab raw


def test_fetch_source_passes_headers(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        return httpx.Response(200, text='{"openapi":"3.0.0","paths":{}}', request=httpx.Request("GET", url))

    monkeypatch.setattr(import_service.httpx, "get", fake_get)

    text = import_service.fetch_source("https://raw.x/openapi.json", headers={"PRIVATE-TOKEN": "t"})

    assert '"openapi"' in text
    assert captured["headers"] == {"PRIVATE-TOKEN": "t"}
