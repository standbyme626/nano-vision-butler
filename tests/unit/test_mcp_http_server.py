from __future__ import annotations

import unittest
from unittest.mock import Mock, call, patch

from src.mcp_server.http_server import build_http_server


class _FakeFastMCP:
    def __init__(
        self,
        *,
        name: str,
        host: str,
        port: int,
        streamable_http_path: str,
    ) -> None:
        self.name = name
        self.host = host
        self.port = port
        self.streamable_http_path = streamable_http_path
        self.registered_tools: dict[str, dict[str, object]] = {}

    def tool(self, *, name: str, description: str):
        def _decorator(handler):
            self.registered_tools[name] = {
                "description": description,
                "handler": handler,
            }
            return handler

        return _decorator


class MCPHttpServerTests(unittest.TestCase):
    def test_build_http_server_registers_tools_and_handlers(self) -> None:
        facade = Mock()
        facade.list_tools.return_value = [
            {"name": "take_snapshot", "description": "capture"},
            {"name": "evaluate_staleness", "description": ""},
            {"name": "", "description": "skip-invalid"},
        ]
        facade.call_tool.return_value = {"ok": True, "summary": "ok"}

        with patch("src.mcp_server.http_server.create_server", return_value=facade):
            with patch("src.mcp_server.http_server.FastMCP", new=_FakeFastMCP):
                server = build_http_server(
                    config_dir="config",
                    host="0.0.0.0",
                    port=8001,
                    streamable_http_path="/mcp",
                )

        self.assertEqual(server.name, "vision-butler-mcp")
        self.assertEqual(server.host, "0.0.0.0")
        self.assertEqual(server.port, 8001)
        self.assertEqual(server.streamable_http_path, "/mcp")
        self.assertSetEqual(set(server.registered_tools.keys()), {"take_snapshot", "evaluate_staleness"})
        self.assertEqual(server.registered_tools["evaluate_staleness"]["description"], "evaluate_staleness")

        handler = server.registered_tools["take_snapshot"]["handler"]
        self.assertTrue(callable(handler))
        result = handler(device_id="rk3566-dev-01")
        self.assertEqual(result, {"ok": True, "summary": "ok"})
        facade.call_tool.assert_called_with(name="take_snapshot", args={"device_id": "rk3566-dev-01"})

    def test_tool_handler_unwraps_kwargs_json_string(self) -> None:
        facade = Mock()
        facade.list_tools.return_value = [{"name": "describe_scene", "description": "scene"}]
        facade.call_tool.return_value = {"ok": True, "summary": "ok"}

        with patch("src.mcp_server.http_server.create_server", return_value=facade):
            with patch("src.mcp_server.http_server.FastMCP", new=_FakeFastMCP):
                server = build_http_server(
                    config_dir="config",
                    host="0.0.0.0",
                    port=8001,
                    streamable_http_path="/mcp",
                )

        handler = server.registered_tools["describe_scene"]["handler"]
        self.assertTrue(callable(handler))
        result = handler(kwargs='{"camera_id":"cam-entry-01","zone_id":"z-entry-01"}', trace_id="t-1")
        self.assertEqual(result, {"ok": True, "summary": "ok"})
        facade.call_tool.assert_called_with(
            name="describe_scene",
            args={"camera_id": "cam-entry-01", "zone_id": "z-entry-01", "trace_id": "t-1"},
        )

    def test_tool_handler_unwraps_kwargs_object(self) -> None:
        facade = Mock()
        facade.list_tools.return_value = [{"name": "get_recent_clip", "description": "clip"}]
        facade.call_tool.return_value = {"ok": True, "summary": "ok"}

        with patch("src.mcp_server.http_server.create_server", return_value=facade):
            with patch("src.mcp_server.http_server.FastMCP", new=_FakeFastMCP):
                server = build_http_server(
                    config_dir="config",
                    host="0.0.0.0",
                    port=8001,
                    streamable_http_path="/mcp",
                )

        handler = server.registered_tools["get_recent_clip"]["handler"]
        self.assertTrue(callable(handler))
        result = handler(kwargs={"camera_id": "cam-entry-01", "duration_sec": 10}, user_id="7566115125")
        self.assertEqual(result, {"ok": True, "summary": "ok"})
        facade.call_tool.assert_has_calls(
            [
                call(
                    name="get_recent_clip",
                    args={"camera_id": "cam-entry-01", "duration_sec": 10, "user_id": "7566115125"},
                )
            ]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
