from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

import yaml
from fastapi.testclient import TestClient
from PIL import Image

from edge_device.api.server import EdgeDeviceConfig, EdgeDeviceRuntime
from src.app import create_app


class _BackendRecorder:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.heartbeats: list[dict] = []

    def post_event(self, payload: dict) -> dict:
        self.events.append(payload)
        return {"ok": True, "data": {"accepted": True, "type": "device_ingest_event"}}

    def post_heartbeat(self, payload: dict) -> dict:
        self.heartbeats.append(payload)
        return {"ok": True, "data": {"accepted": True, "type": "device_heartbeat"}}


class EdgeSnapshotRealMediaIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t13d_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "edge_snapshot_media.db")
            (self.config_dir / name).write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        self.app = create_app(config_dir=self.config_dir)
        self.client = TestClient(self.app)
        self.client.__enter__()

        self.backend = _BackendRecorder()
        media_root = Path(self.tmp_dir.name) / "edge_media"
        self.runtime = EdgeDeviceRuntime(
            config=EdgeDeviceConfig(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                backend_base_url="http://127.0.0.1:8000",
                capture_source="stub://camera",
                capture_width=640,
                capture_height=360,
                capture_pixel_format="MJPG",
                snapshot_dir=media_root / "snapshots",
                clip_dir=media_root / "clips",
            ),
            backend_client=self.backend,
        )

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tmp_dir.cleanup()

    @staticmethod
    def _file_uri_to_path(uri: str) -> Path:
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            raise AssertionError(f"expected file:// URI, got: {uri}")
        return Path(parsed.path)

    def test_take_snapshot_writes_real_jpeg_with_expected_dimensions(self) -> None:
        response = self.runtime.take_snapshot(trace_id="trace-t13d-snapshot")
        self.assertTrue(response["ok"])
        snapshot_uri = response["data"]["snapshot_uri"]
        snapshot_path = self._file_uri_to_path(snapshot_uri)

        self.assertTrue(snapshot_path.exists(), msg=f"snapshot file not found: {snapshot_path}")
        self.assertGreater(snapshot_path.stat().st_size, 0, msg="snapshot file is empty")

        with Image.open(snapshot_path) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (640, 360))

    def test_snapshot_uri_roundtrip_to_backend_observation(self) -> None:
        run_once = self.runtime.run_once(trace_id="trace-t13d-run-once")
        self.assertTrue(run_once["ok"])
        self.assertEqual(len(self.backend.events), 1)

        payload = self.backend.events[0]
        self.assertTrue(str(payload["snapshot_uri"]).startswith("file://"))
        ingest = self.client.post("/device/ingest/event", json=payload)
        self.assertEqual(ingest.status_code, 200)
        self.assertTrue(ingest.json()["data"]["accepted"])

        with self.app.state.session_factory.connect() as conn:
            row = conn.execute(
                "SELECT snapshot_uri FROM observations ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            indexed = conn.execute(
                "SELECT COUNT(*) AS total FROM observations WHERE snapshot_uri = ?",
                (payload["snapshot_uri"],),
            ).fetchone()["total"]
        self.assertIsNotNone(row)
        self.assertEqual(row["snapshot_uri"], payload["snapshot_uri"])
        self.assertEqual(indexed, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
