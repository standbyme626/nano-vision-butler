"""Schema models for security/audit entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason_code: str
    message: str
    trace_id: str | None
    target_type: str | None
    target_id: str | None
    user_id: str | None
    device_id: str | None
    meta: dict[str, Any]


@dataclass(frozen=True)
class AuditLog:
    id: str
    user_id: str | None
    device_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    decision: str
    reason: str | None
    trace_id: str | None
    meta_json: str | None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "AuditLog":
        return cls(**dict(row))
