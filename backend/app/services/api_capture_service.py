import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

SKIP_HEADER_KEYS = {
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "sec-fetch-dest",
    "sec-fetch-mode",
    "sec-fetch-site",
    "sec-fetch-user",
    ":authority",
    ":method",
    ":path",
    ":scheme",
    "priority",
    "connection",
    "accept-encoding",
    "content-length",
}


def _unescape_js_string(value: str) -> str:
    try:
        return bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\'", "'")


def _extract_quoted_string(text: str, start: int) -> Tuple[Optional[str], int]:
    idx = start
    while idx < len(text) and text[idx].isspace():
        idx += 1
    if idx >= len(text) or text[idx] not in ('"', "'"):
        return None, idx
    quote = text[idx]
    idx += 1
    chars = []
    escape = False
    while idx < len(text):
        ch = text[idx]
        if escape:
            chars.append(ch)
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == quote:
            return _unescape_js_string("".join(chars)), idx + 1
        else:
            chars.append(ch)
        idx += 1
    return None, idx


def _extract_braced_block(text: str, start: int) -> Tuple[Optional[str], int]:
    idx = start
    while idx < len(text) and text[idx].isspace():
        idx += 1
    if idx >= len(text) or text[idx] != "{":
        return None, idx
    depth = 0
    in_string = False
    quote = ""
    escape = False
    block_start = idx
    while idx < len(text):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[block_start : idx + 1], idx + 1
        idx += 1
    return None, idx


def _skip_fetch_first_arg(text: str, start: int) -> int:
    idx = start
    while idx < len(text) and text[idx].isspace():
        idx += 1
    if idx < len(text) and text[idx] in ('"', "'"):
        _, idx = _extract_quoted_string(text, idx)
        return idx
    return idx


def _extract_fetch_options(text: str) -> Optional[str]:
    match = re.search(r"fetch\s*\(", text, re.IGNORECASE)
    if not match:
        return None
    idx = _skip_fetch_first_arg(text, match.end())
    while idx < len(text) and text[idx].isspace():
        idx += 1
    if idx >= len(text) or text[idx] != ",":
        return None
    idx += 1
    block, _ = _extract_braced_block(text, idx)
    return block


def _parse_js_key_values(block: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    idx = 0
    while idx < len(block):
        key_match = re.match(r'\s*["\']?([A-Za-z0-9_-]+)["\']?\s*:\s*', block[idx:])
        if not key_match:
            idx += 1
            continue
        key = key_match.group(1)
        idx += key_match.end()
        while idx < len(block) and block[idx].isspace():
            idx += 1
        if idx >= len(block):
            break
        if block[idx] in ('"', "'"):
            value, idx = _extract_quoted_string(block, idx)
            if value is not None:
                result[key.lower()] = value
            continue
        if block[idx] == "{":
            nested, idx = _extract_braced_block(block, idx)
            if nested:
                result[key.lower()] = nested
            continue
        value_match = re.match(r"([^,}\n]+)", block[idx:])
        if value_match:
            result[key.lower()] = value_match.group(1).strip().strip(",")
            idx += value_match.end()
    return result


def _parse_headers_block(headers_block: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    inner = headers_block.strip()
    if inner.startswith("{"):
        inner = inner[1:-1]
    pairs = _parse_js_key_values("{" + inner + "}")
    for key, value in pairs.items():
        if isinstance(value, str) and not value.startswith("{"):
            headers[key] = value
    return headers


def _filter_headers(headers: Dict[str, str]) -> Dict[str, str]:
    filtered: Dict[str, str] = {}
    for key, value in headers.items():
        lower_key = key.lower()
        if lower_key in SKIP_HEADER_KEYS:
            continue
        filtered[key if key.lower() != "referer" else "Referer"] = value
    return filtered


def _split_url(url: str) -> Tuple[str, str]:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("无法解析 URL，请确认抓包数据包含完整地址")
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return base_url, path


def _normalize_curl_text(text: str) -> str:
    """合并 Charles / 终端常见的反斜杠换行续行。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    merged: List[str] = []
    buf = ""
    for line in lines:
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1].strip() + " "
            continue
        buf += stripped
        merged.append(buf.strip())
        buf = ""
    if buf.strip():
        merged.append(buf.strip())
    return " ".join(part for part in merged if part)


def _unescape_bash_ansi_c(value: str) -> str:
    """解析 curl $'...' 中的转义序列。"""
    out: List[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch != "\\" or i + 1 >= len(value):
            out.append(ch)
            i += 1
            continue
        nxt = value[i + 1]
        if nxt == "n":
            out.append("\n")
            i += 2
        elif nxt == "t":
            out.append("\t")
            i += 2
        elif nxt == "r":
            out.append("\r")
            i += 2
        elif nxt == "'":
            out.append("'")
            i += 2
        elif nxt == "\\":
            out.append("\\")
            i += 2
        elif nxt in ('"', "?"):
            out.append(nxt)
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _extract_curl_quoted_value(text: str, start: int) -> Tuple[str, int]:
    idx = start
    while idx < len(text) and text[idx].isspace():
        idx += 1
    if idx >= len(text):
        return "", idx
    if text[idx: idx + 2] == "$'":
        idx += 2
        chars: List[str] = []
        while idx < len(text):
            if text[idx] == "'" and idx > start + 2 and text[idx - 1] != "\\":
                return _unescape_bash_ansi_c("".join(chars)), idx + 1
            chars.append(text[idx])
            idx += 1
        return _unescape_bash_ansi_c("".join(chars)), idx
    if text[idx] in ('"', "'"):
        val, end = _extract_quoted_string(text, idx)
        return val or "", end
    token_match = re.match(r"(\S+)", text[idx:])
    if token_match:
        token = token_match.group(1)
        return token, idx + token_match.end()
    return "", idx


def _extract_curl_url(text: str) -> str:
    urls = re.findall(r"""['"](https?://[^'"]+)['"]""", text, re.IGNORECASE)
    if urls:
        return urls[-1].replace("\\/", "/")
    bare = re.search(r"(https?://[^\s'\"]+)", text, re.IGNORECASE)
    if bare:
        return bare.group(1).rstrip("\\")
    raise ValueError("无法从 cURL 中解析 URL")


def _extract_curl_method(text: str, has_body: bool) -> str:
    for pattern in (r"-X(?=\s|$)\s*(\w+)", r"--request(?=\s|$)\s*(\w+)"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    if has_body:
        return "POST"
    return "GET"


def _extract_curl_headers(text: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for match in re.finditer(r"-H(?=\s|$)\s+", text, re.IGNORECASE):
        value, _ = _extract_curl_quoted_value(text, match.end())
        if not value or ":" not in value:
            continue
        key, val = value.split(":", 1)
        headers[key.strip()] = val.strip()
    return headers


def _find_earliest_curl_flag(text: str, flags: Tuple[str, ...]) -> Optional[re.Match]:
    best: Optional[re.Match] = None
    for flag in flags:
        pattern = re.compile(re.escape(flag) + r"(?=\s|$)", re.IGNORECASE)
        for match in pattern.finditer(text):
            if best is None or match.start() < best.start():
                best = match
    return best


def _extract_curl_body(text: str) -> str:
    flags = ("--data-binary", "--data-raw", "--data-urlencode", "--data", "-d")
    match = _find_earliest_curl_flag(text, flags)
    if not match:
        return ""
    body, _ = _extract_curl_quoted_value(text, match.end())
    return body


def _looks_like_raw_http(text: str) -> bool:
    first = text.strip().split("\n", 1)[0].strip()
    return bool(
        re.match(
            r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|CONNECT)\s+\S+\s+HTTP/\d(?:\.\d)?$",
            first,
            re.IGNORECASE,
        )
    )


def _build_capture_result(
    *,
    method: str,
    path: str,
    base_url: str,
    headers: Dict[str, str],
    body: str,
    case_name: Optional[str],
    source: str,
    full_url: str,
) -> Dict[str, Any]:
    headers = _filter_headers(headers)
    name = _build_case_name(method, path, case_name)
    return {
        "name": name,
        "method": method.upper(),
        "path": path,
        "base_url": base_url,
        "headers": json.dumps(headers, ensure_ascii=False, indent=2) if headers else "",
        "body": body,
        "assertions": json.dumps([{"type": "status_code", "expected": 200}], ensure_ascii=False),
        "source": source,
        "full_url": full_url,
    }


def _build_case_name(method: str, path: str, custom_name: Optional[str] = None) -> str:
    if custom_name and custom_name.strip():
        return custom_name.strip()
    pathname = path.split("?")[0] or "/"
    return f"{method.upper()} {pathname}"


def parse_raw_http_capture(raw_text: str, case_name: Optional[str] = None) -> Dict[str, Any]:
    """解析 Charles「Copy Request」等原始 HTTP 请求文本。"""
    text = raw_text.strip().replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        raise ValueError("抓包内容不能为空")

    parts = re.split(r"\n\s*\n", text, maxsplit=1)
    head_block = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    lines = [line.strip("\r") for line in head_block.split("\n") if line.strip()]
    if not lines:
        raise ValueError("未识别到 HTTP 请求行")

    request_match = re.match(
        r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\S+)\s+HTTP/\d(?:\.\d)?$",
        lines[0],
        re.IGNORECASE,
    )
    if not request_match:
        raise ValueError("未识别到 Charles Copy Request 格式，请粘贴完整 HTTP 请求头")

    method = request_match.group(1).upper()
    target = request_match.group(2)
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()

    if target.lower().startswith("http://") or target.lower().startswith("https://"):
        base_url, path = _split_url(target)
        full_url = target
    else:
        host = headers.get("Host") or headers.get("host")
        if not host:
            raise ValueError("相对路径请求缺少 Host 头，无法解析 Base URL")
        host_only = host.split(":")[0] if ":" in host else host
        scheme = "https"
        if "X-Forwarded-Proto" in headers:
            scheme = headers["X-Forwarded-Proto"].split(",")[0].strip().lower() or "https"
        base_url = f"{scheme}://{host_only}"
        path = target if target.startswith("/") else f"/{target}"
        full_url = f"{base_url}{path}"

    return _build_capture_result(
        method=method,
        path=path,
        base_url=base_url,
        headers=headers,
        body=body.strip(),
        case_name=case_name,
        source="charles_raw",
        full_url=full_url,
    )


def parse_fetch_capture(raw_text: str, case_name: Optional[str] = None) -> Dict[str, Any]:
    text = raw_text.strip().rstrip(";")
    if not text:
        raise ValueError("抓包内容不能为空")

    url_match = re.search(r'fetch\s*\(\s*(["\'])(.+?)\1', text, re.IGNORECASE | re.DOTALL)
    if not url_match:
        raise ValueError("未识别到 fetch 抓包格式，请粘贴浏览器 Copy as fetch 内容")

    url = _unescape_js_string(url_match.group(2))
    base_url, path = _split_url(url)
    options = _extract_fetch_options(text) or "{}"
    options_map = _parse_js_key_values(options)

    method = (options_map.get("method") or "GET").strip().strip('"').strip("'").upper()
    body = options_map.get("body", "")
    if body.startswith('"') and body.endswith('"'):
        body = body[1:-1]

    headers: Dict[str, str] = {}
    headers_raw = options_map.get("headers")
    if headers_raw:
        headers = _parse_headers_block(headers_raw)

    referrer = options_map.get("referrer")
    if referrer and referrer not in ('""', "''", ""):
        ref = referrer.strip().strip('"').strip("'")
        if ref:
            headers.setdefault("Referer", ref)

    return _build_capture_result(
        method=method,
        path=path,
        base_url=base_url,
        headers=headers,
        body=body,
        case_name=case_name,
        source="fetch",
        full_url=url,
    )


def parse_curl_capture(raw_text: str, case_name: Optional[str] = None) -> Dict[str, Any]:
    text = _normalize_curl_text(raw_text.strip())
    if not re.search(r"\bcurl\b", text, re.IGNORECASE):
        raise ValueError("未识别到 cURL 格式")

    url = _extract_curl_url(text)
    base_url, path = _split_url(url)
    body = _extract_curl_body(text)
    method = _extract_curl_method(text, bool(body))
    headers = _extract_curl_headers(text)

    return _build_capture_result(
        method=method,
        path=path,
        base_url=base_url,
        headers=headers,
        body=body,
        case_name=case_name,
        source="charles_curl",
        full_url=url,
    )


def parse_capture_text(raw_text: str, case_name: Optional[str] = None) -> Dict[str, Any]:
    text = raw_text.strip()
    if not text:
        raise ValueError("抓包内容不能为空")
    if _looks_like_raw_http(text):
        return parse_raw_http_capture(text, case_name)
    normalized = _normalize_curl_text(text)
    if re.search(r"\bcurl\b", normalized, re.IGNORECASE):
        return parse_curl_capture(text, case_name)
    return parse_fetch_capture(text, case_name)


def parse_multiple_captures(raw_text: str) -> List[Dict[str, Any]]:
    text = raw_text.strip()
    if not text:
        raise ValueError("抓包内容不能为空")

    if _looks_like_raw_http(text):
        return [parse_raw_http_capture(text)]

    blocks = re.split(r"\n(?=fetch\s*\()", text)
    if len(blocks) == 1 and re.search(r"\bcurl\b", _normalize_curl_text(blocks[0]), re.IGNORECASE):
        return [parse_curl_capture(blocks[0])]

    results: List[Dict[str, Any]] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if re.search(r"\bcurl\b", _normalize_curl_text(block), re.IGNORECASE):
            results.append(parse_curl_capture(block))
        elif "fetch" in block.lower():
            results.append(parse_fetch_capture(block))
        elif _looks_like_raw_http(block):
            results.append(parse_raw_http_capture(block))
    if not results:
        raise ValueError("未识别到可导入的抓包数据，支持 fetch / cURL / Charles Copy Request")
    return results
