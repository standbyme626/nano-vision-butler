from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class DeviceOfflineAlertE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t15_e2e_offline_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "device_offline_alert.db")
            if name == "access.yaml":
                content["telegram_allowlist"]["user_ids"] = ["42"]
            (self.config_dir / name).write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        self.app = create_app(config_dir=self.config_dir)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.client.post(
            "/device/heartbeat",
            json={
                "device_id": "rk3566-dev-01",
                "camera_id": "cam-entry-01",
                "status": "offline",
                "trace_id": "t15-e2e-offline-heartbeat",
            },
        )

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tmp_dir.cleanup()

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

    def test_snapshot_command_when_device_offline_returns_failed_status(self) -> None:
        response = self.client.post(
            "/telegram/update",
            json=self._build_update(update_id=6601, text="/snapshot rk3566-dev-01"),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["command"], "snapshot")
        self.assertIn("DEVICE_OFFLINE", payload["error"])
        self.assertTrue(payload["outbound_messages"])
        self.assertIn("DEVICE_OFFLINE", payload["outbound_messages"][0]["text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
