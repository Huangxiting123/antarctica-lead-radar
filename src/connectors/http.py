from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ConnectorError(RuntimeError):
    pass


def request_json(
    url: str,
    *,
    query: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    if query:
        separator = "&" if "?" in url else "?"
        url += separator + urllib.parse.urlencode(query)
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    combined_headers = {
        "Accept": "application/json",
        "User-Agent": "OmniMediaIntelligenceRadar/0.2 (+local desktop app)",
        **(headers or {}),
    }
    if data is not None:
        combined_headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=body, headers=combined_headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise ConnectorError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ConnectorError(f"网络连接失败：{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ConnectorError("平台返回了无法解析的数据") from exc
