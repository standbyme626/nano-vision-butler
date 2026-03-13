"""HTTP client for posting edge payloads to backend device routes."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request


class BackendApiClient:
    """Minimal JSON client for /device/ingest/event and /device/heartbeat."""

    def __init__(self, *, base_url: str, timeout_sec: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_sec = timeout_sec

    def post_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post_json("/device/ingest/event", payload)

    def post_heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post_json("/device/heartbeat", payload)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = parse.urljoin(f"{self._base_url}/", path.lstrip("/"))
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout_sec) as resp:
                text = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "status_code": exc.code,
                "error": "http_error",
                "detail": text,
            }
        except error.URLError as exc:
            return {
                "ok": False,
                "error": "network_error",
                "detail": str(exc.reason),
            }

        try:
            parsed: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"ok": False, "error": "invalid_json", "detail": text}
        return parsed
