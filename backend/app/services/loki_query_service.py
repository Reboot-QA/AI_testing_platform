import time
from typing import Dict, List, Optional

import httpx
from fastapi import HTTPException

from app.services.log_integration_service import resolve_loki_upstream

DEFAULT_QUERY = '{job="ai-platform"}'
DEFAULT_LIMIT = 200


def _parse_loki_response(payload: dict) -> List[Dict]:
    lines: List[Dict] = []
    data = payload.get("data", {})
    result = data.get("result", [])
    for stream in result:
        labels = stream.get("stream", {})
        source = labels.get("source") or labels.get("job") or "unknown"
        level = labels.get("level") or "INFO"
        for value in stream.get("values", []):
            if not isinstance(value, (list, tuple)) or len(value) < 2:
                continue
            ts_ns, text = value[0], value[1]
            try:
                ts_ms = int(ts_ns) // 1_000_000
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_ms / 1000))
            except (TypeError, ValueError):
                timestamp = None
            lines.append(
                {
                    "timestamp": timestamp,
                    "source": source,
                    "level": str(level).upper(),
                    "text": str(text),
                }
            )
    lines.sort(key=lambda item: item.get("timestamp") or "")
    return lines


async def query_loki(
    expr: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    hours: int = 6,
) -> Dict:
    query = (expr or DEFAULT_QUERY).strip() or DEFAULT_QUERY
    limit = max(1, min(limit, 1000))
    hours = max(1, min(hours, 168))

    end_ns = int(time.time() * 1_000_000_000)
    start_ns = end_ns - hours * 3600 * 1_000_000_000
    upstream = resolve_loki_upstream().rstrip("/")
    url = f"{upstream}/loki/api/v1/query_range"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = await client.get(
                url,
                params={
                    "query": query,
                    "limit": limit,
                    "start": start_ns,
                    "end": end_ns,
                    "direction": "backward",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"无法连接 Loki: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Loki 查询失败: {response.text[:300]}")

    payload = response.json()
    if payload.get("status") != "success":
        raise HTTPException(status_code=502, detail="Loki 返回异常结果")

    lines = _parse_loki_response(payload)
    return {
        "query": query,
        "lines": lines,
        "total": len(lines),
        "hours": hours,
    }
