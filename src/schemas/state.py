"""Schema models for state-layer entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ObjectState:
    id: str
    object_name: str
    camera_id: str | None
    zone_id: str | None
    state_value: str
    state_confidence: float
    observed_at: str | None
    last_confirmed_at: str | None
    last_changed_at: str | None
    fresh_until: str | None
    is_stale: int
    evidence_count: int
    source_layer: str | None
    summary: str | None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ObjectState":
        return cls(**dict(row))


@dataclass(frozen=True)
class ZoneState:
    id: str
    camera_id: str
    zone_id: str
    state_value: str
    state_confidence: float
    observed_at: str | None
    fresh_until: str | None
    is_stale: int
    evidence_count: int
    source_layer: str | None
    summary: str | None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ZoneState":
        return cls(**dict(row))
