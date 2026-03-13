"""Device data access repository."""

from __future__ import annotations

import sqlite3
from typing import Optional

from src.db.session import normalize_iso8601, require_non_empty, require_positive_limit, utc_now_iso8601
from src.schemas.device import DeviceStatus


class DeviceRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_device_status(self, device: DeviceStatus) -> DeviceStatus:
        require_non_empty(device.id, "device.id")
        require_non_empty(device.device_id, "device.device_id")
        require_non_empty(device.camera_id, "device.camera_id")
        require_non_empty(device.api_key_hash, "device.api_key_hash")

        last_seen = (
            normalize_iso8601(device.last_seen, "device.last_seen")
            if device.last_seen
            else None
        )
        created_at = (
            normalize_iso8601(device.created_at, "device.created_at")
            if device.created_at
            else utc_now_iso8601()
        )
        updated_at = (
            normalize_iso8601(device.updated_at, "device.updated_at")
            if device.updated_at
            else utc_now_iso8601()
        )

        self.conn.execute(
            """
            INSERT INTO devices (
                id, device_id, camera_id, device_name, api_key_hash, status, ip_addr,
                firmware_version, model_version, temperature, cpu_load, npu_load,
                free_mem_mb, camera_fps, last_seen, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                camera_id = excluded.camera_id,
                device_name = excluded.device_name,
                api_key_hash = excluded.api_key_hash,
                status = excluded.status,
                ip_addr = excluded.ip_addr,
                firmware_version = excluded.firmware_version,
                model_version = excluded.model_version,
                temperature = excluded.temperature,
                cpu_load = excluded.cpu_load,
                npu_load = excluded.npu_load,
                free_mem_mb = excluded.free_mem_mb,
                camera_fps = excluded.camera_fps,
                last_seen = excluded.last_seen,
                updated_at = excluded.updated_at
            """,
            (
                device.id,
                device.device_id,
                device.camera_id,
                device.device_name,
                device.api_key_hash,
                device.status,
                device.ip_addr,
                device.firmware_version,
                device.model_version,
                device.temperature,
                device.cpu_load,
                device.npu_load,
                device.free_mem_mb,
                device.camera_fps,
                last_seen,
                created_at,
                updated_at,
            ),
        )
        current = self.get_device_status(device.device_id)
        assert current is not None
        return current

    def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        require_non_empty(device_id, "device_id")
        row = self.conn.execute(
            "SELECT * FROM devices WHERE device_id = ? LIMIT 1", (device_id,)
        ).fetchone()
        return DeviceStatus.from_row(row) if row else None

    def device_status(self, device_id: str) -> Optional[DeviceStatus]:
        return self.get_device_status(device_id)

    def get_device_status_by_camera(self, camera_id: str) -> Optional[DeviceStatus]:
        require_non_empty(camera_id, "camera_id")
        row = self.conn.execute(
            "SELECT * FROM devices WHERE camera_id = ? LIMIT 1",
            (camera_id,),
        ).fetchone()
        return DeviceStatus.from_row(row) if row else None

    def list_devices(
        self,
        *,
        status: str | None = None,
        camera_id: str | None = None,
        limit: int = 50,
    ) -> list[DeviceStatus]:
        require_positive_limit(limit)
        rows = self.conn.execute(
            """
            SELECT *
            FROM devices
            WHERE (? IS NULL OR status = ?)
              AND (? IS NULL OR camera_id = ?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (
                status,
                status,
                camera_id,
                camera_id,
                limit,
            ),
        ).fetchall()
        return [DeviceStatus.from_row(row) for row in rows]
