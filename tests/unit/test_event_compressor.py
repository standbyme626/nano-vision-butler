from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from edge_device.capture.camera import CapturedFrame
from edge_device.compression.event_compressor import EventCompressor
from edge_device.inference.detector import Detection


def _frame() -> CapturedFrame:
    return CapturedFrame(
        frame_id="frame-evt-0001",
        captured_at="2026-03-17T10:00:00Z",
        width=1280,
        height=720,
        source="stub://camera",
        pixel_format="rgb24",
    )


class _TimeSource:
    def __init__(self) -> None:
        self.current = 0.0

    def now(self) -> float:
        return self.current


class EventCompressorUnitTests(unittest.TestCase):
    def test_ocr_allowlist_is_env_configurable(self) -> None:
        frame = _frame()
        with patch.dict(
            os.environ,
            {
                "EDGE_ANALYSIS_ENABLE": "1",
                "EDGE_ANALYSIS_OCR_ENABLE": "1",
                "EDGE_ANALYSIS_MIN_IMPORTANCE_OCR": "4",
                "EDGE_ANALYSIS_OCR_CLASSES": "package",
            },
            clear=False,
        ):
            compressor = EventCompressor(min_confidence=0.35, dedupe_window_sec=0.0, throttle_window_sec=0.0)

        label_detection = Detection(
            object_name="label",
            object_class="label",
            confidence=0.95,
            bbox=(200, 120, 520, 500),
            zone_id="entry_door",
            track_id="trk-00012",
        )
        package_detection = Detection(
            object_name="package",
            object_class="package",
            confidence=0.95,
            bbox=(200, 120, 520, 500),
            zone_id="entry_door",
            track_id="trk-00013",
        )

        label_event = compressor.build_envelope(
            device_id="rk3566-dev-01",
            camera_id="cam-entry-01",
            seq_no=1,
            frame=frame,
            detections=[label_detection],
            snapshot_uri="file:///tmp/label.jpg",
        )
        package_event = compressor.build_envelope(
            device_id="rk3566-dev-01",
            camera_id="cam-entry-01",
            seq_no=2,
            frame=frame,
            detections=[package_detection],
            snapshot_uri="file:///tmp/package.jpg",
        )

        self.assertEqual(label_event["payload"]["analysis_requests"], [])
        self.assertTrue(package_event["payload"]["analysis_required"])
        self.assertEqual(package_event["payload"]["analysis_requests"][0]["type"], "ocr_quick_read")

    def test_signature_cache_is_bounded_for_long_running_runtime(self) -> None:
        frame = _frame()
        time_source = _TimeSource()
        with patch.dict(
            os.environ,
            {
                "EDGE_EVENT_SIGNATURE_CACHE_MAX": "8",
                "EDGE_EVENT_SIGNATURE_RETENTION_SEC": "0.15",
            },
            clear=False,
        ):
            compressor = EventCompressor(
                min_confidence=0.2,
                dedupe_window_sec=0.05,
                throttle_window_sec=0.0,
                time_provider=time_source.now,
            )

        for idx in range(40):
            time_source.current = idx * 0.02
            detection = Detection(
                object_name="person",
                object_class="person",
                confidence=0.9,
                bbox=(100 + idx, 120, 340 + idx, 520),
                zone_id="entry_door",
                track_id=f"trk-{idx:05d}",
            )
            compressor.build_envelope(
                device_id="rk3566-dev-01",
                camera_id="cam-entry-01",
                seq_no=idx + 1,
                frame=frame,
                detections=[detection],
                snapshot_uri="file:///tmp/person.jpg",
            )

        self.assertLessEqual(len(compressor._last_signature_at), 8)

    def test_q8_analysis_request_respects_30s_camera_interval(self) -> None:
        frame = _frame()
        time_source = _TimeSource()
        with patch.dict(
            os.environ,
            {
                "EDGE_ANALYSIS_ENABLE": "1",
                "EDGE_ANALYSIS_OCR_ENABLE": "0",
                "EDGE_ANALYSIS_Q8_ENABLE": "1",
                "EDGE_ANALYSIS_Q8_INTERVAL_SEC": "30",
                "EDGE_ANALYSIS_Q8_CLASSES": "person",
                "EDGE_ANALYSIS_MIN_IMPORTANCE_Q8": "3",
            },
            clear=False,
        ):
            compressor = EventCompressor(
                min_confidence=0.20,
                dedupe_window_sec=0.0,
                throttle_window_sec=0.0,
                time_provider=time_source.now,
            )

        detection = Detection(
            object_name="person",
            object_class="person",
            confidence=0.92,
            bbox=(120, 100, 440, 620),
            zone_id="entry_door",
            track_id="trk-q8-001",
        )

        first_event = compressor.build_envelope(
            device_id="rk3566-dev-01",
            camera_id="cam-entry-01",
            seq_no=1,
            frame=frame,
            detections=[detection],
            snapshot_uri="file:///tmp/person-1.jpg",
        )
        time_source.current = 5.0
        second_event = compressor.build_envelope(
            device_id="rk3566-dev-01",
            camera_id="cam-entry-01",
            seq_no=2,
            frame=frame,
            detections=[detection],
            snapshot_uri="file:///tmp/person-2.jpg",
        )
        time_source.current = 31.0
        third_event = compressor.build_envelope(
            device_id="rk3566-dev-01",
            camera_id="cam-entry-01",
            seq_no=3,
            frame=frame,
            detections=[detection],
            snapshot_uri="file:///tmp/person-3.jpg",
        )

        first_types = [item["type"] for item in first_event["payload"]["analysis_requests"]]
        second_types = [item["type"] for item in second_event["payload"]["analysis_requests"]]
        third_types = [item["type"] for item in third_event["payload"]["analysis_requests"]]

        self.assertIn("vision_q8_describe", first_types)
        self.assertNotIn("vision_q8_describe", second_types)
        self.assertIn("vision_q8_describe", third_types)


if __name__ == "__main__":
    unittest.main(verbosity=2)
