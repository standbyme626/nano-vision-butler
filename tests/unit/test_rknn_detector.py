from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from edge_device.capture.camera import StubCamera
from edge_device.inference.detector import LightweightDetector, create_detector_from_env
from edge_device.inference.rknn_detector import (
    COCO80_LABELS,
    RKNNDetector,
    RKNNDetectorConfig,
    create_rknn_detector_from_env,
)


class _FakeRuntime:
    def __init__(self, outputs):
        self._outputs = outputs

    def inference(self, inputs):  # noqa: ANN001
        del inputs
        return self._outputs


class _FailRuntime:
    def inference(self, inputs):  # noqa: ANN001
        del inputs
        raise RuntimeError("infer failed")


class RKNNDetectorTests(unittest.TestCase):
    def test_factory_rknn_backend_degrades_when_model_missing(self) -> None:
        old_backend = os.environ.get("EDGE_DETECTOR_BACKEND")
        old_path = os.environ.get("EDGE_RKNN_MODEL_PATH")
        try:
            os.environ["EDGE_DETECTOR_BACKEND"] = "rknn"
            os.environ["EDGE_RKNN_MODEL_PATH"] = "/tmp/not_found_model_for_test.rknn"
            detector = create_detector_from_env()
        finally:
            if old_backend is None:
                os.environ.pop("EDGE_DETECTOR_BACKEND", None)
            else:
                os.environ["EDGE_DETECTOR_BACKEND"] = old_backend
            if old_path is None:
                os.environ.pop("EDGE_RKNN_MODEL_PATH", None)
            else:
                os.environ["EDGE_RKNN_MODEL_PATH"] = old_path

        frame = StubCamera(width=640, height=360).capture_latest_frame()
        detections = detector.detect(frame)
        self.assertTrue(detections)
        self.assertEqual(detector.model_version, "stub-detector-v1")
        self.assertIsNotNone(detector.last_error)

    def test_decode_fake_runtime_output_to_detection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vision_butler_rknn_unit_") as tmp:
            model_path = Path(tmp) / "main_detector.rknn"
            model_path.write_text("dummy", encoding="utf-8")
            detector = RKNNDetector(
                config=RKNNDetectorConfig(
                    model_path=model_path,
                    model_version="rknn-main-v1",
                    min_confidence=0.3,
                    labels=("person", "package"),
                ),
                runtime=_FakeRuntime(outputs=[[[120, 100, 420, 300, 0.92, 0]]]),
            )

            frame = StubCamera(width=640, height=360).capture_latest_frame()
            detections = detector.detect(frame)
            self.assertEqual(len(detections), 1)
            self.assertEqual(detections[0].object_class, "person")
            self.assertGreater(detections[0].confidence, 0.9)
            self.assertEqual(detector.model_version, "rknn-main-v1")
            self.assertIsNone(detector.last_error)

    def test_inference_failure_falls_back_and_records_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vision_butler_rknn_unit_") as tmp:
            model_path = Path(tmp) / "main_detector.rknn"
            model_path.write_text("dummy", encoding="utf-8")
            fallback = LightweightDetector(model_version="fallback-detector-v1")
            detector = RKNNDetector(
                config=RKNNDetectorConfig(model_path=model_path, model_version="rknn-main-v1"),
                runtime=_FailRuntime(),
                fallback_detector=fallback,
            )

            frame = StubCamera(width=640, height=360).capture_latest_frame()
            detections = detector.detect(frame)
            self.assertTrue(detections)
            self.assertEqual(detector.model_version, "fallback-detector-v1")
            self.assertIn("rknn_inference_failed", detector.last_error or "")

    def test_decode_rkopt_outputs_to_detection_and_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vision_butler_rknn_unit_") as tmp:
            model_path = Path(tmp) / "main_detector.rknn"
            model_path.write_text("dummy", encoding="utf-8")
            zero_pos = np.zeros((1, 64, 1, 1), dtype=np.float32)
            cls_hit = np.array([[[[0.95]], [[0.05]]]], dtype=np.float32)
            cls_miss = np.array([[[[0.05]], [[0.05]]]], dtype=np.float32)
            sum_hit = np.array([[[[0.95]]]], dtype=np.float32)
            sum_miss = np.array([[[[0.05]]]], dtype=np.float32)
            detector = RKNNDetector(
                config=RKNNDetectorConfig(
                    model_path=model_path,
                    model_version="yolov8n-rkopt-i8",
                    min_confidence=0.3,
                    labels=("person", "package"),
                ),
                runtime=_FakeRuntime(
                    outputs=[
                        zero_pos,
                        cls_hit,
                        sum_hit,
                        zero_pos,
                        cls_miss,
                        sum_miss,
                        zero_pos,
                        cls_miss,
                        sum_miss,
                    ]
                ),
            )

            frame = StubCamera(width=640, height=360).capture_latest_frame()
            detections = detector.detect(frame)
            self.assertEqual(len(detections), 1)
            self.assertEqual(detections[0].object_class, "person")
            self.assertGreaterEqual(detections[0].confidence, 0.9)
            self.assertEqual(detector.model_version, "yolov8n-rkopt-i8")
            self.assertIsNotNone(detector.last_profile)
            self.assertIn("infer_ms", detector.last_profile or {})

    def test_decode_yolov8_flat_output_to_detection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vision_butler_rknn_unit_") as tmp:
            model_path = Path(tmp) / "oiv7_detector.rknn"
            model_path.write_text("dummy", encoding="utf-8")
            # shape: (1, C, N), C = 4 box + 2 classes
            flat = np.array(
                [
                    [
                        [320.0, 320.0, 120.0],  # cx
                        [320.0, 320.0, 120.0],  # cy
                        [200.0, 180.0, 40.0],   # w
                        [120.0, 100.0, 40.0],   # h
                        [0.91, 0.15, 0.05],     # cls0
                        [0.09, 0.82, 0.10],     # cls1
                    ]
                ],
                dtype=np.float32,
            )
            detector = RKNNDetector(
                config=RKNNDetectorConfig(
                    model_path=model_path,
                    model_version="yolov8n-oiv7",
                    min_confidence=0.3,
                    labels=("class0", "class1"),
                ),
                runtime=_FakeRuntime(outputs=[flat]),
            )

            frame = StubCamera(width=640, height=640).capture_latest_frame()
            detections = detector.detect(frame)
            self.assertEqual(len(detections), 2)
            self.assertEqual(detections[0].object_class, "class0")
            self.assertEqual(detections[1].object_class, "class1")
            self.assertGreaterEqual(detections[0].confidence, 0.9)
            self.assertGreaterEqual(detections[1].confidence, 0.8)

    def test_decode_yolov8_flat_all_zero_class_head_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vision_butler_rknn_unit_") as tmp:
            model_path = Path(tmp) / "oiv7_detector.rknn"
            model_path.write_text("dummy", encoding="utf-8")
            flat = np.array(
                [
                    [
                        [320.0],
                        [320.0],
                        [120.0],
                        [80.0],
                        [0.0],
                        [0.0],
                    ]
                ],
                dtype=np.float32,
            )
            detector = RKNNDetector(
                config=RKNNDetectorConfig(
                    model_path=model_path,
                    model_version="yolov8n-oiv7",
                    min_confidence=0.2,
                    labels=("class0", "class1"),
                ),
                runtime=_FakeRuntime(outputs=[flat]),
            )

            frame = StubCamera(width=640, height=640).capture_latest_frame()
            detections = detector.detect(frame)
            self.assertEqual(detections, [])

    def test_empty_model_path_env_falls_back_to_default_path(self) -> None:
        old_backend = os.environ.get("EDGE_DETECTOR_BACKEND")
        old_model_path = os.environ.get("EDGE_RKNN_MODEL_PATH")
        try:
            os.environ["EDGE_DETECTOR_BACKEND"] = "rknn"
            os.environ["EDGE_RKNN_MODEL_PATH"] = ""
            detector = create_rknn_detector_from_env(min_confidence=0.35)
        finally:
            if old_backend is None:
                os.environ.pop("EDGE_DETECTOR_BACKEND", None)
            else:
                os.environ["EDGE_DETECTOR_BACKEND"] = old_backend
            if old_model_path is None:
                os.environ.pop("EDGE_RKNN_MODEL_PATH", None)
            else:
                os.environ["EDGE_RKNN_MODEL_PATH"] = old_model_path

        self.assertEqual(detector.config.model_path, Path("./models/rknn/yolov8n_rockchip_opt_i8_rk3566.rknn"))

    def test_empty_model_version_env_falls_back_to_model_stem(self) -> None:
        old_model_path = os.environ.get("EDGE_RKNN_MODEL_PATH")
        old_model_version = os.environ.get("EDGE_RKNN_MODEL_VERSION")
        try:
            os.environ["EDGE_RKNN_MODEL_PATH"] = "./models/rknn/yolov8n_rockchip_opt_i8_rk3566.rknn"
            os.environ["EDGE_RKNN_MODEL_VERSION"] = ""
            detector = create_rknn_detector_from_env(min_confidence=0.35)
        finally:
            if old_model_path is None:
                os.environ.pop("EDGE_RKNN_MODEL_PATH", None)
            else:
                os.environ["EDGE_RKNN_MODEL_PATH"] = old_model_path
            if old_model_version is None:
                os.environ.pop("EDGE_RKNN_MODEL_VERSION", None)
            else:
                os.environ["EDGE_RKNN_MODEL_VERSION"] = old_model_version

        self.assertEqual(detector.config.model_version, "yolov8n_rockchip_opt_i8_rk3566")

    def test_empty_labels_env_falls_back_to_coco80(self) -> None:
        old_labels = os.environ.get("EDGE_RKNN_LABELS")
        try:
            os.environ["EDGE_RKNN_LABELS"] = ""
            detector = create_rknn_detector_from_env(min_confidence=0.35)
        finally:
            if old_labels is None:
                os.environ.pop("EDGE_RKNN_LABELS", None)
            else:
                os.environ["EDGE_RKNN_LABELS"] = old_labels

        self.assertEqual(detector.config.labels, COCO80_LABELS)
        self.assertEqual(len(detector.config.labels), 80)

    def test_labels_path_env_overrides_csv_labels(self) -> None:
        old_labels_path = os.environ.get("EDGE_RKNN_LABELS_PATH")
        old_labels = os.environ.get("EDGE_RKNN_LABELS")
        with tempfile.TemporaryDirectory(prefix="vision_butler_rknn_labels_") as tmp:
            labels_file = Path(tmp) / "labels.txt"
            labels_file.write_text("alpha\nbeta\n", encoding="utf-8")
            try:
                os.environ["EDGE_RKNN_LABELS_PATH"] = str(labels_file)
                os.environ["EDGE_RKNN_LABELS"] = "x,y,z"
                detector = create_rknn_detector_from_env(min_confidence=0.35)
            finally:
                if old_labels_path is None:
                    os.environ.pop("EDGE_RKNN_LABELS_PATH", None)
                else:
                    os.environ["EDGE_RKNN_LABELS_PATH"] = old_labels_path
                if old_labels is None:
                    os.environ.pop("EDGE_RKNN_LABELS", None)
                else:
                    os.environ["EDGE_RKNN_LABELS"] = old_labels

        self.assertEqual(detector.config.labels, ("alpha", "beta"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
