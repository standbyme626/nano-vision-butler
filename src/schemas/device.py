"""Schema models for device entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class DeviceStatus:
    id: str
    device_id: str
    camera_id: str
    device_name: str | None
    api_key_hash: str
    status: str
    ip_addr: str | None
    firmware_version: str | None
    model_version: str | None
    temperature: float | None
    cpu_load: float | None
    npu_load: float | None
    free_mem_mb: int | None
    camera_fps: int | None
    last_seen: str | None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "DeviceStatus":
        return cls(**dict(row))
