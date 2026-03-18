from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from PIL import Image

from edge_device.api.server import EdgeDeviceConfig, EdgeDeviceRuntime
from edge_device.capture.camera import CapturedFrame
from edge_device.inference.detector import Detection


class FakeBackendClient:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.heartbeats: list[dict[str, Any]] = []

    def post_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.events.append(payload)
        return {"ok": True, "data": {"accepted": True, "type": "device_ingest_event"}}

    def post_heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.heartbeats.append(payload)
        return {"ok": True, "data": {"accepted": True, "type": "device_heartbeat"}}


class SingleFrameCamera:
    def __init__(self, frame: CapturedFrame) -> None:
        self._frame = frame

    def capture_latest_frame(self) -> CapturedFrame:
        return self._frame


class SlowBackendClient(FakeBackendClient):
    def __init__(self, delay_sec: float = 0.1) -> None:
        super().__init__()
        self.delay_sec = delay_sec

    def post_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        time.sleep(self.delay_sec)
        return super().post_event(payload)


class LowConfidenceDetector:
    def __init__(self) -> None:
        self.model_version = "test-low-conf-detector"
        self.min_confidence = 0.2
        self.last_error: str | None = None

    def detect(self, frame: CapturedFrame) -> list[Detection]:
        return [
            Detection(
                object_name="chair",
                object_class="chair",
                confidence=0.25,
                bbox=(12, 12, 120, 120),
                zone_id="entry_door",
            )
        ]


class MixedClassDetector:
    def __init__(self) -> None:
        self.model_version = "test-mixed-class-detector"
        self.min_confidence = 0.2
        self.last_error: str | None = None

    def detect(self, frame: CapturedFrame) -> list[Detection]:
        return [
            Detection(
                object_name="chair",
                object_class="chair",
                confidence=0.85,
                bbox=(8, 8, 80, 80),
                zone_id="entry_door",
            ),
            Detection(
                object_name="banana",
                object_class="banana",
                confidence=0.86,
                bbox=(16, 16, 96, 96),
                zone_id="entry_door",
            ),
        ]


class EdgeRuntimeUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_edge_t13_")
        root = Path(self.tmp_dir.name)
        self.backend = FakeBackendClient()
        self.runtime = EdgeDeviceRuntime(
            config=EdgeDeviceConfig(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                backend_base_url="http://127.0.0.1:8000",
                snapshot_dir=root / "snapshots",
                clip_dir=root / "clips",
                snapshot_buffer_size=4,
                clip_buffer_size=3,
            ),
            backend_client=self.backend,
        )

    def tearDown(self) -> None:
        self.runtime.close()
        self.tmp_dir.cleanup()

    def test_run_once_posts_backend_event_with_envelope_payload(self) -> None:
        result = self.runtime.run_once(trace_id="trace-edge-run-1")

        self.assertTrue(result["ok"])
        self.assertEqual(result["type"], "edge_run_once")
        self.assertEqual(len(self.backend.events), 1)
        posted = self.backend.events[0]
        self.assertEqual(posted["schema_version"], "edge.event.v1")
        self.assertEqual(posted["device_id"], "rk3566-dev-01")
        self.assertEqual(posted["camera_id"], "cam-entry-01")
        self.assertIn("event_id", posted)
        self.assertIn("objects", posted)
        self.assertIn("object_name", posted)
        self.assertIn("raw_detections", posted)

        envelope = result["data"]["event_envelope"]
        self.assertEqual(envelope["schema"], "vision_butler.edge.event_envelope.v1")
        self.assertEqual(envelope["payload"]["trace_id"], "trace-edge-run-1")
        timings = result["data"]["timings_ms"]
        self.assertIn("capture_ms", timings)
        self.assertIn("detector_infer_ms", timings)
        self.assertIn("emit_ms", timings)
        self.assertIn("total_ms", timings)
        self.assertEqual(result["data"]["backend_post_mode"], "sync")

    def test_heartbeat_payload_is_built_and_sent(self) -> None:
        result = self.runtime.send_heartbeat(trace_id="trace-edge-hb-1")

        self.assertTrue(result["ok"])
        self.assertEqual(len(self.backend.heartbeats), 1)
        payload = self.backend.heartbeats[0]
        self.assertEqual(payload["schema_version"], "edge.heartbeat.v1")
        self.assertEqual(payload["device_id"], "rk3566-dev-01")
        self.assertEqual(payload["camera_id"], "cam-entry-01")
        self.assertEqual(payload["trace_id"], "trace-edge-hb-1")
        self.assertTrue(payload["online"])
        self.assertIn("last_capture_ok", payload)
        self.assertIn("last_upload_ok", payload)
        self.assertIn("last_seen", payload)

    def test_snapshot_and_clip_commands_return_stable_contract(self) -> None:
        snapshot = self.runtime.take_snapshot(trace_id="trace-edge-snapshot-1")
        clip = self.runtime.get_recent_clip(duration_sec=6, trace_id="trace-edge-clip-1")

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["type"], "command_response")
        self.assertEqual(snapshot["schema_version"], "edge.command_response.v1")
        self.assertEqual(snapshot["data"]["command"], "take_snapshot")
        self.assertTrue(snapshot["data"]["snapshot_uri"].startswith("file://"))

        self.assertTrue(clip["ok"])
        self.assertEqual(clip["type"], "command_response")
        self.assertEqual(clip["schema_version"], "edge.command_response.v1")
        self.assertEqual(clip["data"]["command"], "get_recent_clip")
        self.assertEqual(clip["data"]["duration_sec"], 6)
        self.assertTrue(clip["data"]["clip_uri"].startswith("file://"))

    def test_command_id_can_be_provided_by_caller(self) -> None:
        snapshot = self.runtime.take_snapshot(trace_id="trace-edge-snapshot-explicit", command_id="cmd-snapshot-explicit")
        clip = self.runtime.get_recent_clip(
            duration_sec=6,
            trace_id="trace-edge-clip-explicit",
            command_id="cmd-clip-explicit",
        )
        self.assertEqual(snapshot["data"]["command_id"], "cmd-snapshot-explicit")
        self.assertEqual(clip["data"]["command_id"], "cmd-clip-explicit")

    def test_take_snapshot_prefers_real_frame_image_when_available(self) -> None:
        root = Path(self.tmp_dir.name)
        source_image = root / "source.jpg"
        Image.new("RGB", (320, 180), color=(220, 40, 40)).save(source_image, format="JPEG", quality=95)
        frame = CapturedFrame(
            frame_id="frame-000777",
            captured_at="2026-03-14T12:00:00+08:00",
            width=320,
            height=180,
            source="/dev/video0",
            pixel_format="MJPG",
            image_path=str(source_image),
        )
        runtime = EdgeDeviceRuntime(
            config=EdgeDeviceConfig(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                backend_base_url="http://127.0.0.1:8000",
                snapshot_dir=root / "snapshots-real",
                clip_dir=root / "clips-real",
            ),
            backend_client=self.backend,
            camera=SingleFrameCamera(frame),
        )

        snapshot = runtime.take_snapshot(trace_id="trace-edge-real-snapshot")
        snapshot_path = Path(snapshot["data"]["snapshot_path"])
        self.assertTrue(snapshot_path.exists())
        with Image.open(snapshot_path) as image:
            center = image.convert("RGB").getpixel((160, 90))
            self.assertGreater(center[0], 160)
            self.assertLess(center[1], 120)
            self.assertLess(center[2], 120)
        self.assertFalse(source_image.exists(), msg="temporary captured frame artifact should be cleaned")

    def test_run_once_snapshot_can_be_disabled(self) -> None:
        root = Path(self.tmp_dir.name)
        runtime = EdgeDeviceRuntime(
            config=EdgeDeviceConfig(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                backend_base_url="http://127.0.0.1:8000",
                run_once_snapshot_mode="off",
                snapshot_dir=root / "snapshots-off",
                clip_dir=root / "clips-off",
            ),
            backend_client=self.backend,
        )
        try:
            result = runtime.run_once(trace_id="trace-edge-run-off")
            self.assertTrue(result["ok"])
            self.assertIsNone(result["data"]["snapshot_uri"])
        finally:
            runtime.close()

    def test_async_backend_mode_queues_event(self) -> None:
        root = Path(self.tmp_dir.name)
        slow_backend = SlowBackendClient(delay_sec=0.15)
        runtime = EdgeDeviceRuntime(
            config=EdgeDeviceConfig(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                backend_base_url="http://127.0.0.1:8000",
                backend_post_mode="async",
                backend_post_queue_max=2,
                snapshot_dir=root / "snapshots-async",
                clip_dir=root / "clips-async",
            ),
            backend_client=slow_backend,
        )
        try:
            result = runtime.run_once(trace_id="trace-edge-run-async")
            self.assertTrue(result["ok"])
            self.assertEqual(result["data"]["backend_post_mode"], "async")
            self.assertTrue(result["data"]["event_queued"])
            self.assertTrue(result["data"]["backend_response"]["ok"])
        finally:
            runtime.close()

    def test_event_compressor_follows_detector_threshold(self) -> None:
        root = Path(self.tmp_dir.name)
        runtime = EdgeDeviceRuntime(
            config=EdgeDeviceConfig(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                backend_base_url="http://127.0.0.1:8000",
                snapshot_dir=root / "snapshots-conf-sync",
                clip_dir=root / "clips-conf-sync",
            ),
            backend_client=self.backend,
            detector=LowConfidenceDetector(),
        )
        try:
            result = runtime.run_once(trace_id="trace-edge-threshold-sync")
            payload = result["data"]["event_envelope"]["payload"]
            self.assertEqual(payload["event_type"], "object_detected")
            self.assertEqual(len(payload["raw_detections"]), 1)
            self.assertEqual(payload["raw_detections"][0]["object_class"], "chair")
            self.assertNotIn("below_conf_threshold", payload["compress_reason"])
        finally:
            runtime.close()

    def test_class_allowlist_filters_detector_output(self) -> None:
        root = Path(self.tmp_dir.name)
        with patch.dict(
            os.environ,
            {
                "EDGE_DETECT_CLASS_ALLOWLIST": "chair,table",
            },
            clear=False,
        ):
            runtime = EdgeDeviceRuntime(
                config=EdgeDeviceConfig(
                    device_id="rk3566-dev-01",
                    camera_id="cam-entry-01",
                    backend_base_url="http://127.0.0.1:8000",
                    snapshot_dir=root / "snapshots-allowlist",
                    clip_dir=root / "clips-allowlist",
                ),
                backend_client=self.backend,
                detector=MixedClassDetector(),
            )
            try:
                result = runtime.run_once(trace_id="trace-edge-allowlist")
                payload = result["data"]["event_envelope"]["payload"]
                self.assertEqual(result["data"]["detections_raw"], 2)
                self.assertEqual(result["data"]["detections_filtered"], 1)
                self.assertEqual(payload["event_type"], "object_detected")
                self.assertEqual(len(payload["raw_detections"]), 1)
                self.assertEqual(payload["raw_detections"][0]["object_class"], "chair")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
