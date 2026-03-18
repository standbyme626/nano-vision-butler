"""Policy service for recency classification and staleness decisions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.db.repositories.device_repo import DeviceRepo
from src.db.session import normalize_iso8601, require_non_empty, utc_now_iso8601
from src.services.state_service import StateService
from src.settings import AppConfig


class PolicyService:
    """Evaluate staleness/fallback policies without writing state."""

    def __init__(
        self,
        *,
        state_service: StateService,
        device_repo: DeviceRepo,
        config: AppConfig,
    ) -> None:
        self._state_service = state_service
        self._device_repo = device_repo
        self._config = config

    def classify_query_recency(self, *, query_text: str | None = None, query_type: str | None = None) -> str:
        if query_type:
            token = query_type.strip().lower()
            if token in {"realtime", "real_time", "live", "current", "now"}:
                return "realtime"
            if token in {"historical", "history", "past"}:
                return "historical"
            if token in {"recent", "latest"}:
                return "recent"

        text = (query_text or "").strip().lower()
        if any(word in text for word in ("现在", "刚刚", "right now", "currently", "still")):
            return "realtime"
        if any(word in text for word in ("昨天", "上周", "history", "historical", "过去")):
            return "historical"
        return "recent"

    def evaluate_staleness(
        self,
        *,
        query_recency_class: str,
        fresh_until: str | None,
        device_status: str | None,
        now: str | None = None,
    ) -> dict[str, Any]:
        recency_class = query_recency_class if query_recency_class in {"realtime", "recent", "historical"} else "recent"
        evaluated_at = normalize_iso8601(now, "now") if now else utc_now_iso8601()
        now_dt = datetime.fromisoformat(evaluated_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        grace_sec = int(self._config.policies.get("stale", {}).get("stale_grace_sec", 0))
        fallback_enabled = bool(self._config.policies.get("fallback", {}).get("enable_recheck_snapshot", False))

        fresh_dt: datetime | None = None
        if fresh_until:
            normalized_fresh_until = normalize_iso8601(fresh_until, "fresh_until")
            fresh_dt = datetime.fromisoformat(normalized_fresh_until.replace("Z", "+00:00")).astimezone(timezone.utc)
            is_stale = now_dt > (fresh_dt + timedelta(seconds=grace_sec))
        else:
            normalized_fresh_until = None
            is_stale = True

        device = (device_status or "unknown").strip().lower() or "unknown"
        fallback_required = False
        reason_code = "fresh"

        if normalized_fresh_until is None:
            reason_code = "fresh_until_missing"
        elif is_stale and recency_class == "historical":
            reason_code = "stale_but_historical_allowed"
        elif is_stale and device == "offline":
            reason_code = "device_offline_cannot_recheck"
        elif is_stale and recency_class in {"realtime", "recent"} and fallback_enabled:
            fallback_required = True
            reason_code = "stale_requires_recheck"
        elif is_stale:
            reason_code = "stale_no_recheck"
        elif device == "degraded" and recency_class == "realtime" and fallback_enabled:
            fallback_required = True
            reason_code = "device_degraded_recheck_recommended"
        elif device == "degraded":
            reason_code = "device_degraded"

        freshness_level = self._classify_freshness_level(
            fresh_dt=fresh_dt,
            now_dt=now_dt,
            is_stale=is_stale,
            grace_sec=grace_sec,
        )
        seconds_to_fresh_until = int((fresh_dt - now_dt).total_seconds()) if fresh_dt is not None else None

        return {
            "fresh_until": normalized_fresh_until,
            "is_stale": is_stale,
            "freshness_level": freshness_level,
            "seconds_to_fresh_until": seconds_to_fresh_until,
            "fallback_required": fallback_required,
            "reason_code": reason_code,
            "recency_class": recency_class,
            "device_status": device,
            "grace_sec": grace_sec,
            "evaluated_at": evaluated_at,
        }

    def evaluate_staleness_for_object(
        self,
        *,
        object_name: str,
        camera_id: str | None = None,
        zone_id: str | None = None,
        query_text: str | None = None,
        query_type: str | None = None,
        now: str | None = None,
    ) -> dict[str, Any]:
        require_non_empty(object_name, "object_name")
        state = self._state_service.get_object_state(
            object_name=object_name,
            camera_id=camera_id,
            zone_id=zone_id,
        )
        resolved_camera_id = state.get("camera_id") or camera_id

        device_status = "unknown"
        if resolved_camera_id:
            device = self._device_repo.get_device_status_by_camera(str(resolved_camera_id))
            if device is not None:
                device_status = device.status

        recency_class = self.classify_query_recency(query_text=query_text, query_type=query_type)
        decision = self.evaluate_staleness(
            query_recency_class=recency_class,
            fresh_until=state.get("fresh_until"),
            device_status=device_status,
            now=now,
        )
        state_reason_code = state.get("reason_code", "state_unavailable")
        policy_reason_code = decision.get("reason_code", "policy_unavailable")
        return {
            "object_name": object_name,
            "camera_id": resolved_camera_id,
            "zone_id": state.get("zone_id") or zone_id,
            "state_value": state.get("state_value", "unknown"),
            "state_reason_code": state_reason_code,
            "state_freshness_level": state.get("freshness_level", "unknown"),
            "reason_codes": {
                "state": state_reason_code,
                "policy": policy_reason_code,
            },
            **decision,
        }

    @staticmethod
    def _classify_freshness_level(
        *,
        fresh_dt: datetime | None,
        now_dt: datetime,
        is_stale: bool,
        grace_sec: int,
    ) -> str:
        if fresh_dt is None:
            return "unknown"
        if is_stale:
            return "stale"
        remaining_sec = (fresh_dt - now_dt).total_seconds()
        if remaining_sec <= max(grace_sec, 30):
            return "aging"
        return "fresh"
