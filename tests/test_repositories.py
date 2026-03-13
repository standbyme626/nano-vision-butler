from __future__ import annotations

import os
import tempfile
import unittest

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.repositories.state_repo import StateRepo
from src.db.repositories.telegram_update_repo import TelegramUpdateRepo
from src.db.session import create_connection, initialize_database, utc_now_iso8601
from src.schemas.device import DeviceStatus
from src.schemas.memory import Event, Observation
from src.schemas.security import AuditLog
from src.schemas.state import ObjectState, ZoneState
from src.schemas.telegram import TelegramUpdate


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="vision_butler_t3_", suffix=".db")
        os.close(fd)
        initialize_database(self.db_path, schema_path="schema.sql")
        self.conn = create_connection(self.db_path)

        self.device_repo = DeviceRepo(self.conn)
        self.observation_repo = ObservationRepo(self.conn)
        self.event_repo = EventRepo(self.conn)
        self.state_repo = StateRepo(self.conn)
        self.audit_repo = AuditRepo(self.conn)
        self.telegram_repo = TelegramUpdateRepo(self.conn)

        self.device_repo.save_device_status(
            DeviceStatus(
                id="dev-row-1",
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                device_name="rk3566-front",
                api_key_hash="placeholder-hash",
                status="online",
                ip_addr="127.0.0.1",
                firmware_version="v1",
                model_version="m1",
                temperature=45.5,
                cpu_load=0.42,
                npu_load=0.33,
                free_mem_mb=1024,
                camera_fps=10,
                last_seen=utc_now_iso8601(),
            )
        )

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_observation_and_get_last_seen(self) -> None:
        obs = Observation(
            id="obs-1",
            device_id="rk3566-dev-01",
            camera_id="cam-entry-01",
            zone_id="entry_door",
            object_name="package",
            object_class="parcel",
            track_id="t-1",
            confidence=0.91,
            state_hint="present",
            observed_at=utc_now_iso8601(),
            fresh_until=utc_now_iso8601(),
            source_event_id=None,
            snapshot_uri="file://snapshot.jpg",
            clip_uri=None,
            ocr_text=None,
            visibility_scope="private",
            raw_payload_json='{"k":"v"}',
        )
        self.observation_repo.save_observation(obs)
        last_seen = self.observation_repo.get_last_seen("package")
        self.assertIsNotNone(last_seen)
        assert last_seen is not None
        self.assertEqual(last_seen.id, "obs-1")

    def test_save_event_and_query_recent_events(self) -> None:
        event = Event(
            id="evt-1",
            observation_id=None,
            event_type="motion_detected",
            category="event",
            importance=4,
            camera_id="cam-entry-01",
            zone_id="entry_door",
            object_name="person",
            summary="person at entry",
            payload_json='{"frame":1}',
            event_at=utc_now_iso8601(),
        )
        self.event_repo.save_event(event)

        items = self.event_repo.query_recent_events(zone_id="entry_door", limit=5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "evt-1")

    def test_save_and_get_object_and_zone_state(self) -> None:
        object_state = ObjectState(
            id="os-1",
            object_name="package",
            camera_id="cam-entry-01",
            zone_id="entry_door",
            state_value="present",
            state_confidence=0.8,
            observed_at=utc_now_iso8601(),
            last_confirmed_at=None,
            last_changed_at=None,
            fresh_until=utc_now_iso8601(),
            is_stale=0,
            evidence_count=2,
            source_layer="state",
            summary="package likely present",
        )
        zone_state = ZoneState(
            id="zs-1",
            camera_id="cam-entry-01",
            zone_id="entry_door",
            state_value="occupied",
            state_confidence=0.77,
            observed_at=utc_now_iso8601(),
            fresh_until=utc_now_iso8601(),
            is_stale=0,
            evidence_count=3,
            source_layer="state",
            summary="zone occupied",
        )

        self.state_repo.save_object_state(object_state)
        self.state_repo.save_zone_state(zone_state)

        got_object = self.state_repo.get_object_state(
            object_name="package", camera_id="cam-entry-01", zone_id="entry_door"
        )
        got_zone = self.state_repo.get_zone_state("cam-entry-01", "entry_door")

        self.assertIsNotNone(got_object)
        self.assertIsNotNone(got_zone)
        assert got_object is not None
        assert got_zone is not None
        self.assertEqual(got_object.state_value, "present")
        self.assertEqual(got_zone.state_value, "occupied")

    def test_get_device_status(self) -> None:
        status = self.device_repo.get_device_status("rk3566-dev-01")
        self.assertIsNotNone(status)
        assert status is not None
        self.assertEqual(status.status, "online")
        self.assertEqual(self.device_repo.device_status("rk3566-dev-01").device_id, "rk3566-dev-01")

    def test_save_audit_log(self) -> None:
        saved = self.audit_repo.save_audit_log(
            AuditLog(
                id="audit-1",
                user_id=None,
                device_id="rk3566-dev-01",
                action="request_snapshot",
                target_type="camera",
                target_id="cam-entry-01",
                decision="allow",
                reason="policy allows",
                trace_id="trace-1",
                meta_json='{"reason":"ok"}',
            )
        )
        self.assertEqual(saved.id, "audit-1")
        self.assertEqual(self.audit_repo.list_recent(limit=1)[0].id, "audit-1")

    def test_telegram_update_dedup_and_status_markers(self) -> None:
        update = TelegramUpdate(
            id="tg-1",
            update_id="10001",
            chat_id="chat-1",
            from_user_id="user-1",
            message_type="message",
            message_text="hello",
            received_at=None,
            processed_at=None,
            status="received",
            error_message=None,
            trace_id="trace-tg",
        )

        inserted_first = self.telegram_repo.save_telegram_update(update)
        inserted_second = self.telegram_repo.save_telegram_update(update)

        self.assertTrue(inserted_first)
        self.assertFalse(inserted_second)

        marked_processed = self.telegram_repo.mark_telegram_update_processed("10001")
        self.assertTrue(marked_processed)
        record = self.telegram_repo.get_by_update_id("10001")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.status, "processed")

        marked_failed = self.telegram_repo.mark_telegram_update_failed("10001", "timeout")
        self.assertTrue(marked_failed)
        record = self.telegram_repo.get_by_update_id("10001")
        assert record is not None
        self.assertEqual(record.status, "failed")
        self.assertEqual(record.error_message, "timeout")


if __name__ == "__main__":
    unittest.main(verbosity=2)
