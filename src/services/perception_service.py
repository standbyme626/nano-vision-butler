"""Perception ingress service for device events and heartbeats."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.session import require_non_empty, utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.schemas.memory import Event, Observation
from src.schemas.security import AuditLog
from src.security.security_guard import SecurityGuard
from src.services.memory_service import MemoryService
from src.settings import AppConfig


class PerceptionService:
    """Validate device ingress and persist observation/event/device updates."""

    _ALLOWED_STATUSES = {"online", "offline", "degraded"}

    def __init__(
        self,
        *,
        device_repo: DeviceRepo,
        audit_repo: AuditRepo,
        memory_service: MemoryService,
        config: AppConfig,
        security_guard: SecurityGuard,
    ) -> None:
        self._device_repo = device_repo
        self._audit_repo = audit_repo
        self._memory_service = memory_service
        self._config = config
        self._security_guard = security_guard
        self._device_profiles = self._build_device_profiles()

    def ingest_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        device_id = require_non_empty(payload.get("device_id"), "device_id")
        trace_id = self._as_optional_text(payload.get("trace_id"))

        try:
            profile = self._validate_device_access(
                device_id=device_id,
                api_key=self._as_optional_text(payload.get("api_key")),
                trace_id=trace_id,
                action="device_ingest_event",
            )
            device = self._ensure_device_row(device_id=device_id, profile=profile, payload=payload, status_hint="online")
            ingest_payload = dict(payload)
            ingest_payload["device_id"] = device_id
            ingest_payload.setdefault("camera_id", device.camera_id)

            observation = self._memory_service.save_observation_from_payload(ingest_payload)
            promoted_event = self._memory_service.promote_observation_if_needed(ingest_payload, observation)

            self._write_audit(
                action="device_ingest_event",
                decision="allow",
                reason="observation_saved",
                device_id=device_id,
                target_type="observation",
                target_id=observation.id,
                trace_id=trace_id,
                meta={
                    "camera_id": observation.camera_id,
                    "event_promoted": promoted_event is not None,
                    "event_id": promoted_event.id if promoted_event else None,
                },
            )
            if promoted_event is not None:
                self._write_audit(
                    action="perception_promote_event",
                    decision="allow",
                    reason="promotion_rule_matched",
                    device_id=device_id,
                    target_type="event",
                    target_id=promoted_event.id,
                    trace_id=trace_id,
                    meta={
                        "observation_id": observation.id,
                        "event_type": promoted_event.event_type,
                        "importance": promoted_event.importance,
                    },
                )

            self._trigger_state_refresh_hook(observation=observation, promoted_event=promoted_event)

            return {
                "accepted": True,
                "type": "device_ingest_event",
                "device_id": device_id,
                "camera_id": observation.camera_id,
                "observation_id": observation.id,
                "event_id": promoted_event.id if promoted_event else None,
                "event_promoted": promoted_event is not None,
                "received_at": utc_now_iso8601(),
            }
        except ValueError as exc:
            self._write_audit(
                action="device_ingest_event",
                decision="deny",
                reason=str(exc),
                device_id=device_id if self._device_exists(device_id) else None,
                target_type="device",
                target_id=device_id,
                trace_id=trace_id,
                meta={"payload": payload},
            )
            raise

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        device_id = require_non_empty(payload.get("device_id"), "device_id")
        trace_id = self._as_optional_text(payload.get("trace_id"))
        status = (self._as_optional_text(payload.get("status")) or "online").lower()

        try:
            if status not in self._ALLOWED_STATUSES:
                raise ValueError(f"Invalid heartbeat status: {status}")

            profile = self._validate_device_access(
                device_id=device_id,
                api_key=self._as_optional_text(payload.get("api_key")),
                trace_id=trace_id,
                action="device_heartbeat",
            )
            current = self._ensure_device_row(
                device_id=device_id,
                profile=profile,
                payload=payload,
                status_hint=status,
            )

            now = utc_now_iso8601()
            last_seen = self._as_optional_text(payload.get("last_seen")) or now
            camera_id = self._as_optional_text(payload.get("camera_id")) or current.camera_id
            if not camera_id:
                raise ValueError(f"camera_id missing for device_id={device_id}")

            updated = self._device_repo.save_device_status(
                DeviceStatus(
                    id=current.id,
                    device_id=device_id,
                    camera_id=camera_id,
                    device_name=self._coalesce_text(payload, "device_name", current.device_name),
                    api_key_hash=current.api_key_hash,
                    status=status,
                    ip_addr=self._coalesce_text(payload, "ip_addr", current.ip_addr),
                    firmware_version=self._coalesce_text(payload, "firmware_version", current.firmware_version),
                    model_version=self._coalesce_text(payload, "model_version", current.model_version),
                    temperature=self._coalesce_float(payload, "temperature", current.temperature),
                    cpu_load=self._coalesce_float(payload, "cpu_load", current.cpu_load),
                    npu_load=self._coalesce_float(payload, "npu_load", current.npu_load),
                    free_mem_mb=self._coalesce_int(payload, "free_mem_mb", current.free_mem_mb),
                    camera_fps=self._coalesce_int(payload, "camera_fps", current.camera_fps),
                    last_seen=last_seen,
                    created_at=current.created_at,
                    updated_at=now,
                )
            )

            self._write_audit(
                action="device_heartbeat",
                decision="allow",
                reason="device_status_refreshed",
                device_id=device_id,
                target_type="device",
                target_id=device_id,
                trace_id=trace_id,
                meta={
                    "camera_id": updated.camera_id,
                    "status": updated.status,
                    "last_seen": updated.last_seen,
                    "temperature": updated.temperature,
                    "cpu_load": updated.cpu_load,
                    "npu_load": updated.npu_load,
                },
            )

            return {
                "accepted": True,
                "type": "device_heartbeat",
                "device_id": updated.device_id,
                "camera_id": updated.camera_id,
                "status": updated.status,
                "last_seen": updated.last_seen,
                "received_at": now,
            }
        except ValueError as exc:
            self._write_audit(
                action="device_heartbeat",
                decision="deny",
                reason=str(exc),
                device_id=device_id if self._device_exists(device_id) else None,
                target_type="device",
                target_id=device_id,
                trace_id=trace_id,
                meta={"payload": payload},
            )
            raise

    def _validate_device_access(
        self,
        *,
        device_id: str,
        api_key: str | None,
        trace_id: str | None,
        action: str,
    ) -> dict[str, Any]:
        self._security_guard.validate_device_access(
            device_id=device_id,
            api_key=api_key,
            trace_id=trace_id,
            action=action,
            meta={"camera_id": self._as_optional_text(self._device_profiles.get(device_id, {}).get("camera_id"))},
        )
        if device_id not in self._device_profiles:
            raise ValueError(f"Device not registered in config/devices.yaml: {device_id}")
        return self._device_profiles[device_id]

    def _ensure_device_row(
        self,
        *,
        device_id: str,
        profile: dict[str, Any],
        payload: dict[str, Any],
        status_hint: str,
    ) -> DeviceStatus:
        current = self._device_repo.get_device_status(device_id)
        if current is not None:
            return current

        camera_id = self._as_optional_text(payload.get("camera_id")) or self._as_optional_text(profile.get("camera_id"))
        if not camera_id:
            raise ValueError(f"camera_id missing for device_id={device_id}")

        seeded_api_key = (
            self._as_optional_text(payload.get("api_key"))
            or self._as_optional_text(profile.get("auth", {}).get("api_key"))
            or device_id
        )
        bootstrap = DeviceStatus(
            id=f"dev-{uuid4().hex[:12]}",
            device_id=device_id,
            camera_id=camera_id,
            device_name=self._as_optional_text(profile.get("device_name")),
            api_key_hash=self._hash_api_key(seeded_api_key),
            status=status_hint if status_hint in self._ALLOWED_STATUSES else "offline",
            ip_addr=self._as_optional_text(payload.get("ip_addr")),
            firmware_version=self._as_optional_text(payload.get("firmware_version")),
            model_version=self._as_optional_text(payload.get("model_version")),
            temperature=self._to_float(payload.get("temperature")),
            cpu_load=self._to_float(payload.get("cpu_load")),
            npu_load=self._to_float(payload.get("npu_load")),
            free_mem_mb=self._to_int(payload.get("free_mem_mb")),
            camera_fps=self._to_int(payload.get("camera_fps")),
            last_seen=utc_now_iso8601(),
            created_at=None,
            updated_at=None,
        )
        return self._device_repo.save_device_status(bootstrap)

    def _trigger_state_refresh_hook(
        self,
        *,
        observation: Observation,
        promoted_event: Event | None,
    ) -> None:
        # Reserved integration hook for T6 state_service.
        _ = (observation, promoted_event)

    def _write_audit(
        self,
        *,
        action: str,
        decision: str,
        reason: str,
        device_id: str | None,
        target_type: str | None,
        target_id: str | None,
        trace_id: str | None,
        meta: dict[str, Any] | None,
    ) -> None:
        self._audit_repo.save_audit_log(
            AuditLog(
                id=f"audit-{uuid4().hex[:12]}",
                user_id=None,
                device_id=device_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                decision=decision,
                reason=reason,
                trace_id=trace_id,
                meta_json=json.dumps(meta, ensure_ascii=False, sort_keys=True, default=str) if meta else None,
                created_at=None,
            )
        )

    def _device_exists(self, device_id: str) -> bool:
        return self._device_repo.get_device_status(device_id) is not None

    def _build_device_profiles(self) -> dict[str, dict[str, Any]]:
        profiles: dict[str, dict[str, Any]] = {}
        for entry in self._config.devices.get("devices", []):
            if not isinstance(entry, dict):
                continue
            device_id = self._as_optional_text(entry.get("device_id"))
            if not device_id:
                continue
            profiles[device_id] = entry
        return profiles

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

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
    def _to_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _coalesce_text(self, payload: dict[str, Any], key: str, current: str | None) -> str | None:
        if key not in payload:
            return current
        return self._as_optional_text(payload.get(key)) or current

    def _coalesce_float(self, payload: dict[str, Any], key: str, current: float | None) -> float | None:
        if key not in payload:
            return current
        value = self._to_float(payload.get(key))
        return current if value is None else value

    def _coalesce_int(self, payload: dict[str, Any], key: str, current: int | None) -> int | None:
        if key not in payload:
            return current
        value = self._to_int(payload.get(key))
        return current if value is None else value
