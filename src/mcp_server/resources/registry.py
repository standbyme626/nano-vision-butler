"""MCP resources for read-only context loading."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.mcp_server.contracts import ResourceSpec, build_error, build_success
from src.mcp_server.runtime import MCPRuntime


class MCPResourceRegistry:
    def __init__(self, runtime: MCPRuntime):
        self._runtime = runtime
        self._resources: dict[str, ResourceSpec] = {
            "resource://memory/observations": ResourceSpec(
                uri="resource://memory/observations",
                description="Recent observations with optional filters.",
                params_schema={"camera_id": "str?", "zone_id": "str?", "object_name": "str?", "limit": "int?"},
            ),
            "resource://memory/events": ResourceSpec(
                uri="resource://memory/events",
                description="Recent events with optional filters.",
                params_schema={
                    "zone_id": "str?",
                    "object_name": "str?",
                    "start_time": "iso8601?",
                    "end_time": "iso8601?",
                    "limit": "int?",
                },
            ),
            "resource://memory/object_states": ResourceSpec(
                uri="resource://memory/object_states",
                description="Current object state snapshots.",
                params_schema={"camera_id": "str?", "zone_id": "str?", "limit": "int?"},
            ),
            "resource://memory/zone_states": ResourceSpec(
                uri="resource://memory/zone_states",
                description="Current zone state snapshots.",
                params_schema={"camera_id": "str?", "limit": "int?"},
            ),
            "resource://policy/freshness": ResourceSpec(
                uri="resource://policy/freshness",
                description="Configured freshness policy.",
                params_schema={},
            ),
            "resource://devices/status": ResourceSpec(
                uri="resource://devices/status",
                description="Current device status rows.",
                params_schema={"status": "str?", "camera_id": "str?", "limit": "int?"},
            ),
        }

    def list_resources(self) -> list[dict[str, Any]]:
        return [asdict(spec) for spec in self._resources.values()]

    def read_resource(self, uri: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = params or {}
        trace_id = self._as_text(payload.get("trace_id"))
        if uri not in self._resources:
            return build_error(
                summary=f"Unknown resource: {uri}",
                source_layer="mcp.resources",
                trace_id=trace_id,
                details={"available_resources": sorted(self._resources.keys())},
            )
        try:
            self._enforce_resource_access(uri=uri, payload=payload, trace_id=trace_id)
            if uri == "resource://memory/observations":
                return self._observations(payload)
            if uri == "resource://memory/events":
                return self._events(payload)
            if uri == "resource://memory/object_states":
                return self._object_states(payload)
            if uri == "resource://memory/zone_states":
                return self._zone_states(payload)
            if uri == "resource://policy/freshness":
                return self._freshness_policy(payload)
            if uri == "resource://devices/status":
                return self._devices_status(payload)
            return build_error(
                summary=f"Resource handler missing: {uri}",
                source_layer="mcp.resources",
                trace_id=trace_id,
            )
        except Exception as exc:
            return build_error(
                summary=f"Failed reading {uri}: {exc}",
                source_layer="mcp.resources",
                trace_id=trace_id,
            )

    def _observations(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        limit = self._to_limit(payload.get("limit"), default=20, max_limit=200)
        with self._runtime.services() as svc:
            items = svc.observation_repo.query_recent_observations(
                camera_id=self._as_text(payload.get("camera_id")),
                zone_id=self._as_text(payload.get("zone_id")),
                object_name=self._as_text(payload.get("object_name")),
                limit=limit,
            )
        return build_success(
            summary=f"Loaded {len(items)} observations",
            data={"items": items},
            source_layer="mcp.resources.memory",
            trace_id=trace_id,
        )

    def _events(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        limit = self._to_limit(payload.get("limit"), default=20, max_limit=200)
        with self._runtime.services() as svc:
            items = svc.event_repo.query_recent_events(
                zone_id=self._as_text(payload.get("zone_id")),
                object_name=self._as_text(payload.get("object_name")),
                start_time=self._as_text(payload.get("start_time")),
                end_time=self._as_text(payload.get("end_time")),
                limit=limit,
            )
        return build_success(
            summary=f"Loaded {len(items)} events",
            data={"items": items},
            source_layer="mcp.resources.memory",
            trace_id=trace_id,
        )

    def _object_states(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        limit = self._to_limit(payload.get("limit"), default=50, max_limit=200)
        with self._runtime.services() as svc:
            items = svc.state_repo.list_object_states(
                camera_id=self._as_text(payload.get("camera_id")),
                zone_id=self._as_text(payload.get("zone_id")),
                limit=limit,
            )
        return build_success(
            summary=f"Loaded {len(items)} object states",
            data={"items": items},
            source_layer="mcp.resources.state",
            trace_id=trace_id,
        )

    def _zone_states(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        limit = self._to_limit(payload.get("limit"), default=50, max_limit=200)
        with self._runtime.services() as svc:
            items = svc.state_repo.list_zone_states(
                camera_id=self._as_text(payload.get("camera_id")),
                limit=limit,
            )
        return build_success(
            summary=f"Loaded {len(items)} zone states",
            data={"items": items},
            source_layer="mcp.resources.state",
            trace_id=trace_id,
        )

    def _freshness_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        freshness = self._runtime.config.policies.get("freshness", {})
        return build_success(
            summary="Loaded freshness policy",
            data=freshness,
            source_layer="mcp.resources.policy",
            trace_id=trace_id,
        )

    def _devices_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._as_text(payload.get("trace_id"))
        limit = self._to_limit(payload.get("limit"), default=50, max_limit=200)
        with self._runtime.services() as svc:
            items = svc.device_repo.list_devices(
                status=self._as_text(payload.get("status")),
                camera_id=self._as_text(payload.get("camera_id")),
                limit=limit,
            )
        return build_success(
            summary=f"Loaded {len(items)} devices",
            data={"items": items},
            source_layer="mcp.resources.device",
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

    def _enforce_resource_access(self, *, uri: str, payload: dict[str, Any], trace_id: str | None) -> None:
        with self._runtime.services() as svc:
            svc.security_guard.validate_resource_access(
                skill_name=self._as_text(payload.get("skill_name")),
                resource_uri=uri,
                user_id=self._as_text(payload.get("user_id")),
                trace_id=trace_id,
                action="resource_access",
                meta={"resource_uri": uri},
            )
