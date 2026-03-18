from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.repositories.state_repo import StateRepo
from src.db.session import create_connection, initialize_database, utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.schemas.memory import Observation
from src.services.policy_service import PolicyService
from src.services.state_service import StateService
from src.settings import load_settings


class PolicyServiceUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="vision_butler_t15_policy_unit_", suffix=".db")
        os.close(fd)
        initialize_database(self.db_path, schema_path="schema.sql")
        self.conn = create_connection(self.db_path)

        repo_root = Path(__file__).resolve().parents[2]
        self.config = load_settings(repo_root / "config")
        self.device_repo = DeviceRepo(self.conn)
        self.observation_repo = ObservationRepo(self.conn)
        self.state_repo = StateRepo(self.conn)
        self.state_service = StateService(
            state_repo=self.state_repo,
            observation_repo=self.observation_repo,
            conn=self.conn,
            config=self.config,
        )
        self.service = PolicyService(
            state_service=self.state_service,
            device_repo=self.device_repo,
            config=self.config,
        )

        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-policy-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                device_name="rk3566-front",
                api_key_hash="hash-policy",
                status="online",
                ip_addr=None,
                firmware_version=None,
                model_version=None,
                temperature=32.0,
                cpu_load=0.3,
                npu_load=0.2,
                free_mem_mb=2048,
                camera_fps=12,
                last_seen=utc_now_iso8601(),
                created_at=None,
                updated_at=None,
            )
        )

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _save_stale_observation(self, *, object_name: str) -> None:
        self.observation_repo.save_observation(
            Observation(
                id="obs-policy-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                zone_id="entry_door",
                object_name=object_name,
                object_class="object",
                track_id=None,
                confidence=0.95,
                state_hint="present",
                observed_at="2026-01-01T00:00:00.000Z",
                fresh_until="2000-01-01T00:00:00.000Z",
                source_event_id=None,
                snapshot_uri=None,
                clip_uri=None,
                ocr_text=None,
                visibility_scope="private",
                raw_payload_json='{"source":"unit"}',
                created_at=None,
            )
        )

    def test_evaluate_staleness_realtime_stale_requires_recheck(self) -> None:
        decision = self.service.evaluate_staleness(
            query_recency_class="realtime",
            fresh_until="2000-01-01T00:00:00.000Z",
            device_status="online",
            now="2026-03-13T00:00:00.000Z",
        )

        self.assertTrue(decision["is_stale"])
        self.assertTrue(decision["fallback_required"])
        self.assertEqual(decision["reason_code"], "stale_requires_recheck")
        self.assertEqual(decision["freshness_level"], "stale")

    def test_evaluate_staleness_for_object_historical_allows_stale_answer(self) -> None:
        self._save_stale_observation(object_name="package")

        decision = self.service.evaluate_staleness_for_object(
            object_name="package",
            camera_id="cam-entry-01",
            zone_id="entry_door",
            query_type="historical",
            now="2026-03-13T00:00:00.000Z",
        )

        self.assertEqual(decision["object_name"], "package")
        self.assertEqual(decision["recency_class"], "historical")
        self.assertTrue(decision["is_stale"])
        self.assertFalse(decision["fallback_required"])
        self.assertEqual(decision["reason_code"], "stale_but_historical_allowed")
        self.assertEqual(decision["freshness_level"], "stale")
        self.assertIn("reason_codes", decision)
        self.assertEqual(decision["reason_codes"]["policy"], "stale_but_historical_allowed")
        self.assertTrue(decision["state_reason_code"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
