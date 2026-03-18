"""Perception ingress service for device events and heartbeats."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any
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

if TYPE_CHECKING:
    from src.services.notification_service import NotificationService
    from src.services.ocr_service import OCRService
    from src.services.state_service import StateService
    from src.services.vision_analysis_service import VisionAnalysisService


class PerceptionService:
    """Validate device ingress and persist observation/event/device updates."""

    _ALLOWED_STATUSES = {"online", "offline", "degraded"}
    _EVENT_SCHEMA_VERSION = "edge.event.v1"
    _HEARTBEAT_SCHEMA_VERSION = "edge.heartbeat.v1"
    _OCR_ANALYSIS_TYPES = {"ocr_quick_read", "ocr_extract_fields"}
    _VISION_ANALYSIS_TYPES = {"vision_q8_describe"}
    _STATE_ANALYSIS_TYPES = {"scene_recheck", "object_state_recheck", "zone_state_recheck"}
    _SUPPORTED_ANALYSIS_TYPES = _OCR_ANALYSIS_TYPES | _VISION_ANALYSIS_TYPES | _STATE_ANALYSIS_TYPES

    def __init__(
        self,
        *,
        device_repo: DeviceRepo,
        audit_repo: AuditRepo,
        memory_service: MemoryService,
        config: AppConfig,
        security_guard: SecurityGuard,
        ocr_service: OCRService | None = None,
        vision_analysis_service: VisionAnalysisService | None = None,
        state_service: StateService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._audit_repo = audit_repo
        self._memory_service = memory_service
        self._config = config
        self._security_guard = security_guard
        self._ocr_service = ocr_service
        self._vision_analysis_service = vision_analysis_service
        self._state_service = state_service
        self._notification_service = notification_service
        self._device_profiles = self._build_device_profiles()

    def ingest_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        ingest_payload = self._normalize_event_payload(payload)
        device_id = require_non_empty(ingest_payload.get("device_id"), "device_id")
        trace_id = self._as_optional_text(ingest_payload.get("trace_id"))

        try:
            profile = self._validate_device_access(
                device_id=device_id,
                api_key=self._as_optional_text(ingest_payload.get("api_key")),
                trace_id=trace_id,
                action="device_ingest_event",
            )
            device = self._ensure_device_row(
                device_id=device_id,
                profile=profile,
                payload=ingest_payload,
                status_hint="online",
            )
            ingest_payload["device_id"] = device_id
            ingest_payload.setdefault("camera_id", device.camera_id)
            # Event ingress is a liveness signal from edge; keep device status warm.
            device = self._refresh_device_from_event(device=device, payload=ingest_payload)
            ingest_payload["camera_id"] = device.camera_id

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
            analysis_report = self._trigger_backend_analysis(
                payload=ingest_payload,
                observation=observation,
                promoted_event=promoted_event,
                trace_id=trace_id,
            )
            notification_report = self._trigger_notification_hook(
                promoted_event=promoted_event,
                trace_id=trace_id,
            )

            return {
                "accepted": True,
                "type": "device_ingest_event",
                "device_id": device_id,
                "camera_id": observation.camera_id,
                "observation_id": observation.id,
                "event_id": promoted_event.id if promoted_event else None,
                "event_promoted": promoted_event is not None,
                "analysis": analysis_report,
                "notifications": notification_report,
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
        heartbeat_payload = self._normalize_heartbeat_payload(payload)
        device_id = require_non_empty(heartbeat_payload.get("device_id"), "device_id")
        trace_id = self._as_optional_text(heartbeat_payload.get("trace_id"))
        status = (self._as_optional_text(heartbeat_payload.get("status")) or "online").lower()

        try:
            if status not in self._ALLOWED_STATUSES:
                raise ValueError(f"Invalid heartbeat status: {status}")

            profile = self._validate_device_access(
                device_id=device_id,
                api_key=self._as_optional_text(heartbeat_payload.get("api_key")),
                trace_id=trace_id,
                action="device_heartbeat",
            )
            current = self._ensure_device_row(
                device_id=device_id,
                profile=profile,
                payload=heartbeat_payload,
                status_hint=status,
            )

            now = utc_now_iso8601()
            last_seen = self._as_optional_text(heartbeat_payload.get("last_seen")) or now
            camera_id = self._as_optional_text(heartbeat_payload.get("camera_id")) or current.camera_id
            if not camera_id:
                raise ValueError(f"camera_id missing for device_id={device_id}")

            updated = self._device_repo.save_device_status(
                DeviceStatus(
                    id=current.id,
                    device_id=device_id,
                    camera_id=camera_id,
                    device_name=self._coalesce_text(heartbeat_payload, "device_name", current.device_name),
                    api_key_hash=current.api_key_hash,
                    status=status,
                    ip_addr=self._coalesce_text(heartbeat_payload, "ip_addr", current.ip_addr),
                    firmware_version=self._coalesce_text(heartbeat_payload, "firmware_version", current.firmware_version),
                    model_version=self._coalesce_text(heartbeat_payload, "model_version", current.model_version),
                    temperature=self._coalesce_float(heartbeat_payload, "temperature", current.temperature),
                    cpu_load=self._coalesce_float(heartbeat_payload, "cpu_load", current.cpu_load),
                    npu_load=self._coalesce_float(heartbeat_payload, "npu_load", current.npu_load),
                    free_mem_mb=self._coalesce_int(heartbeat_payload, "free_mem_mb", current.free_mem_mb),
                    camera_fps=self._coalesce_int(heartbeat_payload, "camera_fps", current.camera_fps),
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

    def _refresh_device_from_event(self, *, device: DeviceStatus, payload: dict[str, Any]) -> DeviceStatus:
        now = utc_now_iso8601()
        event_last_seen = (
            self._as_optional_text(payload.get("observed_at"))
            or self._as_optional_text(payload.get("last_seen"))
            or now
        )
        camera_id = self._as_optional_text(payload.get("camera_id")) or device.camera_id
        if not camera_id:
            raise ValueError(f"camera_id missing for device_id={device.device_id}")
        refreshed = DeviceStatus(
            id=device.id,
            device_id=device.device_id,
            camera_id=camera_id,
            device_name=self._coalesce_text(payload, "device_name", device.device_name),
            api_key_hash=device.api_key_hash,
            status="online",
            ip_addr=self._coalesce_text(payload, "ip_addr", device.ip_addr),
            firmware_version=self._coalesce_text(payload, "firmware_version", device.firmware_version),
            model_version=self._coalesce_text(payload, "model_version", device.model_version),
            temperature=self._coalesce_float(payload, "temperature", device.temperature),
            cpu_load=self._coalesce_float(payload, "cpu_load", device.cpu_load),
            npu_load=self._coalesce_float(payload, "npu_load", device.npu_load),
            free_mem_mb=self._coalesce_int(payload, "free_mem_mb", device.free_mem_mb),
            camera_fps=self._coalesce_int(payload, "camera_fps", device.camera_fps),
            last_seen=event_last_seen,
            created_at=device.created_at,
            updated_at=now,
        )
        return self._device_repo.save_device_status(refreshed)

    def _trigger_state_refresh_hook(
        self,
        *,
        observation: Observation,
        promoted_event: Event | None,
    ) -> None:
        # Reserved integration hook for T6 state_service.
        _ = (observation, promoted_event)

    def _trigger_notification_hook(
        self,
        *,
        promoted_event: Event | None,
        trace_id: str | None,
    ) -> dict[str, Any] | None:
        if promoted_event is None:
            return None
        if self._notification_service is None:
            return {
                "requested": 0,
                "triggered": 0,
                "skipped": 0,
                "deliveries": [],
                "skipped_reasons": [],
                "status": "skipped",
                "reason": "notification_service_unavailable",
            }
        result = self._notification_service.evaluate_event_notifications(
            event=promoted_event,
            trace_id=trace_id,
        )
        result["status"] = "ok"
        return result

    def _trigger_backend_analysis(
        self,
        *,
        payload: dict[str, Any],
        observation: Observation,
        promoted_event: Event | None,
        trace_id: str | None,
    ) -> dict[str, Any] | None:
        requests = self._normalize_analysis_requests(payload.get("analysis_requests"))
        if not requests:
            return None

        report: dict[str, Any] = {
            "requested": len(requests),
            "executed": 0,
            "skipped": 0,
            "failed": 0,
            "results": [],
        }

        if not self._analysis_enabled():
            report["skipped"] = len(requests)
            report["status"] = "skipped"
            report["reason"] = "policy_disabled"
            return report

        for request in requests:
            req_type = request["type"]
            try:
                result = self._dispatch_analysis_request(
                    request=request,
                    payload=payload,
                    observation=observation,
                    promoted_event=promoted_event,
                    trace_id=trace_id,
                )
            except ValueError as exc:  # pragma: no cover - defensive branch for downstream services
                report["failed"] += 1
                report["results"].append(
                    {
                        "type": req_type,
                        "status": "failed",
                        "reason": str(exc),
                    }
                )
                continue

            status = self._as_optional_text(result.get("status")) or "skipped"
            if status == "ok":
                report["executed"] += 1
            elif status == "failed":
                report["failed"] += 1
            else:
                report["skipped"] += 1
            report["results"].append(result)

        if report["failed"] > 0 and report["executed"] > 0:
            report["status"] = "partial"
        elif report["failed"] > 0:
            report["status"] = "failed"
        elif report["executed"] > 0:
            report["status"] = "ok"
        else:
            report["status"] = "skipped"

        self._write_audit(
            action="perception_backend_analysis",
            decision="allow" if report["failed"] == 0 else "deny",
            reason=str(report["status"]),
            device_id=observation.device_id,
            target_type="observation",
            target_id=observation.id,
            trace_id=trace_id,
            meta=report,
        )
        return report

    def _dispatch_analysis_request(
        self,
        *,
        request: dict[str, Any],
        payload: dict[str, Any],
        observation: Observation,
        promoted_event: Event | None,
        trace_id: str | None,
    ) -> dict[str, Any]:
        req_type = request["type"]
        if req_type in self._OCR_ANALYSIS_TYPES:
            return self._dispatch_ocr_request(
                req_type=req_type,
                request=request,
                payload=payload,
                observation=observation,
                promoted_event=promoted_event,
                trace_id=trace_id,
            )
        if req_type in self._VISION_ANALYSIS_TYPES:
            return self._dispatch_vision_request(
                req_type=req_type,
                request=request,
                payload=payload,
                observation=observation,
                promoted_event=promoted_event,
                trace_id=trace_id,
            )
        if req_type == "scene_recheck":
            return self._dispatch_scene_recheck(request=request, payload=payload, observation=observation)
        if req_type == "object_state_recheck":
            return self._dispatch_object_state_recheck(request=request, payload=payload, observation=observation)
        if req_type == "zone_state_recheck":
            return self._dispatch_zone_state_recheck(request=request, payload=payload, observation=observation)
        return {
            "type": req_type,
            "status": "skipped",
            "reason": "unsupported_analysis_type",
        }

    def _dispatch_ocr_request(
        self,
        *,
        req_type: str,
        request: dict[str, Any],
        payload: dict[str, Any],
        observation: Observation,
        promoted_event: Event | None,
        trace_id: str | None,
    ) -> dict[str, Any]:
        if self._ocr_service is None:
            return {
                "type": req_type,
                "status": "skipped",
                "reason": "ocr_service_unavailable",
            }

        input_uri = self._as_optional_text(request.get("input_uri")) or self._as_optional_text(payload.get("snapshot_uri"))
        if not input_uri:
            return {
                "type": req_type,
                "status": "skipped",
                "reason": "missing_input_uri",
            }

        ocr_payload: dict[str, Any] = {
            "input_uri": input_uri,
            "observation_id": observation.id,
            "event_id": promoted_event.id if promoted_event else None,
            "trace_id": trace_id,
            "promote_to_event": False,
        }
        if req_type == "ocr_extract_fields" and isinstance(request.get("field_schema"), (dict, list)):
            ocr_payload["field_schema"] = request["field_schema"]

        if req_type == "ocr_extract_fields":
            ocr_result = self._ocr_service.extract_fields(ocr_payload)
        else:
            ocr_result = self._ocr_service.quick_read(ocr_payload)
        return {
            "type": req_type,
            "status": "ok",
            "backend": "ocr_service",
            "ocr_result_id": self._as_optional_text(ocr_result.get("ocr_result_id")),
        }

    def _dispatch_vision_request(
        self,
        *,
        req_type: str,
        request: dict[str, Any],
        payload: dict[str, Any],
        observation: Observation,
        promoted_event: Event | None,
        trace_id: str | None,
    ) -> dict[str, Any]:
        if self._vision_analysis_service is None:
            return {
                "type": req_type,
                "status": "skipped",
                "reason": "vision_analysis_service_unavailable",
            }

        input_uri = self._as_optional_text(request.get("input_uri")) or self._as_optional_text(payload.get("snapshot_uri"))
        if not input_uri:
            return {
                "type": req_type,
                "status": "skipped",
                "reason": "missing_input_uri",
            }

        vision_payload: dict[str, Any] = {
            "input_uri": input_uri,
            "observation_id": observation.id,
            "event_id": promoted_event.id if promoted_event else None,
            "trace_id": trace_id,
            "object_name": (
                self._as_optional_text(request.get("object_name"))
                or self._as_optional_text(payload.get("object_name"))
                or self._as_optional_text(observation.object_name)
            ),
            "object_class": (
                self._as_optional_text(request.get("object_class"))
                or self._as_optional_text(payload.get("object_class"))
                or self._as_optional_text(observation.object_class)
            ),
            "camera_id": (
                self._as_optional_text(request.get("camera_id"))
                or self._as_optional_text(payload.get("camera_id"))
                or self._as_optional_text(observation.camera_id)
            ),
            "zone_id": (
                self._as_optional_text(request.get("zone_id"))
                or self._as_optional_text(payload.get("zone_id"))
                or self._as_optional_text(observation.zone_id)
            ),
            "track_id": (
                self._as_optional_text(request.get("track_id"))
                or self._as_optional_text(payload.get("track_id"))
                or self._as_optional_text(observation.track_id)
            ),
            "importance": self._to_int(payload.get("importance")) or 3,
        }
        vision_result = self._vision_analysis_service.describe_scene(vision_payload)
        return {
            "type": req_type,
            "status": "ok",
            "backend": self._as_optional_text(vision_result.get("backend")) or "vision_analysis_service",
            "vision_event_id": self._as_optional_text(vision_result.get("vision_event_id")),
            "summary": self._as_optional_text(vision_result.get("summary")),
            "model": self._as_optional_text(vision_result.get("model")),
            "duration_ms": vision_result.get("duration_ms"),
        }

    def _dispatch_scene_recheck(
        self,
        *,
        request: dict[str, Any],
        payload: dict[str, Any],
        observation: Observation,
    ) -> dict[str, Any]:
        if self._state_service is None:
            return {
                "type": "scene_recheck",
                "status": "skipped",
                "reason": "state_service_unavailable",
            }

        object_result = self._dispatch_object_state_recheck(request=request, payload=payload, observation=observation)
        zone_result = self._dispatch_zone_state_recheck(request=request, payload=payload, observation=observation)
        if object_result["status"] != "ok" and zone_result["status"] != "ok":
            return {
                "type": "scene_recheck",
                "status": "skipped",
                "reason": "missing_scene_context",
                "object_reason": object_result.get("reason"),
                "zone_reason": zone_result.get("reason"),
            }
        return {
            "type": "scene_recheck",
            "status": "ok",
            "backend": "state_service",
            "object_recheck": object_result,
            "zone_recheck": zone_result,
        }

    def _dispatch_object_state_recheck(
        self,
        *,
        request: dict[str, Any],
        payload: dict[str, Any],
        observation: Observation,
    ) -> dict[str, Any]:
        if self._state_service is None:
            return {
                "type": "object_state_recheck",
                "status": "skipped",
                "reason": "state_service_unavailable",
            }

        object_name = (
            self._as_optional_text(request.get("object_name"))
            or self._as_optional_text(payload.get("object_name"))
            or self._as_optional_text(observation.object_name)
        )
        if not object_name:
            return {
                "type": "object_state_recheck",
                "status": "skipped",
                "reason": "missing_object_name",
            }

        camera_id = (
            self._as_optional_text(request.get("camera_id"))
            or self._as_optional_text(payload.get("camera_id"))
            or self._as_optional_text(observation.camera_id)
        )
        zone_id = (
            self._as_optional_text(request.get("zone_id"))
            or self._as_optional_text(payload.get("zone_id"))
            or self._as_optional_text(observation.zone_id)
        )
        object_state, reason_code = self._state_service.refresh_object_state(
            object_name=object_name,
            camera_id=camera_id,
            zone_id=zone_id,
        )
        return {
            "type": "object_state_recheck",
            "status": "ok",
            "backend": "state_service",
            "state_id": object_state.id,
            "state_value": object_state.state_value,
            "reason_code": reason_code,
        }

    def _dispatch_zone_state_recheck(
        self,
        *,
        request: dict[str, Any],
        payload: dict[str, Any],
        observation: Observation,
    ) -> dict[str, Any]:
        if self._state_service is None:
            return {
                "type": "zone_state_recheck",
                "status": "skipped",
                "reason": "state_service_unavailable",
            }

        camera_id = (
            self._as_optional_text(request.get("camera_id"))
            or self._as_optional_text(payload.get("camera_id"))
            or self._as_optional_text(observation.camera_id)
        )
        zone_id = (
            self._as_optional_text(request.get("zone_id"))
            or self._as_optional_text(payload.get("zone_id"))
            or self._as_optional_text(observation.zone_id)
        )
        if not camera_id or not zone_id:
            return {
                "type": "zone_state_recheck",
                "status": "skipped",
                "reason": "missing_zone_context",
            }

        zone_state, reason_code = self._state_service.refresh_zone_state(
            camera_id=camera_id,
            zone_id=zone_id,
        )
        return {
            "type": "zone_state_recheck",
            "status": "ok",
            "backend": "state_service",
            "state_id": zone_state.id,
            "state_value": zone_state.state_value,
            "reason_code": reason_code,
        }

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

    def _normalize_event_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        normalized["analysis_requests"] = self._normalize_analysis_requests(normalized.get("analysis_requests"))
        schema_version = self._as_optional_text(normalized.get("schema_version"))
        if not schema_version:
            return normalized
        if schema_version != self._EVENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported event schema_version: {schema_version} (expected {self._EVENT_SCHEMA_VERSION})"
            )

        self._require_payload_field(normalized, "event_id", "event payload")
        self._require_payload_field(normalized, "device_id", "event payload")
        self._require_payload_field(normalized, "camera_id", "event payload")
        self._require_payload_field(normalized, "seq_no", "event payload")
        self._require_payload_field(normalized, "captured_at", "event payload")
        self._require_payload_field(normalized, "sent_at", "event payload")
        self._require_payload_field(normalized, "event_type", "event payload")
        self._require_payload_field(normalized, "objects", "event payload")

        seq_no = self._to_int(normalized.get("seq_no"))
        if seq_no is None or seq_no < 0:
            raise ValueError("event payload seq_no must be an integer >= 0")
        objects = normalized.get("objects")
        if not isinstance(objects, list):
            raise ValueError("event payload objects must be a list")

        if not self._as_optional_text(normalized.get("observed_at")):
            normalized["observed_at"] = self._as_optional_text(normalized.get("captured_at"))
        if "raw_detections" not in normalized:
            normalized["raw_detections"] = objects
        if self._to_int(normalized.get("importance")) is None:
            normalized["importance"] = 3
        if not self._as_optional_text(normalized.get("summary")):
            normalized["summary"] = self._as_optional_text(normalized.get("event_type")) or "edge_event"

        if objects and isinstance(objects[0], dict):
            primary = objects[0]
            if not self._as_optional_text(normalized.get("object_name")):
                normalized["object_name"] = self._as_optional_text(primary.get("object_name")) or "scene"
            if not self._as_optional_text(normalized.get("object_class")):
                normalized["object_class"] = self._as_optional_text(primary.get("object_class")) or "scene"
            if not self._as_optional_text(normalized.get("track_id")):
                normalized["track_id"] = self._as_optional_text(primary.get("track_id"))
            if self._to_float(normalized.get("confidence")) is None:
                confidence = self._to_float(primary.get("confidence"))
                if confidence is not None:
                    normalized["confidence"] = confidence
            if not self._as_optional_text(normalized.get("zone_id")):
                normalized["zone_id"] = self._as_optional_text(primary.get("zone_id"))

        return normalized

    def _normalize_analysis_requests(self, raw_value: Any) -> list[dict[str, Any]]:
        if raw_value is None:
            return []
        if not isinstance(raw_value, list):
            raise ValueError("event payload analysis_requests must be a list")

        requests: list[dict[str, Any]] = []
        for item in raw_value:
            if not isinstance(item, dict):
                continue
            req_type = self._as_optional_text(item.get("type"))
            if req_type not in self._SUPPORTED_ANALYSIS_TYPES:
                continue
            normalized: dict[str, Any] = {
                "type": req_type,
                "priority": self._as_optional_text(item.get("priority")),
                "reason": self._as_optional_text(item.get("reason")),
                "input_uri": self._as_optional_text(item.get("input_uri")),
                "object_class": self._as_optional_text(item.get("object_class")),
                "track_id": self._as_optional_text(item.get("track_id")),
                "object_name": self._as_optional_text(item.get("object_name")),
                "camera_id": self._as_optional_text(item.get("camera_id")),
                "zone_id": self._as_optional_text(item.get("zone_id")),
            }
            field_schema = item.get("field_schema")
            if isinstance(field_schema, (dict, list)):
                normalized["field_schema"] = field_schema
            requests.append(normalized)
        return requests

    def _analysis_enabled(self) -> bool:
        policy = self._config.policies.get("edge_analysis", {})
        if not isinstance(policy, dict):
            return True
        flag = policy.get("enable_backend_analysis")
        if isinstance(flag, bool):
            return flag
        return True

    def _normalize_heartbeat_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if "status" not in normalized and isinstance(normalized.get("online"), bool):
            normalized["status"] = "online" if normalized["online"] else "offline"
        if "last_seen" not in normalized and self._as_optional_text(normalized.get("sent_at")):
            normalized["last_seen"] = self._as_optional_text(normalized.get("sent_at"))

        schema_version = self._as_optional_text(normalized.get("schema_version"))
        if not schema_version:
            return normalized
        if schema_version != self._HEARTBEAT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported heartbeat schema_version: {schema_version} (expected {self._HEARTBEAT_SCHEMA_VERSION})"
            )

        self._require_payload_field(normalized, "device_id", "heartbeat payload")
        self._require_payload_field(normalized, "online", "heartbeat payload")
        self._require_payload_field(normalized, "last_capture_ok", "heartbeat payload")
        self._require_payload_field(normalized, "last_upload_ok", "heartbeat payload")
        self._require_payload_field(normalized, "sent_at", "heartbeat payload")

        if not isinstance(normalized.get("online"), bool):
            raise ValueError("heartbeat payload online must be boolean")
        if not isinstance(normalized.get("last_capture_ok"), bool):
            raise ValueError("heartbeat payload last_capture_ok must be boolean")
        if not isinstance(normalized.get("last_upload_ok"), bool):
            raise ValueError("heartbeat payload last_upload_ok must be boolean")

        if "status" not in normalized:
            normalized["status"] = "online" if normalized["online"] else "offline"
        if "last_seen" not in normalized:
            normalized["last_seen"] = normalized["sent_at"]
        return normalized

    def _require_payload_field(self, payload: dict[str, Any], field: str, context: str) -> None:
        if field not in payload:
            raise ValueError(f"{context} missing required field: {field}")
        value = payload.get(field)
        if value is None:
            raise ValueError(f"{context} field {field} cannot be null")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{context} field {field} cannot be empty")
