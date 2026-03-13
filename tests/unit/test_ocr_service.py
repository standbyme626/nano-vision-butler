from __future__ import annotations

import os
import tempfile
import unittest

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.repositories.ocr_repo import OcrRepo
from src.db.session import create_connection, initialize_database, utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.schemas.memory import Event, MediaItem, Observation
from src.services.ocr_service import OCRService


class OCRServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="vision_butler_t8_ocr_", suffix=".db")
        os.close(fd)
        initialize_database(self.db_path, schema_path="schema.sql")
        self.conn = create_connection(self.db_path)

        self.device_repo = DeviceRepo(self.conn)
        self.event_repo = EventRepo(self.conn)
        self.media_repo = MediaRepo(self.conn)
        self.observation_repo = ObservationRepo(self.conn)
        self.ocr_repo = OcrRepo(self.conn)
        self.audit_repo = AuditRepo(self.conn)

        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-1",
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
                id="obs-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                zone_id="entry_door",
                object_name="parcel",
                object_class="package",
                track_id=None,
                confidence=0.9,
                state_hint="present",
                observed_at=utc_now_iso8601(),
                fresh_until=utc_now_iso8601(),
                source_event_id=None,
                snapshot_uri=None,
                clip_uri=None,
                ocr_text=None,
                visibility_scope="private",
                raw_payload_json='{"source":"test"}',
                created_at=None,
            )
        )
        self.event_repo.save_event(
            Event(
                id="evt-1",
                observation_id="obs-1",
                event_type="security_alert",
                category="event",
                importance=4,
                camera_id="cam-entry-01",
                zone_id="entry_door",
                object_name="parcel",
                summary="parcel detected",
                payload_json=None,
                event_at=utc_now_iso8601(),
                created_at=None,
            )
        )
        self.media_repo.save_media_item(
            MediaItem(
                id="media-1",
                owner_type="manual",
                owner_id="cmd-1",
                media_type="image",
                uri="file://snapshot.jpg",
                local_path="/tmp/snapshot.jpg",
                mime_type="image/jpeg",
                duration_sec=None,
                width=1280,
                height=720,
                visibility_scope="private",
                sha256=None,
                created_at=None,
            )
        )

        self.service = OCRService(
            media_repo=self.media_repo,
            observation_repo=self.observation_repo,
            event_repo=self.event_repo,
            ocr_repo=self.ocr_repo,
            audit_repo=self.audit_repo,
        )

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_quick_read_persists_ocr_result(self) -> None:
        result = self.service.quick_read({"media_id": "media-1"})

        self.assertEqual(result["ocr_mode"], "model_direct")
        self.assertTrue(result["raw_text"])
        self.assertEqual(result["source_media_id"], "media-1")
        row = self.conn.execute("SELECT COUNT(*) FROM ocr_results WHERE source_media_id = 'media-1'").fetchone()
        self.assertEqual(row[0], 1)

    def test_extract_fields_links_event_and_observation(self) -> None:
        result = self.service.extract_fields(
            {
                "media_id": "media-1",
                "event_id": "evt-1",
                "field_schema": {"person": "string", "zone": "string"},
                "mock_raw_text": "person: alice, zone: entry_door",
            }
        )

        self.assertEqual(result["ocr_mode"], "tool_structured")
        self.assertEqual(result["source_observation_id"], "obs-1")
        self.assertEqual(result["fields_json"]["person"], "alice")
        obs_row = self.conn.execute("SELECT ocr_text FROM observations WHERE id = 'obs-1'").fetchone()
        self.assertIn("person: alice", obs_row["ocr_text"])

    def test_quick_read_rejects_missing_media_id(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.service.quick_read({"media_id": "missing"})
        self.assertIn("media_id not found", str(ctx.exception))

    def test_extract_fields_handles_ocr_failure(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.service.extract_fields(
                {
                    "media_id": "media-1",
                    "simulate_failure": True,
                }
            )
        self.assertIn("OCR execution failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
