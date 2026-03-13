from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class DeviceCommandEdgeBridgeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t13e_")
        self.config_dir = Path(self.tmp_dir.name) / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        repo_root = Path(__file__).resolve().parents[2]
        source_config = repo_root / "config"
        media_root = Path(self.tmp_dir.name) / "edge_media"
        snapshot_dir = media_root / "snapshots"
        clip_dir = media_root / "clips"

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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "edge_bridge.db")
            if name == "devices.yaml":
                for item in content.get("devices", []):
                    if isinstance(item, dict):
                        upload = item.setdefault("upload", {})
                        upload["snapshot_dir"] = str(snapshot_dir)
                        upload["clip_dir"] = str(clip_dir)
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
    def _file_uri_to_path(uri: str) -> Path:
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            raise AssertionError(f"expected file:// URI, got {uri}")
        return Path(parsed.path)

    def test_device_commands_bridge_to_edge_runtime(self) -> None:
        hb = self.client.post(
            "/device/heartbeat",
            json={"device_id": "rk3566-dev-01", "camera_id": "cam-entry-01", "status": "online"},
        )
        self.assertEqual(hb.status_code, 200)

        snapshot = self.client.post(
            "/device/command/take-snapshot",
            json={"device_id": "rk3566-dev-01", "trace_id": "trace-t13e-snapshot"},
        )
        clip = self.client.post(
            "/device/command/get-recent-clip",
            json={"device_id": "rk3566-dev-01", "duration_sec": 6, "trace_id": "trace-t13e-clip"},
        )
        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(clip.status_code, 200)

        snapshot_result = snapshot.json()["data"]
        clip_result = clip.json()["data"]
        self.assertTrue(snapshot_result["ok"])
        self.assertTrue(clip_result["ok"])
        self.assertEqual(snapshot_result["meta"]["adapter"], "edge_command_client")
        self.assertEqual(clip_result["meta"]["adapter"], "edge_command_client")
        self.assertEqual(snapshot_result["meta"]["command_id"], snapshot_result["meta"]["edge_command_id"])
        self.assertEqual(clip_result["meta"]["command_id"], clip_result["meta"]["edge_command_id"])

        snapshot_path = self._file_uri_to_path(snapshot_result["data"]["uri"])
        clip_path = self._file_uri_to_path(clip_result["data"]["uri"])
        self.assertTrue(snapshot_path.exists(), msg=f"snapshot file missing: {snapshot_path}")
        self.assertTrue(clip_path.exists(), msg=f"clip file missing: {clip_path}")

        with self.app.state.session_factory.connect() as conn:
            media_count = conn.execute("SELECT COUNT(*) AS total FROM media_items").fetchone()["total"]
            audit_rows = conn.execute(
                """
                SELECT action, trace_id, meta_json
                FROM audit_logs
                WHERE action IN ('device_take_snapshot', 'device_get_recent_clip')
                ORDER BY created_at ASC
                """
            ).fetchall()
        self.assertEqual(media_count, 2)
        self.assertEqual(len(audit_rows), 2)

        snapshot_audit = next(row for row in audit_rows if row["action"] == "device_take_snapshot")
        clip_audit = next(row for row in audit_rows if row["action"] == "device_get_recent_clip")
        self.assertEqual(snapshot_audit["trace_id"], "trace-t13e-snapshot")
        self.assertEqual(clip_audit["trace_id"], "trace-t13e-clip")

        snapshot_meta = json.loads(snapshot_audit["meta_json"])
        clip_meta = json.loads(clip_audit["meta_json"])
        self.assertEqual(snapshot_meta["command_id"], snapshot_result["meta"]["command_id"])
        self.assertEqual(clip_meta["command_id"], clip_result["meta"]["command_id"])
        self.assertEqual(snapshot_meta["edge_command_id"], snapshot_result["meta"]["edge_command_id"])
        self.assertEqual(clip_meta["edge_command_id"], clip_result["meta"]["edge_command_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
