from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class ObjectStateQueryE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t15_e2e_object_state_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "object_state_query.db")
            if name == "access.yaml":
                content["telegram_allowlist"]["user_ids"] = ["42"]
            (self.config_dir / name).write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        self.app = create_app(config_dir=self.config_dir)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self._seed_runtime_data()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tmp_dir.cleanup()

    def _seed_runtime_data(self) -> None:
        self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "online",
                "trace_id": "t15-e2e-state-heartbeat",
            },
        )
        self.client.post(
            "/device/ingest/event",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "object_name": "package",
                "confidence": 0.94,
                "trace_id": "t15-e2e-state-ingest",
            },
        )

    @staticmethod
    def _build_update(update_id: int, text: str) -> dict:
        return {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "chat": {"id": 1001},
                "from": {"id": 42},
                "text": text,
            },
        }

    def test_object_state_command(self) -> None:
        response = self.client.post(
            "/telegram/update",
            json=self._build_update(update_id=6301, text="/state package cam-entry-01 entry_door"),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], "processed")
        self.assertEqual(payload["command"], "state")
        self.assertTrue(payload["outbound_messages"])
        text = payload["outbound_messages"][0]["text"]
        self.assertIn("对象状态", text)
        self.assertIn("state_value:", text)

    def test_object_state_text_query_routes_to_state_plus_staleness(self) -> None:
        response = self.client.post(
            "/telegram/update",
            json=self._build_update(update_id=6302, text="package现在还在不在？"),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], "processed")
        text = payload["outbound_messages"][0]["text"]
        self.assertIn("当前环境结构化结论", text)
        self.assertIn("调用链: get_object_state -> evaluate_staleness", text)
        self.assertIn("新鲜度:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
