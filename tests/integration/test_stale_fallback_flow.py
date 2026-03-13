from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class StaleFallbackFlowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t15_stale_fallback_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "stale_fallback_flow.db")
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

    def test_stale_object_realtime_requires_recheck_but_historical_allows(self) -> None:
        self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-stale-heartbeat",
            },
        )
        self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "confidence": 0.9,
                "fresh_until": "2000-01-01T00:00:00.000Z",
                "trace_id": "t15-stale-ingest",
            },
        )

        realtime = self.client.get(
            "/policy/evaluate-staleness",
            params={
                "object_name": "package",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "query_type": "current",
            },
        )
        self.assertEqual(realtime.status_code, 200)
        realtime_data = realtime.json()["data"]
        self.assertTrue(realtime_data["is_stale"])
        self.assertTrue(realtime_data["fallback_required"])
        self.assertEqual(realtime_data["reason_code"], "stale_requires_recheck")

        historical = self.client.get(
            "/policy/evaluate-staleness",
            params={
                "object_name": "package",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "query_type": "historical",
            },
        )
        self.assertEqual(historical.status_code, 200)
        historical_data = historical.json()["data"]
        self.assertTrue(historical_data["is_stale"])
        self.assertFalse(historical_data["fallback_required"])
        self.assertEqual(historical_data["reason_code"], "stale_but_historical_allowed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
