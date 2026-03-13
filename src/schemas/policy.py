"""Schema models for policy-layer entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class NotificationRule:
    id: str
    user_id: str
    rule_name: str
    trigger_type: str
    target_scope: str | None
    condition_json: str
    is_enabled: int
    cooldown_sec: int
    last_triggered_at: str | None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "NotificationRule":
        return cls(**dict(row))


@dataclass(frozen=True)
class Fact:
    id: str
    fact_key: str
    fact_value: str
    fact_type: str
    scope: str | None
    source: str | None
    confidence: float | None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Fact":
        return cls(**dict(row))
