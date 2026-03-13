"""State service for object/zone/world state query and refresh."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from src.db.repositories.observation_repo import ObservationRepo
from src.db.repositories.state_repo import StateRepo
from src.db.session import require_non_empty, utc_now_iso8601
from src.schemas.memory import Observation
from src.schemas.state import ObjectState, ZoneState
from src.settings import AppConfig


class StateService:
    """Read and refresh current state snapshots based on repository data."""

    _OBJECT_VALUES = {"present", "absent", "unknown"}
    _ZONE_VALUES = {"occupied", "empty", "likely_occupied", "unknown"}

    def __init__(
        self,
        *,
        state_repo: StateRepo,
        observation_repo: ObservationRepo,
        conn: sqlite3.Connection,
        config: AppConfig,
    ) -> None:
        self._state_repo = state_repo
        self._observation_repo = observation_repo
        self._conn = conn
        self._config = config

    def get_object_state(
        self,
        *,
        object_name: str,
        camera_id: str | None = None,
        zone_id: str | None = None,
    ) -> dict[str, Any]:
        require_non_empty(object_name, "object_name")
        existing = self._state_repo.get_object_state(object_name=object_name, camera_id=camera_id, zone_id=zone_id)
        if existing is not None:
            return self._serialize_object_state(existing, reason_code="state_row_found")

        refreshed, reason_code = self.refresh_object_state(
            object_name=object_name,
            camera_id=camera_id,
            zone_id=zone_id,
        )
        return self._serialize_object_state(refreshed, reason_code=reason_code)

    def get_zone_state(self, *, camera_id: str, zone_id: str) -> dict[str, Any]:
        require_non_empty(camera_id, "camera_id")
        require_non_empty(zone_id, "zone_id")
        existing = self._state_repo.get_zone_state(camera_id=camera_id, zone_id=zone_id)
        if existing is not None:
            return self._serialize_zone_state(existing, reason_code="state_row_found")

        refreshed, reason_code = self.refresh_zone_state(camera_id=camera_id, zone_id=zone_id)
        return self._serialize_zone_state(refreshed, reason_code=reason_code)

    def get_world_state(self, camera_id: str | None = None) -> dict[str, Any]:
        rows = self._conn.execute(
            """
            SELECT *
            FROM world_state_view
            WHERE (? IS NULL OR camera_id = ?)
            ORDER BY camera_id, zone_id
            """,
            (camera_id, camera_id),
        ).fetchall()
        items = [dict(row) for row in rows]
        status_counts: dict[str, int] = {}
        zone_counts: dict[str, int] = {}
        for item in items:
            status = str(item.get("device_status") or "unknown")
            zone_value = str(item.get("zone_state_value") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            zone_counts[zone_value] = zone_counts.get(zone_value, 0) + 1

        return {
            "items": items,
            "summary": {
                "total_rows": len(items),
                "device_status_counts": status_counts,
                "zone_state_counts": zone_counts,
                "generated_at": utc_now_iso8601(),
            },
            "reason_code": "world_state_view_snapshot",
        }

    def refresh_object_state(
        self,
        *,
        object_name: str,
        camera_id: str | None = None,
        zone_id: str | None = None,
    ) -> tuple[ObjectState, str]:
        require_non_empty(object_name, "object_name")
        now_iso = utc_now_iso8601()
        last_seen = self._observation_repo.get_last_seen(
            object_name=object_name,
            camera_id=camera_id,
            zone_id=zone_id,
        )
        if last_seen is None:
            unknown_state = ObjectState(
                id=f"os-{uuid4().hex[:12]}",
                object_name=object_name,
                camera_id=camera_id,
                zone_id=zone_id,
                state_value="unknown",
                state_confidence=0.0,
                observed_at=None,
                last_confirmed_at=None,
                last_changed_at=None,
                fresh_until=now_iso,
                is_stale=1,
                evidence_count=0,
                source_layer="state_service.refresh",
                summary="No observation evidence for object",
                updated_at=now_iso,
            )
            return self._state_repo.save_object_state(unknown_state), "no_observation_evidence"

        inferred_value = self._infer_object_state_value(last_seen)
        confidence = self._infer_object_confidence(last_seen, inferred_value)
        fresh_until = last_seen.fresh_until or self._compute_fresh_until(last_seen)
        is_stale = int(self._is_stale(fresh_until))
        summary = f"Derived from latest observation {last_seen.id}"
        derived = ObjectState(
            id=f"os-{uuid4().hex[:12]}",
            object_name=object_name,
            camera_id=last_seen.camera_id,
            zone_id=last_seen.zone_id,
            state_value=inferred_value,
            state_confidence=confidence,
            observed_at=last_seen.observed_at,
            last_confirmed_at=last_seen.observed_at if inferred_value == "present" else None,
            last_changed_at=last_seen.observed_at,
            fresh_until=fresh_until,
            is_stale=is_stale,
            evidence_count=1,
            source_layer="state_service.refresh",
            summary=summary,
            updated_at=now_iso,
        )
        return self._state_repo.save_object_state(derived), "refreshed_from_observation"

    def refresh_zone_state(
        self,
        *,
        camera_id: str,
        zone_id: str,
    ) -> tuple[ZoneState, str]:
        require_non_empty(camera_id, "camera_id")
        require_non_empty(zone_id, "zone_id")
        now_iso = utc_now_iso8601()
        observations = self._observation_repo.list_recent_by_zone(camera_id=camera_id, zone_id=zone_id, limit=20)
        if not observations:
            unknown_zone = ZoneState(
                id=f"zs-{uuid4().hex[:12]}",
                camera_id=camera_id,
                zone_id=zone_id,
                state_value="unknown",
                state_confidence=0.0,
                observed_at=None,
                fresh_until=now_iso,
                is_stale=1,
                evidence_count=0,
                source_layer="state_service.refresh",
                summary="No observations in zone",
                updated_at=now_iso,
            )
            return self._state_repo.save_zone_state(unknown_zone), "no_zone_observations"

        present_count = 0
        absent_count = 0
        max_confidence = 0.0
        for obs in observations:
            inferred = self._infer_object_state_value(obs)
            if inferred == "present":
                present_count += 1
            elif inferred == "absent":
                absent_count += 1
            max_confidence = max(max_confidence, float(obs.confidence or 0.0))

        if present_count >= 2:
            zone_value = "occupied"
        elif present_count == 1:
            zone_value = "likely_occupied"
        elif absent_count > 0:
            zone_value = "empty"
        else:
            zone_value = "unknown"

        latest = observations[0]
        fresh_until = latest.fresh_until or self._compute_fresh_until(latest)
        zone_confidence = max_confidence if max_confidence > 0 else 0.5 if zone_value != "unknown" else 0.0
        derived_zone = ZoneState(
            id=f"zs-{uuid4().hex[:12]}",
            camera_id=camera_id,
            zone_id=zone_id,
            state_value=zone_value,
            state_confidence=zone_confidence,
            observed_at=latest.observed_at,
            fresh_until=fresh_until,
            is_stale=int(self._is_stale(fresh_until)),
            evidence_count=len(observations),
            source_layer="state_service.refresh",
            summary=f"Derived from {len(observations)} recent observations",
            updated_at=now_iso,
        )
        return self._state_repo.save_zone_state(derived_zone), "refreshed_from_zone_observations"

    def _infer_object_state_value(self, observation: Observation) -> str:
        hint = (observation.state_hint or "").strip().lower()
        if hint in self._OBJECT_VALUES:
            return hint
        confidence = float(observation.confidence or 0.0)
        if confidence >= 0.5:
            return "present"
        if confidence <= 0.15:
            return "absent"
        return "unknown"

    @staticmethod
    def _infer_object_confidence(observation: Observation, state_value: str) -> float:
        if observation.confidence is not None:
            return float(max(min(observation.confidence, 1.0), 0.0))
        if state_value == "present":
            return 0.6
        if state_value == "absent":
            return 0.5
        return 0.0

    def _compute_fresh_until(self, observation: Observation) -> str:
        freshness_cfg = self._config.policies.get("freshness", {})
        ttl_sec = int(freshness_cfg.get("default_ttl_sec", 300))
        overrides = freshness_cfg.get("object_overrides", {})
        for key in (observation.object_name, observation.object_class):
            if key and key in overrides:
                ttl_sec = int(overrides[key])
                break
        observed_dt = datetime.fromisoformat(observation.observed_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        return (observed_dt + timedelta(seconds=max(ttl_sec, 0))).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )

    @staticmethod
    def _is_stale(fresh_until: str) -> bool:
        now = datetime.now(tz=timezone.utc)
        fresh_until_dt = datetime.fromisoformat(fresh_until.replace("Z", "+00:00")).astimezone(timezone.utc)
        return now > fresh_until_dt

    def _serialize_object_state(self, state: ObjectState, *, reason_code: str) -> dict[str, Any]:
        payload = {
            "id": state.id,
            "object_name": state.object_name,
            "camera_id": state.camera_id,
            "zone_id": state.zone_id,
            "state_value": state.state_value if state.state_value in self._OBJECT_VALUES else "unknown",
            "state_confidence": state.state_confidence,
            "observed_at": state.observed_at,
            "last_confirmed_at": state.last_confirmed_at,
            "last_changed_at": state.last_changed_at,
            "fresh_until": state.fresh_until,
            "is_stale": bool(state.is_stale),
            "evidence_count": state.evidence_count,
            "source_layer": state.source_layer,
            "summary": state.summary,
            "updated_at": state.updated_at,
            "reason_code": reason_code,
        }
        return payload

    def _serialize_zone_state(self, state: ZoneState, *, reason_code: str) -> dict[str, Any]:
        payload = {
            "id": state.id,
            "camera_id": state.camera_id,
            "zone_id": state.zone_id,
            "state_value": state.state_value if state.state_value in self._ZONE_VALUES else "unknown",
            "state_confidence": state.state_confidence,
            "observed_at": state.observed_at,
            "fresh_until": state.fresh_until,
            "is_stale": bool(state.is_stale),
            "evidence_count": state.evidence_count,
            "source_layer": state.source_layer,
            "summary": state.summary,
            "updated_at": state.updated_at,
            "reason_code": reason_code,
        }
        return payload

