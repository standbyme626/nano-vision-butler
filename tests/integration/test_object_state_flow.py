from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class ObjectStateFlowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t15_object_state_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "object_state_flow.db")
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

    def test_object_state_refresh_then_state_row_hit(self) -> None:
        self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-object-heartbeat",
            },
        )
        self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "confidence": 0.93,
                "trace_id": "t15-object-ingest",
            },
        )

        first = self.client.get(
            "/memory/object-state",
            params={"object_name": "package", "camera_id": "cam-entry-01", "zone_id": "entry_door"},
        )
        self.assertEqual(first.status_code, 200)
        first_data = first.json()["data"]
        self.assertEqual(first_data["object_name"], "package")
        self.assertEqual(first_data["state_value"], "present")
        self.assertEqual(first_data["reason_code"], "refreshed_from_observation")
        self.assertIn(first_data["freshness_level"], {"fresh", "aging"})

        second = self.client.get(
            "/memory/object-state",
            params={"object_name": "package", "camera_id": "cam-entry-01", "zone_id": "entry_door"},
        )
        self.assertEqual(second.status_code, 200)
        second_data = second.json()["data"]
        self.assertIn(second_data["reason_code"], {"state_row_found", "state_row_found_stale"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
