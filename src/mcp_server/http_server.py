"""Streamable HTTP MCP server for Vision Butler tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from src.mcp_server.server import VisionButlerMCPServer, create_server


def _normalize_tool_args(raw_args: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw_args, dict):
        return {}

    payload = dict(raw_args)
    nested = payload.pop("kwargs", None)
    if nested is None:
        return payload

    parsed_kwargs: dict[str, Any] | None = None
    if isinstance(nested, dict):
        parsed_kwargs = nested
    elif isinstance(nested, str):
        text = nested.strip()
        if not text:
            parsed_kwargs = {}
        else:
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                parsed_kwargs = None
            else:
                if isinstance(decoded, dict):
                    parsed_kwargs = decoded

    if parsed_kwargs is None:
        payload["kwargs"] = nested
        return payload

    payload.update(parsed_kwargs)
    return payload


def _tool_handler_factory(server: VisionButlerMCPServer, tool_name: str) -> Callable[..., dict[str, Any]]:
    def _handler(**kwargs: Any) -> dict[str, Any]:
        normalized = _normalize_tool_args(kwargs or {})
        return server.call_tool(name=tool_name, args=normalized)

    _handler.__name__ = f"tool_{tool_name}"
    return _handler


def build_http_server(
    *,
    config_dir: str | Path | None,
    host: str,
    port: int,
    streamable_http_path: str,
) -> FastMCP:
    facade = create_server(config_dir=config_dir)
    mcp = FastMCP(
        name="vision-butler-mcp",
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
    )

    for spec in facade.list_tools():
        name = str(spec.get("name", "")).strip()
        if not name:
            continue
        description = str(spec.get("description", "")).strip() or name
        mcp.tool(name=name, description=description)(_tool_handler_factory(facade, name))

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Vision Butler MCP streamable-http server")
    parser.add_argument("--config-dir", default=None, help="Path to config directory")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8001, help="Bind port")
    parser.add_argument("--path", default="/mcp", help="Streamable HTTP mount path")
    args = parser.parse_args()

    server = build_http_server(
        config_dir=args.config_dir,
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
    )
    server.run("streamable-http")


if __name__ == "__main__":
    main()
