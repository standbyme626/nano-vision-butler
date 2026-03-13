"""MCP tools wrapping existing service-layer capabilities."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from src.db.session import require_non_empty
from src.mcp_server.contracts import ToolSpec, build_error, build_success
from src.mcp_server.runtime import MCPRuntime


class MCPToolRegistry:
    def __init__(self, runtime: MCPRuntime):
        self._runtime = runtime
        self._tools: dict[str, ToolSpec] = {
            "take_snapshot": ToolSpec(
                name="take_snapshot",
                description="Capture a snapshot from an online edge device.",
                input_schema={"device_id": "str?", "camera_id": "str?", "trace_id": "str?"},
            ),
            "get_recent_clip": ToolSpec(
                name="get_recent_clip",
                description="Fetch a recent clip from an online edge device.",
                input_schema={
                    "device_id": "str?",
                    "camera_id": "str?",
                    "duration_sec": "int?",
                    "trace_id": "str?",
                },
            ),
            "describe_scene": ToolSpec(
                name="describe_scene",
                description="Summarize zone state with recent observations/events.",
                input_schema={"camera_id": "str", "zone_id": "str", "limit": "int?", "trace_id": "str?"},
            ),
            "last_seen_object": ToolSpec(
                name="last_seen_object",
                description="Lookup the last observation of a target object.",
                input_schema={
                    "object_name": "str",
                    "camera_id": "str?",
                    "zone_id": "str?",
                    "trace_id": "str?",
                },
            ),
            "get_object_state": ToolSpec(
                name="get_object_state",
                description="Read object state from state service.",
                input_schema={
                    "object_name": "str",
                    "camera_id": "str?",
                    "zone_id": "str?",
                    "trace_id": "str?",
                },
            ),
            "get_zone_state": ToolSpec(
                name="get_zone_state",
                description="Read zone state from state service.",
                input_schema={"camera_id": "str", "zone_id": "str", "trace_id": "str?"},
            ),
            "get_world_state": ToolSpec(
                name="get_world_state",
                description="Read current world snapshot from world_state_view.",
                input_schema={"camera_id": "str?", "trace_id": "str?"},
            ),
            "query_recent_events": ToolSpec(
                name="query_recent_events",
                description="Query recent events with optional filters.",
                input_schema={
                    "zone_id": "str?",
                    "object_name": "str?",
                    "start_time": "iso8601?",
                    "end_time": "iso8601?",
                    "limit": "int?",
                    "trace_id": "str?",
                },
            ),
            "evaluate_staleness": ToolSpec(
                name="evaluate_staleness",
                description="Evaluate stale/fallback decision for object query.",
                input_schema={
                    "object_name": "str",
                    "camera_id": "str?",
                    "zone_id": "str?",
                    "query_text": "str?",
                    "query_type": "str?",
                    "trace_id": "str?",
                },
            ),
            "ocr_quick_read": ToolSpec(
                name="ocr_quick_read",
                description="Run model-direct OCR quick read.",
                input_schema={"media_id": "str?", "input_uri": "str?", "trace_id": "str?"},
            ),
            "ocr_extract_fields": ToolSpec(
                name="ocr_extract_fields",
                description="Run tool-structured OCR field extraction.",
                input_schema={
                    "media_id": "str?",
                    "input_uri": "str?",
                    "field_schema": "dict|list?",
                    "trace_id": "str?",
                },
            ),
            "device_status": ToolSpec(
                name="device_status",
                description="Query device runtime status.",
                input_schema={"device_id": "str", "trace_id": "str?"},
            ),
        }
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "take_snapshot": self._take_snapshot,
            "get_recent_clip": self._get_recent_clip,
            "describe_scene": self._describe_scene,
            "last_seen_object": self._last_seen_object,
            "get_object_state": self._get_object_state,
            "get_zone_state": self._get_zone_state,
            "get_world_state": self._get_world_state,
            "query_recent_events": self._query_recent_events,
            "evaluate_staleness": self._evaluate_staleness,
            "ocr_quick_read": self._ocr_quick_read,
            "ocr_extract_fields": self._ocr_extract_fields,
            "device_status": self._device_status,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [asdict(spec) for spec in self._tools.values()]

    def call_tool(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = args or {}
        trace_id = self._as_text(payload.get("trace_id"))
        if name not in self._handlers:
            return build_error(
                summary=f"Unknown tool: {name}",
                source_layer="mcp.tools",
                trace_id=trace_id,
                details={"available_tools": sorted(self._handlers.keys())},
            )
        try:
            self._enforce_tool_access(tool_name=name, payload=payload, trace_id=trace_id)
            return self._handlers[name](payload)
        except Exception as exc:
            return build_error(
                summary=f"{name} failed: {exc}",
                source_layer="mcp.tools",
                trace_id=trace_id,
            )

    def _take_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        with self._runtime.services() as svc:
            result = svc.device_service.take_snapshot(payload)
        return build_success(
            summary=result.get("summary", "Snapshot command completed"),
            data=result.get("data", result),
            source_layer="mcp.tools.device",
            trace_id=trace_id,
        )

    def _get_recent_clip(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        with self._runtime.services() as svc:
            result = svc.device_service.get_recent_clip(payload)
        return build_success(
            summary=result.get("summary", "Recent clip command completed"),
            data=result.get("data", result),
            source_layer="mcp.tools.device",
            trace_id=trace_id,
        )

    def _describe_scene(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        camera_id = require_non_empty(self._as_text(payload.get("camera_id")), "camera_id")
        zone_id = require_non_empty(self._as_text(payload.get("zone_id")), "zone_id")
        limit = self._to_limit(payload.get("limit"), default=10, max_limit=50)

        with self._runtime.services() as svc:
            zone_state = svc.state_service.get_zone_state(camera_id=camera_id, zone_id=zone_id)
            observations = svc.observation_repo.query_recent_observations(
                camera_id=camera_id,
                zone_id=zone_id,
                limit=limit,
            )
            events = svc.event_repo.query_recent_events(
                zone_id=zone_id,
                object_name=self._as_text(payload.get("object_name")),
                start_time=self._as_text(payload.get("start_time")),
                end_time=self._as_text(payload.get("end_time")),
                limit=limit,
            )
        data = {
            "camera_id": camera_id,
            "zone_id": zone_id,
            "zone_state": zone_state,
            "observations": observations,
            "events": events,
        }
        return build_success(
            summary=f"Scene {camera_id}/{zone_id} described",
            data=data,
            source_layer="mcp.tools.scene",
            trace_id=trace_id,
            confidence=self._to_float(zone_state.get("state_confidence")),
            fresh_until=zone_state.get("fresh_until"),
            is_stale=bool(zone_state.get("is_stale", 0)),
        )

    def _last_seen_object(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        object_name = require_non_empty(self._as_text(payload.get("object_name")), "object_name")
        with self._runtime.services() as svc:
            observation = svc.observation_repo.get_last_seen(
                object_name=object_name,
                camera_id=self._as_text(payload.get("camera_id")),
                zone_id=self._as_text(payload.get("zone_id")),
            )
        if observation is None:
            raise ValueError(f"No observation found for {object_name}")
        return build_success(
            summary=f"Last seen found for {object_name}",
            data=observation,
            source_layer="mcp.tools.memory",
            trace_id=trace_id,
            confidence=observation.confidence,
            fresh_until=observation.fresh_until,
        )

    def _get_object_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        object_name = require_non_empty(self._as_text(payload.get("object_name")), "object_name")
        with self._runtime.services() as svc:
            state = svc.state_service.get_object_state(
                object_name=object_name,
                camera_id=self._as_text(payload.get("camera_id")),
                zone_id=self._as_text(payload.get("zone_id")),
            )
        return build_success(
            summary=f"Object state resolved for {object_name}",
            data=state,
            source_layer="mcp.tools.state",
            trace_id=trace_id,
            confidence=self._to_float(state.get("state_confidence")),
            fresh_until=state.get("fresh_until"),
            is_stale=bool(state.get("is_stale", 0)),
        )

    def _get_zone_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        camera_id = require_non_empty(self._as_text(payload.get("camera_id")), "camera_id")
        zone_id = require_non_empty(self._as_text(payload.get("zone_id")), "zone_id")
        with self._runtime.services() as svc:
            state = svc.state_service.get_zone_state(camera_id=camera_id, zone_id=zone_id)
        return build_success(
            summary=f"Zone state resolved for {camera_id}/{zone_id}",
            data=state,
            source_layer="mcp.tools.state",
            trace_id=trace_id,
            confidence=self._to_float(state.get("state_confidence")),
            fresh_until=state.get("fresh_until"),
            is_stale=bool(state.get("is_stale", 0)),
        )

    def _get_world_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        with self._runtime.services() as svc:
            world = svc.state_service.get_world_state(camera_id=self._as_text(payload.get("camera_id")))
        total_rows = int(world.get("summary", {}).get("total_rows", 0))
        return build_success(
            summary=f"World state loaded with {total_rows} rows",
            data=world,
            source_layer="mcp.tools.state",
            trace_id=trace_id,
        )

    def _query_recent_events(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        limit = self._to_limit(payload.get("limit"), default=20, max_limit=200)
        with self._runtime.services() as svc:
            events = svc.event_repo.query_recent_events(
                zone_id=self._as_text(payload.get("zone_id")),
                object_name=self._as_text(payload.get("object_name")),
                start_time=self._as_text(payload.get("start_time")),
                end_time=self._as_text(payload.get("end_time")),
                limit=limit,
            )
        return build_success(
            summary=f"Loaded {len(events)} recent events",
            data=events,
            source_layer="mcp.tools.memory",
            trace_id=trace_id,
        )

    def _evaluate_staleness(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        object_name = require_non_empty(self._as_text(payload.get("object_name")), "object_name")
        with self._runtime.services() as svc:
            result = svc.policy_service.evaluate_staleness_for_object(
                object_name=object_name,
                camera_id=self._as_text(payload.get("camera_id")),
                zone_id=self._as_text(payload.get("zone_id")),
                query_text=self._as_text(payload.get("query_text")),
                query_type=self._as_text(payload.get("query_type")),
            )
        return build_success(
            summary=f"Staleness evaluated for {object_name}",
            data=result,
            source_layer="mcp.tools.policy",
            trace_id=trace_id,
            fresh_until=result.get("fresh_until"),
            is_stale=bool(result.get("is_stale", False)),
            fallback_required=bool(result.get("fallback_required", False)),
        )

    def _ocr_quick_read(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        with self._runtime.services() as svc:
            media_id = self._as_text(payload.get("media_id"))
            user_id = self._as_text(payload.get("user_id"))
            if media_id and user_id:
                svc.security_guard.validate_media_visibility(
                    user_id=user_id,
                    media_id=media_id,
                    trace_id=trace_id,
                    action="media_access",
                    meta={"tool_name": "ocr_quick_read"},
                )
            result = svc.ocr_service.quick_read(payload)
        return build_success(
            summary="OCR quick read completed",
            data=result,
            source_layer="mcp.tools.ocr",
            trace_id=trace_id,
            confidence=self._to_float(result.get("confidence")),
        )

    def _ocr_extract_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        with self._runtime.services() as svc:
            media_id = self._as_text(payload.get("media_id"))
            user_id = self._as_text(payload.get("user_id"))
            if media_id and user_id:
                svc.security_guard.validate_media_visibility(
                    user_id=user_id,
                    media_id=media_id,
                    trace_id=trace_id,
                    action="media_access",
                    meta={"tool_name": "ocr_extract_fields"},
                )
            result = svc.ocr_service.extract_fields(payload)
        return build_success(
            summary="OCR field extraction completed",
            data=result,
            source_layer="mcp.tools.ocr",
            trace_id=trace_id,
            confidence=self._to_float(result.get("confidence")),
        )

    def _device_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        device_id = require_non_empty(self._as_text(payload.get("device_id")), "device_id")
        with self._runtime.services() as svc:
            status = svc.device_service.get_device_status(device_id)
        if status is None:
            raise ValueError(f"Device not found: {device_id}")
        return build_success(
            summary=f"Device status loaded for {device_id}",
            data=status,
            source_layer="mcp.tools.device",
            trace_id=trace_id,
        )

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _to_limit(value: Any, *, default: int, max_limit: int) -> int:
        try:
            parsed = int(value) if value is not None else default
        except (TypeError, ValueError):
            parsed = default
        return min(max(parsed, 1), max_limit)

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _enforce_tool_access(self, *, tool_name: str, payload: dict[str, Any], trace_id: str | None) -> None:
        with self._runtime.services() as svc:
            svc.security_guard.validate_tool_access(
                skill_name=self._as_text(payload.get("skill_name")),
                tool_name=tool_name,
                user_id=self._as_text(payload.get("user_id")),
                trace_id=trace_id,
                action="tool_access",
                meta={"tool_name": tool_name},
            )
