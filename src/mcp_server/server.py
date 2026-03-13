"""Vision Butler MCP server entrypoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.mcp_server.prompts import MCPPromptRegistry
from src.mcp_server.resources import MCPResourceRegistry
from src.mcp_server.runtime import MCPRuntime
from src.mcp_server.tools import MCPToolRegistry


class VisionButlerMCPServer:
    """In-process MCP server facade for tools/resources/prompts."""

    def __init__(
        self,
        *,
        config_dir: str | Path | None = None,
        runtime: MCPRuntime | None = None,
    ) -> None:
        self.runtime = runtime or MCPRuntime(config_dir=config_dir)
        self.tools = MCPToolRegistry(self.runtime)
        self.resources = MCPResourceRegistry(self.runtime)
        self.prompts = MCPPromptRegistry(self.runtime)

    def list_tools(self) -> list[dict[str, Any]]:
        return self.tools.list_tools()

    def call_tool(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.tools.call_tool(name=name, args=args)

    def list_resources(self) -> list[dict[str, Any]]:
        return self.resources.list_resources()

    def read_resource(self, uri: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.resources.read_resource(uri=uri, params=params)

    def list_prompts(self) -> list[dict[str, Any]]:
        return self.prompts.list_prompts()

    def get_prompt(self, name: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.prompts.get_prompt(name=name, variables=variables)

    def capabilities(self) -> dict[str, Any]:
        return {
            "tools": self.list_tools(),
            "resources": self.list_resources(),
            "prompts": self.list_prompts(),
        }


def create_server(config_dir: str | Path | None = None) -> VisionButlerMCPServer:
    return VisionButlerMCPServer(config_dir=config_dir)


def _parse_json_arg(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("JSON argument must be an object")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Vision Butler MCP server launcher")
    parser.add_argument("--config-dir", default=None, help="Path to config directory")
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("list", help="List tools/resources/prompts")

    call_tool_parser = subparsers.add_parser("call-tool", help="Call a tool by name")
    call_tool_parser.add_argument("--name", required=True)
    call_tool_parser.add_argument("--args-json", default="{}")

    read_resource_parser = subparsers.add_parser("read-resource", help="Read a resource URI")
    read_resource_parser.add_argument("--uri", required=True)
    read_resource_parser.add_argument("--params-json", default="{}")

    get_prompt_parser = subparsers.add_parser("get-prompt", help="Get a prompt template")
    get_prompt_parser.add_argument("--name", required=True)
    get_prompt_parser.add_argument("--vars-json", default="{}")

    args = parser.parse_args()
    server = create_server(config_dir=args.config_dir)

    command = args.command or "list"
    if command == "list":
        output = server.capabilities()
    elif command == "call-tool":
        output = server.call_tool(name=args.name, args=_parse_json_arg(args.args_json))
    elif command == "read-resource":
        output = server.read_resource(uri=args.uri, params=_parse_json_arg(args.params_json))
    elif command == "get-prompt":
        output = server.get_prompt(name=args.name, variables=_parse_json_arg(args.vars_json))
    else:
        raise ValueError(f"Unsupported command: {command}")

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
