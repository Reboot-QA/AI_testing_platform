import logging
import time
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import Request, urlopen

from app.config import settings

INTERNAL_HOSTS = frozenset({"127.0.0.1", "localhost", "grafana", "loki"})
GRAFANA_PROXY_PREFIX = "/api/v1/logs/grafana"
DASHBOARD_UID = "ai-platform-logs"
DASHBOARD_QUERY = "orgId=1&refresh=10s&kiosk"
# 英文标题对应 slug；与 provision JSON 保持一致，API 不可用时作兜底
DASHBOARD_ROUTE_FALLBACK = "/d/ai-platform-logs/ai-platform-logs"

_grafana_upstream_cache: Optional[tuple] = None
_loki_upstream_cache: Optional[tuple] = None
_dashboard_meta_cache: Optional[tuple] = None


def _host_gateway_candidates(port: int) -> List[str]:
    return [
        _build_url("http://host.docker.internal", port),
        f"http://172.17.0.1:{port}",
        _build_url("http://127.0.0.1", port),
    ]


def _resolve_upstream(cache_name: str, primary_url: str, port: int, health_path: str) -> str:
    cache = globals()[cache_name]
    now = time.time()
    if cache and now - cache[0] < 60:
        return cache[1]

    candidates = [primary_url, *_host_gateway_candidates(port)]
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _probe(f"{candidate}{health_path}"):
            globals()[cache_name] = (now, candidate)
            return candidate

    globals()[cache_name] = (now, primary_url)
    return primary_url


def _build_url(base: str, port: int, default_host: str = "127.0.0.1") -> str:
    value = (base or "").strip().rstrip("/")
    if value:
        return value
    return f"http://{default_host}:{port}"


def _apply_public_host(url: str, public_host: Optional[str]) -> str:
    if not public_host or public_host in {"127.0.0.1", "localhost"}:
        return url
    parsed = urlparse(url)
    if not parsed.hostname or parsed.hostname not in INTERNAL_HOSTS:
        return url
    netloc = f"{public_host}:{parsed.port}" if parsed.port else public_host
    return urlunparse(parsed._replace(netloc=netloc))


def _resolve_public_url(internal_url: str, public_url_setting: str, public_host: Optional[str]) -> str:
    configured = (public_url_setting or "").strip().rstrip("/")
    if configured:
        return configured
    return _apply_public_host(internal_url, public_host)


def _probe(url: str, timeout: float = 2.0) -> bool:
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except URLError:
        return False
    except Exception:
        return False


def get_grafana_url() -> str:
    return _build_url(settings.grafana_url, settings.grafana_port)


def resolve_grafana_upstream() -> str:
    return _resolve_upstream(
        "_grafana_upstream_cache",
        get_grafana_url(),
        settings.grafana_port,
        "/api/health",
    )


def get_loki_url() -> str:
    return _build_url(settings.loki_url, settings.loki_port)


def resolve_loki_upstream() -> str:
    return _resolve_upstream(
        "_loki_upstream_cache",
        get_loki_url(),
        settings.loki_port,
        "/ready",
    )


def _probe_grafana() -> bool:
    return _probe(f"{resolve_grafana_upstream()}/api/health")


def _probe_loki() -> bool:
    return _probe(f"{resolve_loki_upstream()}/ready")


def _grafana_admin_auth():
    user = (settings.grafana_admin_user or "admin").strip()
    password = settings.grafana_admin_password or ""
    if not user or not password:
        return None, user, password
    import httpx

    return httpx.BasicAuth(user, password), user, password


def _meta_url_to_dashboard_route(meta_url: str) -> Optional[str]:
    if not meta_url:
        return None
    route = meta_url.strip()
    if route.startswith(GRAFANA_PROXY_PREFIX):
        route = route[len(GRAFANA_PROXY_PREFIX) :] or "/"
    if not route.startswith("/d/"):
        return None
    return route.split("?", 1)[0]


def _fetch_dashboard_meta() -> tuple[bool, str, Optional[str]]:
    global _dashboard_meta_cache
    now = time.time()
    if _dashboard_meta_cache and now - _dashboard_meta_cache[0] < 60:
        return _dashboard_meta_cache[1], _dashboard_meta_cache[2], _dashboard_meta_cache[3]

    auth, _, _ = _grafana_admin_auth()
    if auth is None:
        result = (False, "未配置 GRAFANA_ADMIN_PASSWORD", None)
        _dashboard_meta_cache = (now, *result)
        return result

    base = resolve_grafana_upstream().rstrip("/")
    api_paths = (
        f"{base}/api/dashboards/uid/{DASHBOARD_UID}",
        f"{base}{GRAFANA_PROXY_PREFIX}/api/dashboards/uid/{DASHBOARD_UID}",
    )
    try:
        import httpx

        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0), follow_redirects=False) as client:
            resp = None
            for api_url in api_paths:
                resp = client.get(api_url, auth=auth)
                if resp.status_code == 200:
                    break
            if resp is None or resp.status_code == 404:
                result = (False, "预置仪表盘未导入，请执行: ./deploy.sh monitoring fix-dashboard", None)
            elif resp.status_code != 200:
                result = (False, f"仪表盘检查失败 (HTTP {resp.status_code})", None)
            else:
                meta_url = (resp.json().get("meta") or {}).get("url") or ""
                route = _meta_url_to_dashboard_route(meta_url)
                if not route:
                    result = (
                        False,
                        "无法解析 Grafana 仪表盘路径，请执行: ./deploy.sh monitoring fix-dashboard",
                        None,
                    )
                else:
                    result = (True, "", route)
    except Exception as exc:
        result = (False, f"无法检查仪表盘: {exc}", None)

    _dashboard_meta_cache = (now, *result)
    return result


def resolve_dashboard_path() -> str:
    ok, _, route = _fetch_dashboard_meta()
    if ok and route:
        return f"{route}?{DASHBOARD_QUERY}"
    return f"{DASHBOARD_ROUTE_FALLBACK}?{DASHBOARD_QUERY}"


def verify_grafana_dashboard() -> tuple[bool, str]:
    ok, message, _ = _fetch_dashboard_meta()
    return ok, message


def verify_grafana_credentials() -> tuple[bool, str]:
    auth, _, _ = _grafana_admin_auth()
    if auth is None:
        return False, "未配置 GRAFANA_ADMIN_PASSWORD"
    base = resolve_grafana_upstream().rstrip("/")
    try:
        import httpx

        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0), follow_redirects=False) as client:
            user_resp = client.get(f"{base}/api/user", auth=auth)
            if user_resp.status_code == 200:
                return True, ""
            if user_resp.status_code == 401:
                return False, "Grafana 管理员密码不正确，请执行: ./deploy.sh monitoring fix-auth '你的新密码'"
            return False, f"Grafana 认证异常 (HTTP {user_resp.status_code})"
    except Exception as exc:
        return False, f"无法连接 Grafana: {exc}"


def get_integration_status(public_host: Optional[str] = None, public_origin: Optional[str] = None) -> Dict:
    grafana_url = get_grafana_url()
    loki_url = get_loki_url()

    public_grafana = _resolve_public_url(grafana_url, settings.grafana_public_url, public_host)
    public_loki = _resolve_public_url(loki_url, settings.loki_public_url, public_host)

    grafana_ok = _probe_grafana()
    loki_ok = _probe_loki()
    grafana_auth_ok, grafana_auth_message = verify_grafana_credentials() if grafana_ok else (False, "Grafana 未启动")
    grafana_dashboard_ok, grafana_dashboard_message, _ = (
        _fetch_dashboard_meta() if grafana_ok and grafana_auth_ok else (False, "", None)
    )
    dashboard_path = resolve_dashboard_path()
    dashboard_not_imported = "未导入" in (grafana_dashboard_message or "")

    # Grafana 11 Explore 使用 panes 参数（left 已废弃，会导致 Page not found）
    explore_panes = (
        '{"loki":{"datasource":"loki","queries":[{"refId":"A","expr":"{job=\\"ai-platform\\"}"}],'
        '"range":{"from":"now-1h","to":"now"}}}'
    )
    explore_path = f"/explore?orgId=1&schemaVersion=1&panes={quote(explore_panes)}"
    explore_simple_path = "/explore?orgId=1&schemaVersion=1"

    proxy_base = f"{public_origin.rstrip('/')}/api/v1/logs/grafana" if public_origin else ""
    use_proxy = settings.grafana_enabled and bool(proxy_base)

    if use_proxy:
        grafana_display = proxy_base
        dashboard_url = dashboard_path
        explore_url = explore_path
        embed_url = dashboard_path
    else:
        grafana_display = public_grafana
        dashboard_url = f"{public_grafana}{dashboard_path}"
        explore_url = f"{public_grafana}{explore_path}"
        embed_url = dashboard_url

    return {
        "enabled": settings.grafana_enabled,
        "embed_enabled": settings.grafana_embed,
        "use_proxy": use_proxy,
        "grafana_url": grafana_display,
        "loki_url": public_loki,
        "dashboard_url": dashboard_url,
        "explore_url": explore_url,
        "embed_url": explore_simple_path if dashboard_not_imported else dashboard_path,
        "grafana_online": grafana_ok,
        "loki_online": loki_ok,
        "grafana_auth_ok": grafana_auth_ok,
        "grafana_auth_message": grafana_auth_message,
        "grafana_dashboard_ok": grafana_dashboard_ok,
        "grafana_dashboard_message": grafana_dashboard_message,
        "monitoring_online": grafana_ok and loki_ok and grafana_auth_ok,
        "anonymous_access": not use_proxy,
        "startup_hint": "./deploy.sh monitoring fix-dashboard",
        "docs_path": "monitoring/README.md",
    }
