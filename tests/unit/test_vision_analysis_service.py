from __future__ import annotations

import os
import tempfile
import unittest

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.session import create_connection, initialize_database, utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.schemas.memory import Observation
from src.services.vision_analysis_service import StubVisionAdapter, VisionAnalysisService


class VisionAnalysisServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="vision_butler_q8_", suffix=".db")
        os.close(fd)
        initialize_database(self.db_path, schema_path="schema.sql")
        self.conn = create_connection(self.db_path)
        self.device_repo = DeviceRepo(self.conn)
        self.event_repo = EventRepo(self.conn)
        self.media_repo = MediaRepo(self.conn)
        self.observation_repo = ObservationRepo(self.conn)
        self.audit_repo = AuditRepo(self.conn)
        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-q8-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                device_name="rk3566-front",
                api_key_hash="hash",
                status="online",
                ip_addr="127.0.0.1",
                firmware_version="v1",
                model_version="m1",
                temperature=30.0,
                cpu_load=0.2,
                npu_load=0.1,
                free_mem_mb=800,
                camera_fps=10,
                last_seen=utc_now_iso8601(),
                created_at=None,
                updated_at=None,
            )
        )
        self.observation_repo.save_observation(
            Observation(
                id="obs-q8-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                zone_id="entry_door",
                object_name="person",
                object_class="person",
                track_id="trk-q8-1",
                confidence=0.94,
                state_hint="present",
                observed_at=utc_now_iso8601(),
                fresh_until=utc_now_iso8601(),
                source_event_id=None,
                snapshot_uri="file:///tmp/mock_person.jpg",
                clip_uri=None,
                ocr_text=None,
                visibility_scope="private",
                raw_payload_json='{"source":"test"}',
                created_at=None,
            )
        )
        self.service = VisionAnalysisService(
            media_repo=self.media_repo,
            observation_repo=self.observation_repo,
            event_repo=self.event_repo,
            audit_repo=self.audit_repo,
            adapter=StubVisionAdapter(),
        )

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_describe_scene_persists_event_and_audit(self) -> None:
        result = self.service.describe_scene(
            {
                "input_uri": "file:///tmp/mock_person.jpg",
                "observation_id": "obs-q8-1",
                "object_name": "person",
                "object_class": "person",
                "track_id": "trk-q8-1",
                "trace_id": "trace-q8-unit-1",
            }
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["backend"], "stub")
        self.assertTrue(result["summary"])
        self.assertIsNotNone(result["vision_event_id"])

        event_total = self.conn.execute(
            "SELECT COUNT(*) AS total FROM events WHERE event_type = 'vision_q8_described'"
        ).fetchone()["total"]
        audit_total = self.conn.execute(
            "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'vision_q8_describe'"
        ).fetchone()["total"]
        self.assertEqual(event_total, 1)
        self.assertGreaterEqual(audit_total, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
