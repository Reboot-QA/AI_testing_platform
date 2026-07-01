from typing import Dict, Optional
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import settings


def _build_url(base: str, port: int, default_host: str = "127.0.0.1") -> str:
    value = (base or "").strip().rstrip("/")
    if value:
        return value
    return f"http://{default_host}:{port}"


def _apply_public_host(url: str, public_host: Optional[str]) -> str:
    if not public_host or public_host in {"127.0.0.1", "localhost"}:
        return url
    return url.replace("127.0.0.1", public_host).replace("localhost", public_host)


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


def get_loki_url() -> str:
    return _build_url(settings.loki_url, settings.loki_port)


def get_integration_status(public_host: Optional[str] = None) -> Dict:
    grafana_url = get_grafana_url()
    loki_url = get_loki_url()

    public_grafana = _resolve_public_url(grafana_url, settings.grafana_public_url, public_host)
    public_loki = _resolve_public_url(loki_url, settings.loki_public_url, public_host)

    dashboard_url = f"{public_grafana}/d/ai-platform-logs/ai-platform-logs?orgId=1&refresh=10s"
    explore_left = (
        '{"datasource":"loki","queries":[{"expr":"{job=\\"ai-platform\\"}","refId":"A"}],'
        '"range":{"from":"now-1h","to":"now"}}'
    )
    explore_url = f"{public_grafana}/explore?orgId=1&left={quote(explore_left)}"
    embed_url = f"{dashboard_url}&kiosk"

    grafana_ok = _probe(f"{grafana_url}/api/health")
    loki_ok = _probe(f"{loki_url}/ready")

    return {
        "enabled": settings.grafana_enabled,
        "embed_enabled": settings.grafana_embed,
        "grafana_url": public_grafana,
        "loki_url": public_loki,
        "dashboard_url": dashboard_url,
        "explore_url": explore_url,
        "embed_url": embed_url,
        "grafana_online": grafana_ok,
        "loki_online": loki_ok,
        "monitoring_online": grafana_ok and loki_ok,
        "startup_hint": "./deploy.sh monitoring start",
        "docs_path": "monitoring/README.md",
    }
