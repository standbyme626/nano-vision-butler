from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class TelegramMessageFlowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t12_tg_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "telegram_flow.db")
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
    def _build_update(
        *,
        update_id: int,
        user_id: int = 42,
        chat_id: int = 1001,
        text: str | None = None,
        photo_file_id: str | None = None,
        video_file_id: str | None = None,
        caption: str | None = None,
    ) -> dict:
        message: dict = {
            "message_id": update_id,
            "chat": {"id": chat_id},
            "from": {"id": user_id},
        }
        if text is not None:
            message["text"] = text
        if caption is not None:
            message["caption"] = caption
        if photo_file_id is not None:
            message["photo"] = [{"file_id": "small"}, {"file_id": photo_file_id}]
        if video_file_id is not None:
            message["video"] = {"file_id": video_file_id}
        return {"update_id": update_id, "message": message}

    def test_help_dedup_and_status_transition(self) -> None:
        payload = self._build_update(update_id=5101, text="/help")
        first = self.client.post("/telegram/update", json=payload)
        second = self.client.post("/telegram/update", json=payload)

        self.assertEqual(first.status_code, 200)
        first_data = first.json()["data"]
        self.assertTrue(first_data["ok"])
        self.assertEqual(first_data["status"], "processed")
        self.assertEqual(first_data["command"], "help")
        self.assertTrue(first_data["outbound_messages"])
        self.assertEqual(first_data["actions"][0]["method"], "sendChatAction")

        self.assertEqual(second.status_code, 200)
        second_data = second.json()["data"]
        self.assertEqual(second_data["status"], "ignored_duplicate")
        self.assertTrue(second_data["deduplicated"])

        with self.app.state.session_factory.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total, MAX(status) AS status FROM telegram_updates WHERE update_id = ?",
                ("5101",),
            ).fetchone()
        self.assertEqual(row["total"], 1)
        self.assertEqual(row["status"], "processed")

    def test_photo_branch_routes_to_ocr_and_marks_processed(self) -> None:
        payload = self._build_update(update_id=5102, photo_file_id="photo_large_001")
        response = self.client.post("/telegram/update", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["message_type"], "photo")
        self.assertEqual(data["actions"][0]["action"], "upload_photo")
        self.assertIn("OCR", data["outbound_messages"][0]["text"])

        with self.app.state.session_factory.connect() as conn:
            row = conn.execute(
                "SELECT status FROM telegram_updates WHERE update_id = ? LIMIT 1",
                ("5102",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "processed")

    def test_failed_command_marks_failed_status(self) -> None:
        payload = self._build_update(update_id=5103, text="/lastseen")
        response = self.client.post("/telegram/update", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "failed")
        self.assertIn("object_name", data["error"])

        with self.app.state.session_factory.connect() as conn:
            row = conn.execute(
                "SELECT status, error_message FROM telegram_updates WHERE update_id = ? LIMIT 1",
                ("5103",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "failed")
        self.assertIn("object_name", row["error_message"])

    def test_long_text_reply_is_chunked(self) -> None:
        long_text = "Q" * 9000
        payload = self._build_update(update_id=5104, text=long_text)
        response = self.client.post("/telegram/update", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "processed")
        self.assertGreater(len(data["outbound_messages"]), 1)
        self.assertTrue(all(len(item["text"]) <= 3500 for item in data["outbound_messages"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
