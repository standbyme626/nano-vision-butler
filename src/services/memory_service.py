"""Memory-layer write service for observations and event promotion."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from src.db.repositories.event_repo import EventRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.session import normalize_iso8601, utc_now_iso8601
from src.schemas.memory import Event, Observation
from src.settings import AppConfig


class MemoryService:
    """Persist raw observations and promote selected ones into events."""

    def __init__(
        self,
        *,
        observation_repo: ObservationRepo,
        event_repo: EventRepo,
        config: AppConfig,
    ) -> None:
        self._observation_repo = observation_repo
        self._event_repo = event_repo
        self._config = config

    def save_observation_from_payload(self, payload: dict[str, Any]) -> Observation:
        observed_at = normalize_iso8601(
            str(payload.get("observed_at") or utc_now_iso8601()),
            "payload.observed_at",
        )
        fresh_until = payload.get("fresh_until")
        if fresh_until:
            fresh_until_value = normalize_iso8601(str(fresh_until), "payload.fresh_until")
        else:
            fresh_until_value = self._compute_fresh_until(
                observed_at=observed_at,
                object_name=self._as_optional_text(payload.get("object_name")),
                object_class=self._as_optional_text(payload.get("object_class")),
            )

        observation = Observation(
            id=f"obs-{uuid4().hex[:12]}",
            device_id=self._required_text(payload.get("device_id"), "payload.device_id"),
            camera_id=self._required_text(payload.get("camera_id"), "payload.camera_id"),
            zone_id=self._as_optional_text(payload.get("zone_id")),
            object_name=self._as_optional_text(payload.get("object_name")),
            object_class=self._as_optional_text(payload.get("object_class")),
            track_id=self._as_optional_text(payload.get("track_id")),
            confidence=self._to_float(payload.get("confidence")),
            state_hint=self._as_optional_text(payload.get("state_hint")),
            observed_at=observed_at,
            fresh_until=fresh_until_value,
            source_event_id=self._as_optional_text(payload.get("source_event_id")),
            snapshot_uri=self._as_optional_text(payload.get("snapshot_uri")),
            clip_uri=self._as_optional_text(payload.get("clip_uri")),
            ocr_text=self._as_optional_text(payload.get("ocr_text")),
            visibility_scope=self._as_optional_text(payload.get("visibility_scope")) or "private",
            raw_payload_json=self._json_dumps(payload),
            created_at=None,
        )
        return self._observation_repo.save_observation(observation)

    def promote_observation_if_needed(
        self,
        payload: dict[str, Any],
        observation: Observation,
    ) -> Event | None:
        if not self.should_promote_to_event(payload):
            return None

        event_at = normalize_iso8601(
            str(payload.get("event_at") or observation.observed_at),
            "payload.event_at",
        )
        event = Event(
            id=f"evt-{uuid4().hex[:12]}",
            observation_id=observation.id,
            event_type=self._as_optional_text(payload.get("event_type")) or "observation_promoted",
            category=self._sanitize_event_category(payload.get("category")),
            importance=self._sanitize_importance(payload.get("importance")),
            camera_id=self._as_optional_text(payload.get("camera_id")) or observation.camera_id,
            zone_id=self._as_optional_text(payload.get("zone_id")) or observation.zone_id,
            object_name=self._as_optional_text(payload.get("object_name")) or observation.object_name,
            summary=self._build_event_summary(payload, observation),
            payload_json=self._json_dumps(payload),
            event_at=event_at,
            created_at=None,
        )
        return self._event_repo.save_event(event)

    def should_promote_to_event(self, payload: dict[str, Any]) -> bool:
        if self._to_bool(payload.get("force_event")):
            return True

        importance = self._sanitize_importance(payload.get("importance"))
        if importance >= 4:
            return True

        event_type = (self._as_optional_text(payload.get("event_type")) or "").lower()
        high_priority_types = {
            "security_alert",
            "intrusion_alert",
            "tamper_alert",
            "device_alert",
        }
        return event_type in high_priority_types

    def _compute_fresh_until(
        self,
        *,
        observed_at: str,
        object_name: str | None,
        object_class: str | None,
    ) -> str:
        freshness_cfg = self._config.policies.get("freshness", {})
        ttl_sec = int(freshness_cfg.get("default_ttl_sec", 300))
        overrides = freshness_cfg.get("object_overrides", {})

        for key in (object_name, object_class):
            if key and key in overrides:
                ttl_sec = int(overrides[key])
                break

        observed_dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        fresh_until_dt = observed_dt + timedelta(seconds=max(ttl_sec, 0))
        return fresh_until_dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @staticmethod
    def _sanitize_event_category(raw: Any) -> str:
        category = (str(raw).strip().lower() if raw is not None else "event") or "event"
        return category if category in {"event", "episode"} else "event"

    @staticmethod
    def _sanitize_importance(raw: Any) -> int:
        try:
            value = int(raw) if raw is not None else 3
        except (TypeError, ValueError):
            value = 3
        return min(max(value, 1), 5)

    @staticmethod
    def _build_event_summary(payload: dict[str, Any], observation: Observation) -> str:
        summary = MemoryService._as_optional_text(payload.get("summary"))
        if summary:
            return summary
        object_name = MemoryService._as_optional_text(payload.get("object_name")) or observation.object_name or "unknown_object"
        zone_id = MemoryService._as_optional_text(payload.get("zone_id")) or observation.zone_id or "unknown_zone"
        event_type = MemoryService._as_optional_text(payload.get("event_type")) or "observation_promoted"
        return f"{event_type}: {object_name} @ {zone_id}"

    @staticmethod
    def _required_text(value: Any, field_name: str) -> str:
        text = MemoryService._as_optional_text(value)
        if not text:
            raise ValueError(f"{field_name} is required")
        return text

    @staticmethod
    def _as_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(value, (int, float)):
            return value != 0
        return False

    @staticmethod
    def _json_dumps(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)

