from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.app import create_app


class DeviceCommandFlowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t7_int_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "integration_test.db")
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

    def test_snapshot_and_clip_flow_with_camera_identifier(self) -> None:
        hb = self.client.post(
            "/device/heartbeat",
            json={"device_id": "rk3566-dev-01", "camera_id": "cam-entry-01", "status": "online"},
        )
        self.assertEqual(hb.status_code, 200)

        snapshot = self.client.post(
            "/device/command/take-snapshot",
            json={"camera_id": "cam-entry-01", "trace_id": "trace-int-snapshot"},
        )
        clip = self.client.post(
            "/device/command/get-recent-clip",
            json={"camera_id": "cam-entry-01", "duration_sec": 6, "trace_id": "trace-int-clip"},
        )

        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(clip.status_code, 200)
        snap_payload = snapshot.json()
        clip_payload = clip.json()
        self.assertTrue(snap_payload["ok"])
        self.assertTrue(clip_payload["ok"])
        self.assertTrue(snap_payload["data"]["ok"])
        self.assertTrue(clip_payload["data"]["ok"])
        self.assertEqual(snap_payload["data"]["data"]["media_type"], "image")
        self.assertEqual(clip_payload["data"]["data"]["media_type"], "video")

        with self.app.state.session_factory.connect() as conn:
            media_count = conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
            audit_count = conn.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE action IN ('device_take_snapshot', 'device_get_recent_clip')"
            ).fetchone()[0]
        self.assertEqual(media_count, 2)
        self.assertEqual(audit_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

