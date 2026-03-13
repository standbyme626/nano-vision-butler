"""Streamable HTTP MCP server for Vision Butler tools."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from src.mcp_server.server import VisionButlerMCPServer, create_server


def _tool_handler_factory(server: VisionButlerMCPServer, tool_name: str) -> Callable[..., dict[str, Any]]:
    def _handler(**kwargs: Any) -> dict[str, Any]:
        return server.call_tool(name=tool_name, args=kwargs or {})

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
