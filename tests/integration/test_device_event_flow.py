from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app
from src.db.repositories.notification_rule_repo import NotificationRuleRepo
from src.schemas.policy import NotificationRule


class DeviceEventFlowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t15_device_event_")
        self.config_dir = Path(self.tmp_dir.name) / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        repo_root = Path(__file__).resolve().parents[2]
        source_config = repo_root / "config"
        for name in [
            "settings.yaml",
            "policies.yaml",
            "access.yaml",
            "devices.yaml",
            "cameras.yaml",
            "aliases.yaml",
        ]:
            content = yaml.safe_load((source_config / name).read_text(encoding="utf-8"))
            if name == "settings.yaml":
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "device_event_flow.db")
            (self.config_dir / name).write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        self.app = create_app(config_dir=self.config_dir)
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tmp_dir.cleanup()

    def test_ingest_event_persists_observation_event_and_audit(self) -> None:
        heartbeat = self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-int-heartbeat",
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        ingest = self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "event_type": "security_alert",
                "importance": 5,
                "confidence": 0.96,
                "trace_id": "t15-int-ingest",
            },
        )
        self.assertEqual(ingest.status_code, 200)
        payload = ingest.json()["data"]
        self.assertTrue(payload["accepted"])
        self.assertTrue(payload["event_promoted"])
        self.assertIsNotNone(payload["observation_id"])
        self.assertIsNotNone(payload["event_id"])

        with self.app.state.session_factory.connect() as conn:
            observations = conn.execute("SELECT COUNT(*) AS total FROM observations").fetchone()["total"]
            events = conn.execute("SELECT COUNT(*) AS total FROM events").fetchone()["total"]
            audits = conn.execute(
                "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'device_ingest_event' AND decision = 'allow'"
            ).fetchone()["total"]
        self.assertEqual(observations, 1)
        self.assertEqual(events, 1)
        self.assertGreaterEqual(audits, 1)

    def test_ingest_event_refreshes_device_liveness(self) -> None:
        observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        heartbeat = self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "offline",
                "last_seen": "2000-01-01T00:00:00Z",
                "trace_id": "t15-int-heartbeat-offline",
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        status_before = self.client.get("/device/status", params={"device_id": "rk3566-dev-01"})
        self.assertEqual(status_before.status_code, 200)
        self.assertFalse(status_before.json()["data"]["is_online"])

        ingest = self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "person",
                "event_type": "object_detected",
                "importance": 4,
                "confidence": 0.88,
                "observed_at": observed_at,
                "trace_id": "t15-int-ingest-refresh",
            },
        )
        self.assertEqual(ingest.status_code, 200)
        self.assertTrue(ingest.json()["data"]["accepted"])

        status_after = self.client.get("/device/status", params={"device_id": "rk3566-dev-01"})
        self.assertEqual(status_after.status_code, 200)
        payload = status_after.json()["data"]
        self.assertTrue(payload["is_online"])
        self.assertEqual(payload["effective_status"], "online")
        self.assertEqual(payload["status"], "online")

    def test_ingest_event_triggers_backend_ocr_when_analysis_requests_present(self) -> None:
        heartbeat = self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-int-heartbeat-analysis",
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        ingest = self.client.post(
            "/device/ingest/event",
            json={
                "schema_version": "edge.event.v1",
                "event_id": "evt-analysis-001",
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "seq_no": 100,
                "captured_at": "2026-03-14T08:00:00Z",
                "sent_at": "2026-03-14T08:00:01Z",
                "event_type": "object_detected",
                "zone_id": "entry_door",
                "snapshot_uri": "file:///tmp/mock_receipt.jpg",
                "objects": [
                    {
                        "object_name": "package",
                        "object_class": "package",
                        "confidence": 0.95,
                        "bbox": [120, 120, 420, 420],
                        "zone_id": "entry_door",
                        "track_id": "trk-00042",
                    }
                ],
                "analysis_profile": "backend_heavy_v1",
                "analysis_required": True,
                "analysis_requests": [
                    {
                        "type": "ocr_quick_read",
                        "reason": "package_detected",
                        "priority": "high",
                        "input_uri": "file:///tmp/mock_receipt.jpg",
                    }
                ],
                "trace_id": "t15-int-ingest-analysis",
            },
        )
        self.assertEqual(ingest.status_code, 200)
        payload = ingest.json()["data"]
        self.assertTrue(payload["accepted"])
        self.assertIsNotNone(payload.get("analysis"))
        self.assertEqual(payload["analysis"]["requested"], 1)
        self.assertEqual(payload["analysis"]["executed"], 1)
        self.assertEqual(payload["analysis"]["failed"], 0)

        with self.app.state.session_factory.connect() as conn:
            ocr_count = conn.execute("SELECT COUNT(*) AS total FROM ocr_results").fetchone()["total"]
            analysis_audits = conn.execute(
                "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'perception_backend_analysis'"
            ).fetchone()["total"]
        self.assertEqual(ocr_count, 1)
        self.assertGreaterEqual(analysis_audits, 1)

    def test_ingest_event_dispatches_state_recheck_requests(self) -> None:
        heartbeat = self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-int-heartbeat-state-recheck",
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        ingest = self.client.post(
            "/device/ingest/event",
            json={
                "schema_version": "edge.event.v1",
                "event_id": "evt-analysis-state-001",
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "seq_no": 101,
                "captured_at": "2026-03-14T08:10:00Z",
                "sent_at": "2026-03-14T08:10:01Z",
                "event_type": "object_detected",
                "zone_id": "entry_door",
                "objects": [
                    {
                        "object_name": "package",
                        "object_class": "package",
                        "confidence": 0.95,
                        "bbox": [100, 100, 400, 400],
                        "zone_id": "entry_door",
                        "track_id": "trk-10001",
                    }
                ],
                "analysis_profile": "backend_heavy_v1",
                "analysis_required": True,
                "analysis_requests": [
                    {"type": "scene_recheck", "reason": "confirm_scene_state"},
                    {"type": "object_state_recheck", "reason": "confirm_object_state"},
                    {"type": "zone_state_recheck", "reason": "confirm_zone_state"},
                ],
                "trace_id": "t15-int-ingest-state-recheck",
            },
        )
        self.assertEqual(ingest.status_code, 200)
        payload = ingest.json()["data"]
        self.assertTrue(payload["accepted"])
        self.assertIsNotNone(payload.get("analysis"))
        self.assertEqual(payload["analysis"]["requested"], 3)
        self.assertEqual(payload["analysis"]["executed"], 3)
        self.assertEqual(payload["analysis"]["failed"], 0)
        self.assertEqual(payload["analysis"]["status"], "ok")
        result_types = {item["type"] for item in payload["analysis"]["results"] if item["status"] == "ok"}
        self.assertIn("scene_recheck", result_types)
        self.assertIn("object_state_recheck", result_types)
        self.assertIn("zone_state_recheck", result_types)

        with self.app.state.session_factory.connect() as conn:
            object_state_count = conn.execute(
                "SELECT COUNT(*) AS total FROM object_states WHERE object_name = ? AND camera_id = ? AND zone_id = ?",
                ("package", "cam-entry-01", "entry_door"),
            ).fetchone()["total"]
            zone_state_count = conn.execute(
                "SELECT COUNT(*) AS total FROM zone_states WHERE camera_id = ? AND zone_id = ?",
                ("cam-entry-01", "entry_door"),
            ).fetchone()["total"]
            audit_row = conn.execute(
                "SELECT meta_json FROM audit_logs WHERE action = 'perception_backend_analysis' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        self.assertGreaterEqual(object_state_count, 1)
        self.assertGreaterEqual(zone_state_count, 1)
        self.assertIsNotNone(audit_row)
        audit_meta = json.loads(audit_row["meta_json"])
        audit_result_types = {item["type"] for item in audit_meta["results"]}
        self.assertIn("scene_recheck", audit_result_types)
        self.assertIn("object_state_recheck", audit_result_types)
        self.assertIn("zone_state_recheck", audit_result_types)

    def test_ingest_event_dispatches_q8_vision_request(self) -> None:
        heartbeat = self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-int-heartbeat-q8",
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        ingest = self.client.post(
            "/device/ingest/event",
            json={
                "schema_version": "edge.event.v1",
                "event_id": "evt-analysis-q8-001",
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "seq_no": 102,
                "captured_at": "2026-03-18T08:20:00Z",
                "sent_at": "2026-03-18T08:20:01Z",
                "event_type": "object_detected",
                "zone_id": "entry_door",
                "snapshot_uri": "file:///tmp/mock_person_q8.jpg",
                "objects": [
                    {
                        "object_name": "person",
                        "object_class": "person",
                        "confidence": 0.96,
                        "bbox": [120, 100, 420, 620],
                        "zone_id": "entry_door",
                        "track_id": "trk-q8-0001",
                    }
                ],
                "analysis_profile": "backend_heavy_v1",
                "analysis_required": True,
                "analysis_requests": [
                    {
                        "type": "vision_q8_describe",
                        "reason": "person_periodic_q8",
                        "input_uri": "file:///tmp/mock_person_q8.jpg",
                        "object_class": "person",
                        "object_name": "person",
                        "track_id": "trk-q8-0001",
                        "camera_id": "cam-entry-01",
                        "zone_id": "entry_door",
                    }
                ],
                "trace_id": "t15-int-ingest-q8",
            },
        )
        self.assertEqual(ingest.status_code, 200)
        payload = ingest.json()["data"]
        self.assertTrue(payload["accepted"])
        self.assertIsNotNone(payload.get("analysis"))
        self.assertEqual(payload["analysis"]["requested"], 1)
        self.assertEqual(payload["analysis"]["executed"], 1)
        self.assertEqual(payload["analysis"]["failed"], 0)
        result = payload["analysis"]["results"][0]
        self.assertEqual(result["type"], "vision_q8_describe")
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(result.get("vision_event_id"))

        with self.app.state.session_factory.connect() as conn:
            vision_events = conn.execute(
                "SELECT COUNT(*) AS total FROM events WHERE event_type = 'vision_q8_described'"
            ).fetchone()["total"]
            audit_row = conn.execute(
                "SELECT meta_json FROM audit_logs WHERE action = 'vision_q8_describe' AND decision = 'allow' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(vision_events, 1)
        self.assertIsNotNone(audit_row)
        audit_meta = json.loads(audit_row["meta_json"])
        self.assertEqual(audit_meta["backend"], "stub")

    def test_ingest_event_triggers_notification_rule_and_respects_cooldown(self) -> None:
        with self.app.state.session_factory.connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    id, telegram_user_id, telegram_chat_id, display_name, username,
                    role, is_allowed, media_scope, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "user-owner-1",
                    "7566115125",
                    "1001",
                    "owner",
                    "owner",
                    "owner",
                    1,
                    "all",
                    "seed for notification test",
                ),
            )
            NotificationRuleRepo(conn).save_rule(
                NotificationRule(
                    id="rule-entry-alert-1",
                    user_id="user-owner-1",
                    rule_name="门口包裹提醒",
                    trigger_type="event",
                    target_scope="entry_door",
                    condition_json=json.dumps(
                        {
                            "event_type": "security_alert",
                            "object_name": "package",
                            "zone_id": "entry_door",
                            "min_importance": 5,
                        },
                        ensure_ascii=False,
                    ),
                    is_enabled=1,
                    cooldown_sec=600,
                    last_triggered_at=None,
                    created_at=None,
                    updated_at=None,
                )
            )

        heartbeat = self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-int-heartbeat-notify",
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        first_ingest = self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "event_type": "security_alert",
                "importance": 5,
                "confidence": 0.97,
                "trace_id": "t15-int-ingest-notify-1",
            },
        )
        self.assertEqual(first_ingest.status_code, 200)
        first_payload = first_ingest.json()["data"]
        self.assertTrue(first_payload["event_promoted"])
        self.assertIsNotNone(first_payload["notifications"])
        self.assertEqual(first_payload["notifications"]["triggered"], 1)
        self.assertEqual(len(first_payload["notifications"]["deliveries"]), 1)

        second_ingest = self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "event_type": "security_alert",
                "importance": 5,
                "confidence": 0.93,
                "trace_id": "t15-int-ingest-notify-2",
            },
        )
        self.assertEqual(second_ingest.status_code, 200)
        second_payload = second_ingest.json()["data"]
        self.assertTrue(second_payload["event_promoted"])
        self.assertIsNotNone(second_payload["notifications"])
        self.assertEqual(second_payload["notifications"]["triggered"], 0)
        self.assertGreaterEqual(second_payload["notifications"]["skipped"], 1)
        reasons = {item["reason"] for item in second_payload["notifications"]["skipped_reasons"]}
        self.assertIn("cooldown_active", reasons)

        with self.app.state.session_factory.connect() as conn:
            triggered = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM audit_logs
                WHERE action = 'notification_dispatch'
                  AND decision = 'allow'
                  AND reason = 'rule_triggered'
                """
            ).fetchone()["total"]
            denied = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM audit_logs
                WHERE action = 'notification_dispatch'
                  AND decision = 'deny'
                  AND reason = 'cooldown_active'
                """
            ).fetchone()["total"]
        self.assertEqual(triggered, 1)
        self.assertGreaterEqual(denied, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
