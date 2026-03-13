from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.repositories.state_repo import StateRepo
from src.db.session import create_connection, initialize_database, utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.schemas.memory import Observation
from src.services.state_service import StateService
from src.settings import load_settings


class StateServiceUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="vision_butler_t15_state_unit_", suffix=".db")
        os.close(fd)
        initialize_database(self.db_path, schema_path="schema.sql")
        self.conn = create_connection(self.db_path)

        repo_root = Path(__file__).resolve().parents[2]
        self.config = load_settings(repo_root / "config")
        self.device_repo = DeviceRepo(self.conn)
        self.observation_repo = ObservationRepo(self.conn)
        self.state_repo = StateRepo(self.conn)
        self.service = StateService(
            state_repo=self.state_repo,
            observation_repo=self.observation_repo,
            conn=self.conn,
            config=self.config,
        )
        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-state-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                device_name="rk3566-front",
                api_key_hash="hash-state",
                status="online",
                ip_addr=None,
                firmware_version=None,
                model_version=None,
                temperature=35.0,
                cpu_load=0.2,
                npu_load=0.1,
                free_mem_mb=2048,
                camera_fps=15,
                last_seen=utc_now_iso8601(),
                created_at=None,
                updated_at=None,
            )
        )
        self._counter = 0

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _save_observation(
        self,
        *,
        object_name: str,
        camera_id: str = "cam-entry-01",
        zone_id: str = "entry_door",
        confidence: float = 0.9,
        state_hint: str = "present",
        observed_at: str | None = None,
        fresh_until: str | None = None,
    ) -> Observation:
        self._counter += 1
        obs = Observation(
            id=f"obs-state-{self._counter}",
            device_id="rk3566-dev-01",
            camera_id=camera_id,
            zone_id=zone_id,
            object_name=object_name,
            object_class="object",
            track_id=None,
            confidence=confidence,
            state_hint=state_hint,
            observed_at=observed_at or utc_now_iso8601(),
            fresh_until=fresh_until or utc_now_iso8601(),
            source_event_id=None,
            snapshot_uri=None,
            clip_uri=None,
            ocr_text=None,
            visibility_scope="private",
            raw_payload_json='{"source":"unit"}',
            created_at=None,
        )
        return self.observation_repo.save_observation(obs)

    @staticmethod
    def _future_iso(minutes: int) -> str:
        dt = datetime.now(tz=timezone.utc) + timedelta(minutes=minutes)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def test_get_object_state_refreshes_from_latest_observation(self) -> None:
        self._save_observation(object_name="package", fresh_until=self._future_iso(5))

        result = self.service.get_object_state(
            object_name="package",
            camera_id="cam-entry-01",
            zone_id="entry_door",
        )

        self.assertEqual(result["object_name"], "package")
        self.assertEqual(result["state_value"], "present")
        self.assertEqual(result["reason_code"], "refreshed_from_observation")
        self.assertEqual(result["evidence_count"], 1)
        self.assertFalse(result["is_stale"])

    def test_get_zone_state_marks_zone_occupied_when_multiple_present(self) -> None:
        self._save_observation(object_name="package", fresh_until=self._future_iso(5))
        self._save_observation(object_name="person", fresh_until=self._future_iso(5))

        result = self.service.get_zone_state(camera_id="cam-entry-01", zone_id="entry_door")

        self.assertEqual(result["state_value"], "occupied")
        self.assertEqual(result["reason_code"], "refreshed_from_zone_observations")
        self.assertGreaterEqual(int(result["evidence_count"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
