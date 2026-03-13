"""Schema models for memory-layer entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Observation:
    id: str
    device_id: str
    camera_id: str
    zone_id: str | None
    object_name: str | None
    object_class: str | None
    track_id: str | None
    confidence: float | None
    state_hint: str | None
    observed_at: str
    fresh_until: str | None
    source_event_id: str | None
    snapshot_uri: str | None
    clip_uri: str | None
    ocr_text: str | None
    visibility_scope: str | None
    raw_payload_json: str | None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Observation":
        return cls(**dict(row))


@dataclass(frozen=True)
class Event:
    id: str
    observation_id: str | None
    event_type: str
    category: str
    importance: int
    camera_id: str | None
    zone_id: str | None
    object_name: str | None
    summary: str
    payload_json: str | None
    event_at: str
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Event":
        return cls(**dict(row))


@dataclass(frozen=True)
class MediaItem:
    id: str
    owner_type: str
    owner_id: str
    media_type: str
    uri: str
    local_path: str
    mime_type: str | None
    duration_sec: int | None
    width: int | None
    height: int | None
    visibility_scope: str | None
    sha256: str | None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "MediaItem":
        return cls(**dict(row))


@dataclass(frozen=True)
class OcrResult:
    id: str
    source_media_id: str
    source_observation_id: str | None
    ocr_mode: str
    raw_text: str | None
    fields_json: str | None
    boxes_json: str | None
    language: str | None
    confidence: float | None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "OcrResult":
        return cls(**dict(row))
