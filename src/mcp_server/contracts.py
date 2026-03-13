"""Common contracts and response helpers for MCP server components."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ResourceSpec:
    uri: str
    description: str
    params_schema: dict[str, Any]


@dataclass(frozen=True)
class PromptSpec:
    name: str
    description: str
    variables: list[str]


def serialize(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, tuple):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    return value


def build_success(
    *,
    summary: str,
    data: Any,
    source_layer: str,
    trace_id: str | None = None,
    confidence: float | None = None,
    fresh_until: str | None = None,
    is_stale: bool = False,
    fallback_required: bool = False,
) -> dict[str, Any]:
    return {
        "ok": True,
        "summary": summary,
        "data": serialize(data),
        "meta": {
            "source_layer": source_layer,
            "confidence": confidence,
            "fresh_until": fresh_until,
            "is_stale": is_stale,
            "fallback_required": fallback_required,
            "trace_id": trace_id,
        },
    }


def build_error(
    *,
    summary: str,
    source_layer: str,
    trace_id: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "summary": summary,
        "data": serialize(details) if details is not None else {},
        "meta": {
            "source_layer": source_layer,
            "confidence": None,
            "fresh_until": None,
            "is_stale": False,
            "fallback_required": False,
            "trace_id": trace_id,
        },
    }
