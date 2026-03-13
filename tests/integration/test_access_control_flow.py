from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app
from src.db.repositories.media_repo import MediaRepo
from src.mcp_server.server import create_server
from src.schemas.memory import MediaItem


class AccessControlFlowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t14_access_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "access_test.db")
            if name == "access.yaml":
                content["telegram_allowlist"]["user_ids"] = ["42"]
                content["user_roles"] = {"42": "viewer"}
                content["roles"]["viewer"]["can_view_all"] = False
                content["tool_allowlist_per_skill"] = {
                    "telegram": ["device_status"],
                    "media_skill": ["ocr_quick_read"],
                    "audit_skill": ["query_recent_events"],
                }
                content["resource_scope_per_skill"] = {
                    "audit_skill": ["resource://memory/events"],
                }
                content["media_visibility_scope"] = {
                    "viewer": ["public"],
                    "owner": ["private", "public"],
                }
            (self.config_dir / name).write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        self.app = create_app(config_dir=self.config_dir)
        self.client = TestClient(self.app)
        self.client.__enter__()

        self.server = create_server(config_dir=self.config_dir)
        with self.app.state.session_factory.connect() as conn:
            MediaRepo(conn).save_media_item(
                MediaItem(
                    id="media-private-1",
                    owner_type="manual",
                    owner_id="cmd-1",
                    media_type="image",
                    uri="file://private.jpg",
                    local_path="/tmp/private.jpg",
                    mime_type="image/jpeg",
                    duration_sec=None,
                    width=100,
                    height=100,
                    visibility_scope="private",
                    sha256=None,
                    created_at=None,
                )
            )

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tmp_dir.cleanup()

    @staticmethod
    def _update_payload(*, update_id: int, user_id: int, text: str) -> dict:
        return {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "chat": {"id": 1001},
                "from": {"id": user_id},
                "text": text,
            },
        }

    def test_non_allowlist_user_is_denied_and_audited(self) -> None:
        response = self.client.post(
            "/telegram/update",
            json=self._update_payload(update_id=7001, user_id=99, text="/help"),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], "failed")
        self.assertIn("USER_NOT_ALLOWED", payload["error"])

        with self.app.state.session_factory.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'telegram_user_access' AND decision = 'deny' AND reason = 'USER_NOT_ALLOWED'"
            ).fetchone()
        self.assertGreaterEqual(row["total"], 1)

    def test_non_allowlist_device_is_denied_and_audited(self) -> None:
        response = self.client.post(
            "/device/heartbeat",
            json={"device_id": "rogue-dev-01", "status": "online", "trace_id": "t14-device-deny"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("DEVICE_NOT_ALLOWED", response.json()["error"]["message"])

        with self.app.state.session_factory.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'device_heartbeat' AND decision = 'deny' AND reason = 'DEVICE_NOT_ALLOWED'"
            ).fetchone()
        self.assertGreaterEqual(row["total"], 1)

    def test_tool_resource_and_media_access_controls(self) -> None:
        tool_denied = self.server.call_tool(
            "take_snapshot",
            {
                "skill_name": "telegram",
                "user_id": "42",
                "device_id": "rk3566-dev-01",
                "trace_id": "t14-tool-deny",
            },
        )
        self.assertFalse(tool_denied["ok"])
        self.assertIn("TOOL_NOT_ALLOWED", tool_denied["summary"])

        resource_denied = self.server.read_resource(
            "resource://devices/status",
            {
                "skill_name": "audit_skill",
                "user_id": "42",
                "trace_id": "t14-resource-deny",
            },
        )
        self.assertFalse(resource_denied["ok"])
        self.assertIn("RESOURCE_NOT_ALLOWED", resource_denied["summary"])

        media_denied = self.server.call_tool(
            "ocr_quick_read",
            {
                "skill_name": "media_skill",
                "user_id": "42",
                "media_id": "media-private-1",
                "trace_id": "t14-media-deny",
            },
        )
        self.assertFalse(media_denied["ok"])
        self.assertIn("MEDIA_SCOPE_DENIED", media_denied["summary"])

        with self.app.state.session_factory.connect() as conn:
            counts = {
                "tool": conn.execute(
                    "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'tool_access' AND decision = 'deny'"
                ).fetchone()["total"],
                "resource": conn.execute(
                    "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'resource_access' AND decision = 'deny'"
                ).fetchone()["total"],
                "media": conn.execute(
                    "SELECT COUNT(*) AS total FROM audit_logs WHERE action = 'media_access' AND decision = 'deny'"
                ).fetchone()["total"],
            }
        self.assertGreaterEqual(counts["tool"], 1)
        self.assertGreaterEqual(counts["resource"], 1)
        self.assertGreaterEqual(counts["media"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
