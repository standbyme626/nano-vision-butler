from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.session import create_connection, initialize_database
from src.schemas.device import DeviceStatus
from src.services.memory_service import MemoryService
from src.settings import load_settings


class MemoryServiceUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="vision_butler_t15_memory_unit_", suffix=".db")
        os.close(fd)
        initialize_database(self.db_path, schema_path="schema.sql")
        self.conn = create_connection(self.db_path)

        repo_root = Path(__file__).resolve().parents[2]
        config = load_settings(repo_root / "config")
        self.device_repo = DeviceRepo(self.conn)
        self.observation_repo = ObservationRepo(self.conn)
        self.event_repo = EventRepo(self.conn)
        self.service = MemoryService(
            observation_repo=self.observation_repo,
            event_repo=self.event_repo,
            config=config,
        )
        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-memory-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                device_name="rk3566-front",
                api_key_hash="hash-memory",
                status="online",
                ip_addr=None,
                firmware_version=None,
                model_version=None,
                temperature=33.0,
                cpu_load=0.2,
                npu_load=0.1,
                free_mem_mb=1024,
                camera_fps=12,
                last_seen="2026-01-01T00:00:00.000Z",
                created_at=None,
                updated_at=None,
            )
        )

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_observation_uses_configured_freshness_override(self) -> None:
        observation = self.service.save_observation_from_payload(
            {
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "person",
                "observed_at": "2026-01-01T00:00:00.000Z",
            }
        )

        observed_at = datetime.fromisoformat(observation.observed_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        fresh_until = datetime.fromisoformat(observation.fresh_until.replace("Z", "+00:00")).astimezone(timezone.utc)
        self.assertEqual(int((fresh_until - observed_at).total_seconds()), 30)

    def test_promote_observation_if_needed_creates_event(self) -> None:
        observation = self.service.save_observation_from_payload(
            {
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "observed_at": "2026-01-01T00:00:00.000Z",
            }
        )

        promoted = self.service.promote_observation_if_needed(
            {
                "importance": 5,
                "event_type": "security_alert",
                "zone_id": "entry_door",
                "summary": "high priority package event",
                "event_at": "2026-01-01T00:00:00.000Z",
            },
            observation,
        )

        self.assertIsNotNone(promoted)
        assert promoted is not None
        self.assertEqual(promoted.importance, 5)
        self.assertEqual(promoted.event_type, "security_alert")
        self.assertEqual(promoted.summary, "high priority package event")


if __name__ == "__main__":
    unittest.main(verbosity=2)
