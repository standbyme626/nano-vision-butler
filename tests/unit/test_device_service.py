from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.session import create_connection, initialize_database, utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.services.device_service import DeviceExecutionError, DeviceService
from src.settings import load_settings


class DeviceServiceUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="vision_butler_t7_unit_", suffix=".db")
        os.close(fd)
        initialize_database(self.db_path, schema_path="schema.sql")
        self.conn = create_connection(self.db_path)

        repo_root = Path(__file__).resolve().parents[2]
        config = load_settings(repo_root / "config")

        self.device_repo = DeviceRepo(self.conn)
        self.media_repo = MediaRepo(self.conn)
        self.audit_repo = AuditRepo(self.conn)
        self.service = DeviceService(
            device_repo=self.device_repo,
            media_repo=self.media_repo,
            audit_repo=self.audit_repo,
            config=config,
        )

        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-row-unit-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                device_name="rk3566-front",
                api_key_hash="hash-unit",
                status="online",
                ip_addr=None,
                firmware_version=None,
                model_version=None,
                temperature=42.0,
                cpu_load=0.2,
                npu_load=0.1,
                free_mem_mb=1024,
                camera_fps=15,
                last_seen=utc_now_iso8601(),
                created_at=None,
                updated_at=None,
            )
        )

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_take_snapshot_returns_structured_and_persists_media(self) -> None:
        result = self.service.take_snapshot({"device_id": "rk3566-dev-01", "trace_id": "trace-unit-snap"})
        self.assertTrue(result["ok"])
        self.assertIn("summary", result)
        self.assertIn("data", result)
        self.assertIn("meta", result)
        self.assertEqual(result["data"]["media_type"], "image")

        rows = self.media_repo.list_media_for_owner("manual", result["meta"]["command_id"], limit=5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].media_type, "image")

    def test_get_recent_clip_invalid_duration(self) -> None:
        with self.assertRaises(DeviceExecutionError) as ctx:
            self.service.get_recent_clip({"device_id": "rk3566-dev-01", "duration_sec": 0})
        self.assertEqual(ctx.exception.code, "INVALID_DURATION")

    def test_take_snapshot_offline_device(self) -> None:
        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-row-unit-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                device_name="rk3566-front",
                api_key_hash="hash-unit",
                status="offline",
                ip_addr=None,
                firmware_version=None,
                model_version=None,
                temperature=42.0,
                cpu_load=0.2,
                npu_load=0.1,
                free_mem_mb=1024,
                camera_fps=15,
                last_seen=utc_now_iso8601(),
                created_at=None,
                updated_at=None,
            )
        )
        with self.assertRaises(DeviceExecutionError) as ctx:
            self.service.take_snapshot({"device_id": "rk3566-dev-01", "trace_id": "trace-unit-offline"})
        self.assertEqual(ctx.exception.code, "DEVICE_OFFLINE")
        latest_audit = self.audit_repo.list_recent(limit=1)[0]
        self.assertEqual(latest_audit.action, "device_take_snapshot")
        self.assertEqual(latest_audit.decision, "deny")


if __name__ == "__main__":
    unittest.main(verbosity=2)

