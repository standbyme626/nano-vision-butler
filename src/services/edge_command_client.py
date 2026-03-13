"""Bridge backend device commands to the edge runtime command executor."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from src.schemas.device import DeviceStatus
from src.settings import AppConfig


class EdgeCommandClientError(RuntimeError):
    """Stable edge command error with code and message."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class EdgeCommandClient:
    """Execute edge runtime commands and normalize outputs for device service."""

    def __init__(
        self,
        *,
        config: AppConfig,
        python_bin: str | None = None,
        runtime_module: str = "edge_device.api.server",
        timeout_sec: float = 20.0,
    ) -> None:
        self._python_bin = python_bin or os.getenv("PYTHON_BIN", "python3")
        self._runtime_module = os.getenv("EDGE_RUNTIME_MODULE", runtime_module)
        self._timeout_sec = self._to_timeout(os.getenv("EDGE_COMMAND_TIMEOUT_SEC"), timeout_sec)
        self._repo_root = Path(__file__).resolve().parents[2]
        self._device_profiles = self._build_device_profiles(config)

    def take_snapshot(
        self,
        *,
        device: DeviceStatus,
        camera_id: str,
        command_id: str,
        trace_id: str | None,
    ) -> dict[str, Any]:
        response = self._run_command(
            action="take-snapshot",
            command_id=command_id,
            trace_id=trace_id,
            duration_sec=None,
            env=self._build_env(device_id=device.device_id, camera_id=camera_id),
        )
        return self._normalize_media_result(
            expected_command="take_snapshot",
            uri_field="snapshot_uri",
            path_field="snapshot_path",
            mime_type="image/jpeg",
            response=response,
            fallback_command_id=command_id,
            fallback_trace_id=trace_id,
            duration_sec=None,
        )

    def get_recent_clip(
        self,
        *,
        device: DeviceStatus,
        camera_id: str,
        duration_sec: int,
        command_id: str,
        trace_id: str | None,
    ) -> dict[str, Any]:
        response = self._run_command(
            action="get-recent-clip",
            command_id=command_id,
            trace_id=trace_id,
            duration_sec=duration_sec,
            env=self._build_env(device_id=device.device_id, camera_id=camera_id),
        )
        return self._normalize_media_result(
            expected_command="get_recent_clip",
            uri_field="clip_uri",
            path_field="clip_path",
            mime_type="video/mp4",
            response=response,
            fallback_command_id=command_id,
            fallback_trace_id=trace_id,
            duration_sec=duration_sec,
        )

    def _run_command(
        self,
        *,
        action: str,
        command_id: str,
        trace_id: str | None,
        duration_sec: int | None,
        env: dict[str, str],
    ) -> dict[str, Any]:
        command: list[str] = [self._python_bin, "-m", self._runtime_module, action, "--command-id", command_id]
        if trace_id:
            command.extend(["--trace-id", trace_id])
        if duration_sec is not None:
            command.extend(["--duration-sec", str(duration_sec)])

        try:
            completed = subprocess.run(
                command,
                cwd=self._repo_root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=self._timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            raise EdgeCommandClientError("EDGE_COMMAND_TIMEOUT", f"edge command timed out: {action}") from exc
        except OSError as exc:
            raise EdgeCommandClientError("EDGE_COMMAND_EXEC_FAILED", str(exc)) from exc

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise EdgeCommandClientError(
                "EDGE_COMMAND_EXEC_FAILED",
                detail or f"edge command exited with code {completed.returncode}",
            )

        payload_text = (completed.stdout or "").strip()
        if not payload_text:
            raise EdgeCommandClientError("EDGE_COMMAND_INVALID_RESPONSE", "empty edge command response")

        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise EdgeCommandClientError("EDGE_COMMAND_INVALID_RESPONSE", "edge command returned non-JSON output") from exc

        if not isinstance(payload, dict):
            raise EdgeCommandClientError("EDGE_COMMAND_INVALID_RESPONSE", "edge command payload must be a JSON object")

        if not bool(payload.get("ok")):
            summary = self._as_text(payload.get("summary")) or self._as_text(payload.get("error")) or "command failed"
            raise EdgeCommandClientError("EDGE_COMMAND_FAILED", summary)
        return payload

    def _normalize_media_result(
        self,
        *,
        expected_command: str,
        uri_field: str,
        path_field: str,
        mime_type: str,
        response: dict[str, Any],
        fallback_command_id: str,
        fallback_trace_id: str | None,
        duration_sec: int | None,
    ) -> dict[str, Any]:
        data = self._as_dict(response.get("data"))
        command = self._as_text(data.get("command"))
        if command != expected_command:
            raise EdgeCommandClientError(
                "EDGE_COMMAND_INVALID_RESPONSE",
                f"unexpected command response: expected {expected_command}, got {command or 'missing'}",
            )

        uri = self._as_text(data.get(uri_field))
        if not uri:
            raise EdgeCommandClientError("EDGE_COMMAND_INVALID_RESPONSE", f"missing data.{uri_field}")

        fallback_path = self._as_text(data.get(path_field))
        file_name = self._extract_file_name(uri=uri, fallback_path=fallback_path)
        if not file_name:
            raise EdgeCommandClientError("EDGE_COMMAND_INVALID_RESPONSE", "cannot resolve media file name")

        meta_payload = self._as_dict(response.get("meta"))
        edge_command_id = self._as_text(data.get("command_id")) or fallback_command_id
        edge_trace_id = self._as_text(meta_payload.get("trace_id")) or fallback_trace_id
        edge_received_at = self._as_text(meta_payload.get("received_at"))
        result_duration = self._to_int(data.get("duration_sec"))
        if result_duration is None:
            result_duration = duration_sec

        return {
            "uri": uri,
            "file_name": file_name,
            "mime_type": mime_type,
            "width": self._to_int(data.get("width")),
            "height": self._to_int(data.get("height")),
            "duration_sec": result_duration,
            "sha256": self._as_text(data.get("sha256")),
            "meta": {
                "adapter": "edge_command_client",
                "command_id": fallback_command_id,
                "edge_command_id": edge_command_id,
                "trace_id": edge_trace_id,
                "schema_version": self._as_text(response.get("schema_version")),
                "response_type": self._as_text(response.get("type")),
                "received_at": edge_received_at,
            },
        }

    def _build_env(self, *, device_id: str, camera_id: str) -> dict[str, str]:
        env = dict(os.environ)
        env["EDGE_DEVICE_ID"] = device_id
        env["EDGE_CAMERA_ID"] = camera_id

        profile = self._device_profiles.get(device_id, {})
        upload_cfg = profile.get("upload", {}) if isinstance(profile, dict) else {}
        snapshot_dir = self._as_text(upload_cfg.get("snapshot_dir"))
        clip_dir = self._as_text(upload_cfg.get("clip_dir"))
        if snapshot_dir:
            env["EDGE_SNAPSHOT_DIR"] = snapshot_dir
        if clip_dir:
            env["EDGE_CLIP_DIR"] = clip_dir
        return env

    @staticmethod
    def _build_device_profiles(config: AppConfig) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in config.devices.get("devices", []):
            if not isinstance(item, Mapping):
                continue
            device_id = str(item.get("device_id", "")).strip()
            if not device_id:
                continue
            result[device_id] = dict(item)
        return result

    @staticmethod
    def _extract_file_name(*, uri: str, fallback_path: str | None) -> str | None:
        parsed = urlparse(uri)
        if parsed.path:
            name = Path(parsed.path).name
            if name:
                return name
        if fallback_path:
            fallback = Path(fallback_path).name
            if fallback:
                return fallback
        return None

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return str(value)

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
    def _to_timeout(raw: str | None, fallback: float) -> float:
        if raw is None:
            return fallback
        try:
            timeout = float(raw)
        except ValueError:
            return fallback
        return timeout if timeout > 0 else fallback
