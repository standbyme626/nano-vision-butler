"""MCP prompt templates for common query intents."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.mcp_server.contracts import PromptSpec, build_error, build_success
from src.mcp_server.runtime import MCPRuntime


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class MCPPromptRegistry:
    def __init__(self, runtime: MCPRuntime):
        self._runtime = runtime
        self._prompts: dict[str, tuple[PromptSpec, str]] = {
            "scene_query": (
                PromptSpec(
                    name="scene_query",
                    description="Template for scene understanding in a camera zone.",
                    variables=["camera_id", "zone_id", "question"],
                ),
                "Camera {camera_id}, zone {zone_id}. Question: {question}. Use describe_scene and summarize uncertainty.",
            ),
            "history_query": (
                PromptSpec(
                    name="history_query",
                    description="Template for event history lookup.",
                    variables=["zone_id", "object_name", "time_range"],
                ),
                "History query for zone={zone_id}, object={object_name}, range={time_range}. Use query_recent_events then summarize key timeline.",
            ),
            "last_seen_query": (
                PromptSpec(
                    name="last_seen_query",
                    description="Template for last seen lookup.",
                    variables=["object_name", "camera_id", "zone_id"],
                ),
                "Find last seen for object={object_name}, camera={camera_id}, zone={zone_id}. Use last_seen_object and include timestamp/freshness.",
            ),
            "object_state_query": (
                PromptSpec(
                    name="object_state_query",
                    description="Template for object state reasoning.",
                    variables=["object_name", "camera_id", "zone_id"],
                ),
                "Resolve object state for {object_name} at camera={camera_id}, zone={zone_id}. Use get_object_state and explain reason_code.",
            ),
            "zone_state_query": (
                PromptSpec(
                    name="zone_state_query",
                    description="Template for zone occupancy reasoning.",
                    variables=["camera_id", "zone_id"],
                ),
                "Resolve zone state for camera={camera_id}, zone={zone_id}. Use get_zone_state and report stale/fallback signals.",
            ),
            "ocr_query": (
                PromptSpec(
                    name="ocr_query",
                    description="Template for OCR read or structured extraction.",
                    variables=["media_id", "input_uri", "field_schema"],
                ),
                "OCR request with media_id={media_id}, input_uri={input_uri}, field_schema={field_schema}. Use ocr_quick_read or ocr_extract_fields based on structure need.",
            ),
            "device_status_query": (
                PromptSpec(
                    name="device_status_query",
                    description="Template for edge device health checks.",
                    variables=["device_id"],
                ),
                "Check device status for {device_id}. Use device_status and highlight online/effective_status + telemetry.",
            ),
        }

    def list_prompts(self) -> list[dict[str, Any]]:
        return [asdict(item[0]) for item in self._prompts.values()]

    def get_prompt(self, name: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._as_text((variables or {}).get("trace_id"))
        if name not in self._prompts:
            return build_error(
                summary=f"Unknown prompt: {name}",
                source_layer="mcp.prompts",
                trace_id=trace_id,
                details={"available_prompts": sorted(self._prompts.keys())},
            )

        spec, template = self._prompts[name]
        payload = {str(k): v for k, v in (variables or {}).items()}
        rendered = template.format_map(_SafeDict(payload))
        return build_success(
            summary=f"Prompt template loaded: {name}",
            data={
                "name": spec.name,
                "description": spec.description,
                "variables": spec.variables,
                "template": template,
                "rendered": rendered,
            },
            source_layer="mcp.prompts",
            trace_id=trace_id,
        )

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None
