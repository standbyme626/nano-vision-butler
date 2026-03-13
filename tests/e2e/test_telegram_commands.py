from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class TelegramCommandsE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t12_tg_cmd_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "telegram_commands.db")
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
                "trace_id": "seed-heartbeat",
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
                "trace_id": "seed-observation",
            },
        )

    @staticmethod
    def _build_command_update(update_id: int, text: str) -> dict:
        return {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "chat": {"id": 1001},
                "from": {"id": 42},
                "text": text,
            },
        }

    def test_command_matrix(self) -> None:
        commands = [
            ("/snapshot rk3566-dev-01", "snapshot"),
            ("/clip rk3566-dev-01 6", "clip"),
            ("/lastseen package", "lastseen"),
            ("/state package cam-entry-01 entry_door", "state"),
            ("/ocr tg://photo/demo-1.jpg", "ocr"),
            ("/device rk3566-dev-01", "device"),
            ("/help", "help"),
        ]

        for idx, (command_text, expected_command) in enumerate(commands, start=1):
            response = self.client.post(
                "/telegram/update",
                json=self._build_command_update(update_id=5200 + idx, text=command_text),
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()["data"]
            self.assertEqual(payload["status"], "processed")
            self.assertEqual(payload["command"], expected_command)
            self.assertTrue(payload["outbound_messages"])
            self.assertTrue(payload["actions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
