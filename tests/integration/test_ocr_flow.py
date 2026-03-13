from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class OCRFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t8_flow_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "ocr_flow.db")
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

    def test_quick_read_and_extract_fields_persist_and_link(self) -> None:
        heartbeat = self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
            },
        )
        self.assertEqual(heartbeat.status_code, 200)

        snapshot = self.client.post(
            "/device/command/take-snapshot",
            json={"device_id": "rk3566-dev-01", "trace_id": "trace-t8-ocr-snapshot"},
        )
        self.assertEqual(snapshot.status_code, 200)
        media_id = snapshot.json()["data"]["data"]["media_id"]

        ingest = self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "event_type": "security_alert",
                "importance": 5,
            },
        )
        self.assertEqual(ingest.status_code, 200)
        event_id = ingest.json()["data"]["event_id"]

        quick = self.client.post("/ocr/quick-read", json={"media_id": media_id})
        self.assertEqual(quick.status_code, 200)
        self.assertTrue(quick.json()["data"]["raw_text"])

        extract = self.client.post(
            "/ocr/extract-fields",
            json={
                "media_id": media_id,
                "event_id": event_id,
                "field_schema": {"name": "string", "zone": "string"},
                "mock_raw_text": "name: parcel, zone: entry_door",
            },
        )
        self.assertEqual(extract.status_code, 200)
        payload = extract.json()["data"]
        self.assertEqual(payload["ocr_mode"], "tool_structured")
        self.assertEqual(payload["fields_json"]["zone"], "entry_door")
        self.assertIsNotNone(payload["source_observation_id"])

        with self.app.state.session_factory.connect() as conn:
            ocr_count = conn.execute(
                "SELECT COUNT(*) FROM ocr_results WHERE source_media_id = ?",
                (media_id,),
            ).fetchone()[0]
            linked_count = conn.execute(
                "SELECT COUNT(*) FROM ocr_results WHERE source_observation_id IS NOT NULL"
            ).fetchone()[0]
        self.assertGreaterEqual(ocr_count, 2)
        self.assertGreaterEqual(linked_count, 1)

    def test_ocr_errors_for_missing_media_and_adapter_failure(self) -> None:
        missing_media = self.client.post("/ocr/quick-read", json={"media_id": "missing-media"})
        self.assertEqual(missing_media.status_code, 400)
        self.assertIn("media_id not found", missing_media.json()["error"]["message"])

        adapter_failure = self.client.post(
            "/ocr/quick-read",
            json={"input_uri": "file://test.jpg", "simulate_failure": True},
        )
        self.assertEqual(adapter_failure.status_code, 400)
        self.assertIn("OCR execution failed", adapter_failure.json()["error"]["message"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
