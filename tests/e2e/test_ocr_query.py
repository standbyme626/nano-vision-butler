from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class OCRQueryE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t15_e2e_ocr_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "ocr_query.db")
            if name == "access.yaml":
                content["telegram_allowlist"]["user_ids"] = ["42"]
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

    def test_ocr_command_with_input_uri(self) -> None:
        response = self.client.post(
            "/telegram/update",
            json=self._build_update(update_id=6401, text="/ocr tg://photo/demo-ocr.jpg"),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], "processed")
        self.assertEqual(payload["command"], "ocr")
        self.assertTrue(payload["outbound_messages"])
        text = payload["outbound_messages"][0]["text"]
        self.assertIn("OCR 结果", text)
        self.assertIn("ocr_result_id:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
