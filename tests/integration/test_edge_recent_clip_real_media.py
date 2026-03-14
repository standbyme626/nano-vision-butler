from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from edge_device.api.server import EdgeDeviceConfig, EdgeDeviceRuntime
from edge_device.cache.ring_buffer import ClipItem, MediaRingBuffer


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


class EdgeRecentClipRealMediaIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t13h_")
        media_root = Path(self.tmp_dir.name) / "edge_media"
        self.backend = _BackendRecorder()
        self.runtime = EdgeDeviceRuntime(
            config=EdgeDeviceConfig(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                backend_base_url="http://127.0.0.1:8000",
                capture_source="stub://camera",
                capture_width=640,
                capture_height=360,
                capture_fps=10,
                snapshot_dir=media_root / "snapshots",
                clip_dir=media_root / "clips",
                clip_buffer_size=2,
            ),
            backend_client=self.backend,
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    @staticmethod
    def _file_uri_to_path(uri: str) -> Path:
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            raise AssertionError(f"expected file:// URI, got: {uri}")
        return Path(parsed.path)

    def test_recent_clip_is_real_playable_mp4_and_duration_matches_request(self) -> None:
        self.runtime.run_once(trace_id="trace-t13h-prime")
        result = self.runtime.get_recent_clip(duration_sec=4, trace_id="trace-t13h-clip")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["duration_sec"], 4)

        clip_path = self._file_uri_to_path(result["data"]["clip_uri"])
        self.assertTrue(clip_path.exists(), msg=f"clip file not found: {clip_path}")
        self.assertEqual(clip_path.suffix.lower(), ".mp4")
        self.assertGreater(clip_path.stat().st_size, 0, msg="clip file is empty")

        import cv2

        capture = cv2.VideoCapture(str(clip_path))
        try:
            self.assertTrue(capture.isOpened(), msg="generated clip is not playable by OpenCV")
            fps = capture.get(cv2.CAP_PROP_FPS)
            frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        finally:
            capture.release()

        self.assertGreater(fps, 0.0)
        self.assertGreater(frame_count, 0.0)
        duration = frame_count / fps
        self.assertGreaterEqual(duration, 3.0)
        self.assertLessEqual(duration, 5.0)
        self.assertIn("cache_metrics", result["data"])

    def test_ring_buffer_eviction_policy_is_observable_and_reproducible(self) -> None:
        buffer = MediaRingBuffer(snapshot_capacity=2, clip_capacity=2)
        buffer.add_clip(ClipItem("clip-1", "2026-03-14T10:00:00Z", "2026-03-14T10:00:03Z", 3, "/tmp/c1.mp4", "file:///tmp/c1.mp4"))
        buffer.add_clip(ClipItem("clip-2", "2026-03-14T10:00:03Z", "2026-03-14T10:00:09Z", 6, "/tmp/c2.mp4", "file:///tmp/c2.mp4"))
        buffer.add_clip(ClipItem("clip-3", "2026-03-14T10:00:09Z", "2026-03-14T10:00:17Z", 8, "/tmp/c3.mp4", "file:///tmp/c3.mp4"))

        metrics = buffer.cache_metrics()
        self.assertEqual(metrics["clip_count"], 2)
        self.assertEqual(metrics["clip_evictions"], 1)

        duration_match = buffer.get_recent_clip(5)
        self.assertIsNotNone(duration_match)
        self.assertEqual(duration_match.clip_id, "clip-2")

        duration_fallback = buffer.get_recent_clip(9)
        self.assertIsNotNone(duration_fallback)
        self.assertEqual(duration_fallback.clip_id, "clip-3")

        lookup = buffer.cache_metrics()["last_clip_lookup"]
        self.assertIsNotNone(lookup)
        self.assertEqual(lookup["decision"], "duration_fallback_latest")
        self.assertEqual(lookup["selected_clip_id"], "clip-3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
