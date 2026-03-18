"""Device service for command execution and media indexing."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.session import utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.schemas.memory import MediaItem
from src.schemas.security import AuditLog
from src.services.edge_command_client import EdgeCommandClient, EdgeCommandClientError
from src.settings import AppConfig


class DeviceExecutionError(ValueError):
    """User-facing device command error with stable reason code."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class DeviceService:
    """Service boundary for device status and command execution."""

    def __init__(
        self,
        *,
        device_repo: DeviceRepo,
        media_repo: MediaRepo,
        audit_repo: AuditRepo,
        config: AppConfig,
        adapter: EdgeCommandClient | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._media_repo = media_repo
        self._audit_repo = audit_repo
        self._config = config
        self._adapter = adapter or EdgeCommandClient(config=config)
        self._device_profiles = self._build_device_profiles()

    def get_device_status(self, device_id: str) -> dict[str, Any] | None:
        device = self._device_repo.get_device_status(device_id)
        if device is None:
            return None
        is_online, offline_reason = self._evaluate_online_status(device)
        effective_status = "online" if is_online else "offline"
        return {
            "id": device.id,
            "device_id": device.device_id,
            "camera_id": device.camera_id,
            "device_name": device.device_name,
            "status": device.status,
            "effective_status": effective_status,
            "is_online": is_online,
            "offline_reason": offline_reason,
            "last_seen": device.last_seen,
            "firmware_version": device.firmware_version,
            "model_version": device.model_version,
            "temperature": device.temperature,
            "cpu_load": device.cpu_load,
            "npu_load": device.npu_load,
            "free_mem_mb": device.free_mem_mb,
            "camera_fps": device.camera_fps,
            "updated_at": device.updated_at,
        }

    def take_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        command_id = f"cmd-snapshot-{uuid4().hex[:12]}"
        requested_at = utc_now_iso8601()
        device_hint = self._as_text(payload.get("device_id")) or self._as_text(payload.get("camera_id"))

        try:
            device = self._resolve_device(payload)
            camera_id = device.camera_id
            self._ensure_online_for_command(device)
            try:
                result = self._adapter.take_snapshot(
                    device=device,
                    camera_id=camera_id,
                    command_id=command_id,
                    trace_id=self._as_text(payload.get("trace_id")),
                )
            except EdgeCommandClientError as exc:
                raise DeviceExecutionError(exc.code, exc.message) from exc
            adapter_meta = self._as_dict(result.get("meta"))
            media = self._persist_media_item(
                owner_id=command_id,
                media_type="image",
                result=result,
                visibility_scope=payload.get("visibility_scope"),
                local_dir=self._resolve_media_dir(device.device_id, "snapshot"),
            )
            self._write_audit(
                action="device_take_snapshot",
                decision="allow",
                device_id=device.device_id,
                target_type="media",
                target_id=media.id,
                reason="snapshot_created",
                trace_id=self._as_text(payload.get("trace_id")),
                meta={
                    "camera_id": camera_id,
                    "command_id": command_id,
                    "edge_command_id": self._as_text(adapter_meta.get("edge_command_id")),
                    "uri": media.uri,
                },
            )
            return {
                "ok": True,
                "summary": "Snapshot command completed",
                "data": {
                    "media_id": media.id,
                    "uri": media.uri,
                    "media_type": media.media_type,
                    "device_id": device.device_id,
                    "camera_id": camera_id,
                },
                "meta": {
                    "command": "take_snapshot",
                    "command_id": command_id,
                    "edge_command_id": self._as_text(adapter_meta.get("edge_command_id")),
                    "adapter": self._as_text(adapter_meta.get("adapter")),
                    "requested_at": requested_at,
                    "local_path": media.local_path,
                },
            }
        except DeviceExecutionError as exc:
            audit_device_id = self._resolve_audit_device_id(device_hint)
            self._write_audit(
                action="device_take_snapshot",
                decision="deny",
                device_id=audit_device_id,
                target_type="device",
                target_id=device_hint,
                reason=exc.code,
                trace_id=self._as_text(payload.get("trace_id")),
                meta={"message": exc.message, "command_id": command_id, "device_hint": device_hint},
            )
            self._audit_repo.conn.commit()
            raise

    def get_recent_clip(self, payload: dict[str, Any]) -> dict[str, Any]:
        command_id = f"cmd-clip-{uuid4().hex[:12]}"
        requested_at = utc_now_iso8601()
        device_hint = self._as_text(payload.get("device_id")) or self._as_text(payload.get("camera_id"))

        try:
            device = self._resolve_device(payload)
            camera_id = device.camera_id
            duration_sec = self._normalize_duration(payload)
            self._ensure_online_for_command(device)
            try:
                result = self._adapter.get_recent_clip(
                    device=device,
                    camera_id=camera_id,
                    duration_sec=duration_sec,
                    command_id=command_id,
                    trace_id=self._as_text(payload.get("trace_id")),
                )
            except EdgeCommandClientError as exc:
                raise DeviceExecutionError(exc.code, exc.message) from exc
            adapter_meta = self._as_dict(result.get("meta"))
            media = self._persist_media_item(
                owner_id=command_id,
                media_type="video",
                result=result,
                visibility_scope=payload.get("visibility_scope"),
                local_dir=self._resolve_media_dir(device.device_id, "clip"),
            )
            self._write_audit(
                action="device_get_recent_clip",
                decision="allow",
                device_id=device.device_id,
                target_type="media",
                target_id=media.id,
                reason="clip_created",
                trace_id=self._as_text(payload.get("trace_id")),
                meta={
                    "camera_id": camera_id,
                    "command_id": command_id,
                    "edge_command_id": self._as_text(adapter_meta.get("edge_command_id")),
                    "duration_sec": duration_sec,
                    "uri": media.uri,
                },
            )
            return {
                "ok": True,
                "summary": "Recent clip command completed",
                "data": {
                    "media_id": media.id,
                    "uri": media.uri,
                    "media_type": media.media_type,
                    "device_id": device.device_id,
                    "camera_id": camera_id,
                    "duration_sec": media.duration_sec,
                },
                "meta": {
                    "command": "get_recent_clip",
                    "command_id": command_id,
                    "edge_command_id": self._as_text(adapter_meta.get("edge_command_id")),
                    "adapter": self._as_text(adapter_meta.get("adapter")),
                    "requested_at": requested_at,
                    "local_path": media.local_path,
                },
            }
        except DeviceExecutionError as exc:
            audit_device_id = self._resolve_audit_device_id(device_hint)
            self._write_audit(
                action="device_get_recent_clip",
                decision="deny",
                device_id=audit_device_id,
                target_type="device",
                target_id=device_hint,
                reason=exc.code,
                trace_id=self._as_text(payload.get("trace_id")),
                meta={"message": exc.message, "command_id": command_id, "device_hint": device_hint},
            )
            self._audit_repo.conn.commit()
            raise

    def _resolve_device(self, payload: dict[str, Any]) -> DeviceStatus:
        device_id = self._as_text(payload.get("device_id"))
        camera_id = self._as_text(payload.get("camera_id"))
        if not device_id and not camera_id:
            raise DeviceExecutionError(
                "DEVICE_IDENTIFIER_REQUIRED",
                "device_id or camera_id is required",
            )

        device: DeviceStatus | None = None
        if device_id:
            device = self._device_repo.get_device_status(device_id)
            if device is None:
                # Accept camera_id accidentally provided in device_id.
                device = self._device_repo.get_device_status_by_camera(device_id)
        elif camera_id:
            device = self._device_repo.get_device_status_by_camera(camera_id)

        if device is None:
            key = device_id or camera_id or "unknown"
            raise DeviceExecutionError("DEVICE_NOT_FOUND", f"Device not found: {key}")
        return device

    def _ensure_online_for_command(self, device: DeviceStatus) -> None:
        is_online, reason = self._evaluate_online_status(device)
        if not is_online:
            raise DeviceExecutionError("DEVICE_OFFLINE", reason or f"Device offline: {device.device_id}")

    def _evaluate_online_status(self, device: DeviceStatus) -> tuple[bool, str | None]:
        if (device.status or "").lower() == "offline":
            return False, "device_status_offline"
        if device.last_seen:
            try:
                last_seen_dt = datetime.fromisoformat(device.last_seen.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                return False, "invalid_last_seen"
            now_dt = datetime.now(tz=timezone.utc)
            offline_after_sec = self._offline_after_seconds(device.device_id)
            if (now_dt - last_seen_dt).total_seconds() > offline_after_sec:
                return False, "heartbeat_timeout"
        return True, None

    def _offline_after_seconds(self, device_id: str) -> int:
        profile = self._device_profiles.get(device_id, {})
        value = profile.get("heartbeat", {}).get("offline_after_sec", 90)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return 90

    def _persist_media_item(
        self,
        *,
        owner_id: str,
        media_type: str,
        result: dict[str, Any],
        visibility_scope: Any,
        local_dir: Path,
    ) -> MediaItem:
        uri = self._as_text(result.get("uri"))
        file_name = self._as_text(result.get("file_name"))
        if not uri or not file_name:
            raise DeviceExecutionError("MEDIA_WRITE_FAILED", "adapter result missing uri/file_name")

        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = str(local_dir / file_name)
        media = MediaItem(
            id=f"media-{uuid4().hex[:12]}",
            owner_type="manual",
            owner_id=owner_id,
            media_type=media_type,
            uri=uri,
            local_path=local_path,
            mime_type=self._as_text(result.get("mime_type")),
            duration_sec=self._to_int(result.get("duration_sec")),
            width=self._to_int(result.get("width")),
            height=self._to_int(result.get("height")),
            visibility_scope=self._as_text(visibility_scope) or "private",
            sha256=self._as_text(result.get("sha256")),
            created_at=None,
        )
        try:
            return self._media_repo.save_media_item(media)
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise DeviceExecutionError("MEDIA_WRITE_FAILED", str(exc)) from exc

    def _resolve_media_dir(self, device_id: str, media_kind: str) -> Path:
        default = Path("./data/media/snapshots" if media_kind == "snapshot" else "./data/media/clips")
        profile = self._device_profiles.get(device_id, {})
        upload_cfg = profile.get("upload", {}) if isinstance(profile, dict) else {}
        configured = (
            upload_cfg.get("snapshot_dir")
            if media_kind == "snapshot"
            else upload_cfg.get("clip_dir")
        )
        candidate = Path(str(configured)) if configured else default
        return candidate

    def _normalize_duration(self, payload: dict[str, Any]) -> int:
        raw = payload.get("duration_sec", payload.get("seconds", 10))
        try:
            duration = int(raw)
        except (TypeError, ValueError) as exc:
            raise DeviceExecutionError("INVALID_DURATION", "duration_sec must be an integer") from exc
        if duration <= 0 or duration > 120:
            raise DeviceExecutionError("INVALID_DURATION", "duration_sec must be in [1, 120]")
        return duration

    def _write_audit(
        self,
        *,
        action: str,
        decision: str,
        device_id: str | None,
        target_type: str | None,
        target_id: str | None,
        reason: str,
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
                meta_json=json.dumps(self._serialize(meta), ensure_ascii=False, sort_keys=True) if meta else None,
                created_at=None,
            )
        )

    def _resolve_audit_device_id(self, device_hint: str | None) -> str | None:
        hint = self._as_text(device_hint)
        if not hint:
            return None
        device = self._device_repo.get_device_status(hint)
        if device is not None:
            return device.device_id
        by_camera = self._device_repo.get_device_status_by_camera(hint)
        if by_camera is not None:
            return by_camera.device_id
        return None

    def _build_device_profiles(self) -> dict[str, dict[str, Any]]:
        profiles: dict[str, dict[str, Any]] = {}
        for entry in self._config.devices.get("devices", []):
            if not isinstance(entry, dict):
                continue
            device_id = self._as_text(entry.get("device_id"))
            if not device_id:
                continue
            profiles[device_id] = entry
        return profiles

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _serialize(value: Any) -> Any:
        if value is None:
            return None
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return {str(k): DeviceService._serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [DeviceService._serialize(v) for v in value]
        return value
