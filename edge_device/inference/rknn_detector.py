"""RKNN detector with graceful fallback to lightweight detector."""

from __future__ import annotations

import importlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from edge_device.capture.camera import CapturedFrame
from edge_device.inference.detector import Detection, LightweightDetector

LOGGER = logging.getLogger(__name__)

COCO80_LABELS: tuple[str, ...] = (
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
)
COCO80_LABELS_CSV = ",".join(COCO80_LABELS)


@dataclass(frozen=True)
class RKNNDetectorConfig:
    model_path: Path
    model_version: str
    min_confidence: float = 0.35
    input_width: int = 640
    input_height: int = 640
    nms_threshold: float = 0.45
    max_candidates: int = 64
    labels: tuple[str, ...] = COCO80_LABELS


class RKNNDetector:
    """RKNN-backed detector that degrades to lightweight detection on failure."""

    def __init__(
        self,
        *,
        config: RKNNDetectorConfig,
        runtime: Any | None = None,
        fallback_detector: LightweightDetector | None = None,
        ) -> None:
        self.config = config
        self.last_error: str | None = None
        self.last_profile: dict[str, float] | None = None
        self._fallback = fallback_detector or LightweightDetector(
            model_version="stub-detector-v1",
            min_confidence=config.min_confidence,
        )
        self._runtime = runtime if runtime is not None else self._init_runtime()
        self.model_version = config.model_version if self._runtime is not None else self._fallback.model_version
        self._grid_cache: dict[tuple[int, int], tuple[Any, Any]] = {}

    @property
    def runtime_ready(self) -> bool:
        return self._runtime is not None

    def detect(self, frame: CapturedFrame) -> list[Detection]:
        if self._runtime is None:
            if self.last_error is None:
                self.last_error = f"rknn_runtime_unavailable:model={self.config.model_path}"
                LOGGER.warning("RKNN runtime unavailable, fallback enabled: %s", self.last_error)
            return self._fallback.detect(frame)

        try:
            outputs, preprocess_meta, infer_profile = self._infer(frame)
            post_start = time.perf_counter()
            decoded = self._decode(outputs=outputs, frame=frame, preprocess_meta=preprocess_meta)
            post_ms = (time.perf_counter() - post_start) * 1000.0
            self.last_error = None
            self.model_version = self.config.model_version
            self.last_profile = {
                "preprocess_ms": float(infer_profile.get("preprocess_ms", 0.0)),
                "infer_ms": float(infer_profile.get("infer_ms", 0.0)),
                "postprocess_ms": float(post_ms),
                "detect_total_ms": float(
                    infer_profile.get("preprocess_ms", 0.0) + infer_profile.get("infer_ms", 0.0) + post_ms
                ),
            }
            return decoded
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            self.last_error = f"rknn_inference_failed:{exc}"
            self.model_version = self._fallback.model_version
            self.last_profile = None
            LOGGER.warning("RKNN inference failed, fallback enabled: %s", self.last_error)
            return self._fallback.detect(frame)

    def _init_runtime(self) -> Any | None:
        if not self.config.model_path.exists():
            self.last_error = f"rknn_model_missing:{self.config.model_path}"
            LOGGER.warning("RKNN model not found, fallback enabled: %s", self.last_error)
            return None

        try:
            module = importlib.import_module("rknnlite.api")
            rknn_cls = getattr(module, "RKNNLite")
            runtime = rknn_cls()
            load_ret = runtime.load_rknn(str(self.config.model_path))
            if load_ret != 0:
                self.last_error = f"rknn_load_failed:code={load_ret}"
                LOGGER.warning("RKNN model load failed, fallback enabled: %s", self.last_error)
                return None
            init_ret = runtime.init_runtime()
            if init_ret != 0:
                self.last_error = f"rknn_init_failed:code={init_ret}"
                LOGGER.warning("RKNN runtime init failed, fallback enabled: %s", self.last_error)
                return None
            return runtime
        except Exception as exc:  # pragma: no cover - optional dependency boundary
            self.last_error = f"rknn_runtime_init_error:{exc}"
            LOGGER.warning("RKNN runtime init error, fallback enabled: %s", self.last_error)
            return None

    def _infer(self, frame: CapturedFrame) -> tuple[Any, dict[str, float], dict[str, float]]:
        preprocess_start = time.perf_counter()
        input_tensor, preprocess_meta = self._preprocess_frame(frame)
        preprocess_ms = (time.perf_counter() - preprocess_start) * 1000.0
        infer_start = time.perf_counter()
        outputs = self._runtime.inference(inputs=[input_tensor])
        infer_ms = (time.perf_counter() - infer_start) * 1000.0
        return outputs, preprocess_meta, {"preprocess_ms": preprocess_ms, "infer_ms": infer_ms}

    def _preprocess_frame(self, frame: CapturedFrame) -> tuple[Any, dict[str, float]]:
        import numpy as np
        from PIL import Image

        source_bgr = self._load_frame_bgr(frame)
        src_h, src_w = source_bgr.shape[:2]
        dst_w, dst_h = self.config.input_width, self.config.input_height

        if src_w <= 0 or src_h <= 0:
            source_bgr = np.zeros((dst_h, dst_w, 3), dtype=np.uint8)
            src_h, src_w = dst_h, dst_w

        scale = min(dst_w / float(src_w), dst_h / float(src_h))
        new_w = max(int(round(src_w * scale)), 1)
        new_h = max(int(round(src_h * scale)), 1)
        try:
            import cv2

            resized = cv2.resize(source_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            letterboxed = np.zeros((dst_h, dst_w, 3), dtype=np.uint8)
            pad_x = (dst_w - new_w) // 2
            pad_y = (dst_h - new_h) // 2
            letterboxed[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized
            rgb = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
        except Exception:
            rgb_source = Image.fromarray(source_bgr[:, :, ::-1], mode="RGB")
            resized_rgb = rgb_source.resize((new_w, new_h), resample=Image.BILINEAR)
            letterboxed_rgb = np.zeros((dst_h, dst_w, 3), dtype=np.uint8)
            pad_x = (dst_w - new_w) // 2
            pad_y = (dst_h - new_h) // 2
            letterboxed_rgb[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = np.asarray(resized_rgb, dtype=np.uint8)
            rgb = letterboxed_rgb
        input_tensor = np.expand_dims(rgb, axis=0)
        preprocess_meta = {
            "scale": float(scale),
            "pad_x": float(pad_x),
            "pad_y": float(pad_y),
            "src_w": float(src_w),
            "src_h": float(src_h),
        }
        return input_tensor, preprocess_meta

    @staticmethod
    def _load_frame_bgr(frame: CapturedFrame) -> Any:
        import numpy as np
        from PIL import Image

        if frame.image_path:
            path = Path(frame.image_path)
            if path.exists():
                try:
                    import cv2

                    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                    if image is not None:
                        return image
                except Exception:
                    pass
                try:
                    with Image.open(path) as image:
                        rgb = image.convert("RGB")
                        return np.asarray(rgb, dtype=np.uint8)[:, :, ::-1].copy()
                except Exception:
                    pass
        return np.zeros((max(frame.height, 1), max(frame.width, 1), 3), dtype=np.uint8)

    def _decode(self, *, outputs: Any, frame: CapturedFrame, preprocess_meta: dict[str, float]) -> list[Detection]:
        if not isinstance(outputs, (list, tuple)) or not outputs:
            raise ValueError("RKNN outputs are empty")
        if self._looks_like_yolov8_flat_output(outputs):
            return self._decode_yolov8_flat_output(outputs=outputs, frame=frame, preprocess_meta=preprocess_meta)
        if self._looks_like_rkopt_yolov8(outputs):
            return self._decode_rkopt_yolov8(outputs=outputs, frame=frame, preprocess_meta=preprocess_meta)
        return self._decode_legacy_nx6(outputs=outputs, frame=frame)

    @staticmethod
    def _looks_like_yolov8_flat_output(outputs: Any) -> bool:
        if len(outputs) != 1:
            return False
        first = outputs[0]
        try:
            shape = tuple(first.shape)
        except AttributeError:
            return False
        if len(shape) != 3 or shape[0] != 1:
            return False
        return shape[1] >= 6 or shape[2] >= 6

    @staticmethod
    def _looks_like_rkopt_yolov8(outputs: Any) -> bool:
        if len(outputs) < 6:
            return False
        first = outputs[0]
        second = outputs[1] if len(outputs) > 1 else None
        third = outputs[2] if len(outputs) > 2 else None
        try:
            first_shape = tuple(first.shape)
            second_shape = tuple(second.shape) if second is not None else ()
            third_shape = tuple(third.shape) if third is not None else ()
        except AttributeError:
            return False
        if len(first_shape) != 4 or len(second_shape) != 4:
            return False
        return first_shape[1] % 4 == 0 and third_shape[:2] == (1, 1)

    def _decode_legacy_nx6(self, *, outputs: Any, frame: CapturedFrame) -> list[Detection]:
        import numpy as np

        try:
            arr = np.asarray(outputs[0])
        except Exception as exc:
            raise ValueError(f"RKNN output cast failed: {exc}") from exc

        if arr.size == 0:
            return []
        if arr.ndim == 1:
            if arr.size % 6 != 0:
                raise ValueError("RKNN output must be N*6")
            arr = arr.reshape((-1, 6))
        elif arr.ndim >= 2:
            arr = arr.reshape((-1, arr.shape[-1]))

        if arr.shape[1] < 6:
            raise ValueError("RKNN output row width < 6")

        detections: list[Detection] = []
        max_rows = min(arr.shape[0], 64)
        for idx in range(max_rows):
            row = arr[idx]
            score = float(row[4])
            if score < self.config.min_confidence:
                continue
            class_id = int(row[5])
            label = self._label_for_class_id(class_id)
            x1, y1, x2, y2 = self._normalize_bbox(
                x1=float(row[0]),
                y1=float(row[1]),
                x2=float(row[2]),
                y2=float(row[3]),
                frame=frame,
            )
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append(
                Detection(
                    object_name=label,
                    object_class=label,
                    confidence=max(min(score, 1.0), 0.0),
                    bbox=(x1, y1, x2, y2),
                    zone_id="entry_door",
                )
            )
        return detections

    def _decode_yolov8_flat_output(
        self,
        *,
        outputs: Any,
        frame: CapturedFrame,
        preprocess_meta: dict[str, float],
    ) -> list[Detection]:
        import numpy as np

        raw = np.asarray(outputs[0], dtype=np.float32)
        if raw.ndim != 3 or raw.shape[0] != 1:
            raise ValueError(f"YOLOv8 flat output shape invalid: {raw.shape}")

        pred = raw[0]
        if pred.shape[0] >= 6:
            channels_first = pred
        else:
            channels_first = pred.transpose(1, 0)

        if channels_first.shape[0] < 6:
            raise ValueError(f"YOLOv8 flat output channel count invalid: {channels_first.shape}")

        boxes_xywh = channels_first[0:4, :].transpose(1, 0)
        class_part = channels_first[4:, :].transpose(1, 0)
        if class_part.size == 0:
            return []

        class_min = float(class_part.min())
        class_max = float(class_part.max())
        if class_min < 0.0 or class_max > 1.0:
            class_part = 1.0 / (1.0 + np.exp(-class_part))

        class_scores = class_part.max(axis=1)
        class_ids = class_part.argmax(axis=1)
        if class_scores.size == 0:
            return []

        # Some unsupported RKNN exports produce zeroed class heads; avoid false positives.
        if float(class_scores.max()) <= 0.0:
            LOGGER.warning("RKNN class head is all-zero for model=%s; skip detections", self.config.model_version)
            return []

        keep = class_scores >= self.config.min_confidence
        if not keep.any():
            return []
        boxes_xywh = boxes_xywh[keep]
        class_ids = class_ids[keep]
        class_scores = class_scores[keep]

        cx = boxes_xywh[:, 0]
        cy = boxes_xywh[:, 1]
        w = boxes_xywh[:, 2]
        h = boxes_xywh[:, 3]
        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        x2 = cx + w / 2.0
        y2 = cy + h / 2.0
        boxes_xyxy = np.stack((x1, y1, x2, y2), axis=1)

        keep_indices: list[int] = []
        for class_id in sorted(set(int(item) for item in class_ids.tolist())):
            mask = class_ids == class_id
            indices = np.where(mask)[0]
            class_boxes = boxes_xyxy[mask]
            class_keep = self._nms_indices(class_boxes, class_scores[mask], self.config.nms_threshold)
            keep_indices.extend(indices[idx] for idx in class_keep)
        if not keep_indices:
            return []

        keep_arr = np.array(keep_indices, dtype=np.int64)
        boxes_xyxy = boxes_xyxy[keep_arr]
        class_ids = class_ids[keep_arr]
        class_scores = class_scores[keep_arr]

        order = np.argsort(class_scores)[::-1][: self.config.max_candidates]
        detections: list[Detection] = []
        for idx in order:
            label = self._label_for_class_id(int(class_ids[idx]))
            left, top, right, bottom = self._map_box_to_frame(
                box=boxes_xyxy[idx],
                frame=frame,
                preprocess_meta=preprocess_meta,
            )
            if right <= left or bottom <= top:
                continue
            detections.append(
                Detection(
                    object_name=label,
                    object_class=label,
                    confidence=max(min(float(class_scores[idx]), 1.0), 0.0),
                    bbox=(left, top, right, bottom),
                    zone_id="entry_door",
                )
            )
        return detections

    def _decode_rkopt_yolov8(
        self,
        *,
        outputs: Any,
        frame: CapturedFrame,
        preprocess_meta: dict[str, float],
    ) -> list[Detection]:
        import numpy as np

        branch_count = 3
        pair_per_branch = max(len(outputs) // branch_count, 2)
        all_boxes: list[Any] = []
        all_classes: list[Any] = []
        all_scores: list[Any] = []

        for branch_idx in range(branch_count):
            base = branch_idx * pair_per_branch
            if base + 1 >= len(outputs):
                break
            pos = np.asarray(outputs[base], dtype=np.float32)
            cls_conf = np.asarray(outputs[base + 1], dtype=np.float32)
            score_sum = np.asarray(outputs[base + 2], dtype=np.float32) if (base + 2) < len(outputs) else None

            boxes = self._box_process(pos)
            boxes_flat = self._sp_flatten(boxes)
            cls_flat = self._sp_flatten(cls_conf)
            if boxes_flat.size == 0 or cls_flat.size == 0:
                continue

            if score_sum is not None and score_sum.size > 0:
                sum_flat = self._sp_flatten(score_sum).reshape(-1)
                pre_mask = sum_flat >= self.config.min_confidence
                if pre_mask.any():
                    boxes_flat = boxes_flat[pre_mask]
                    cls_flat = cls_flat[pre_mask]
                else:
                    continue

            class_scores = cls_flat.max(axis=-1)
            class_ids = cls_flat.argmax(axis=-1)
            keep = class_scores >= self.config.min_confidence
            if not keep.any():
                continue
            all_boxes.append(boxes_flat[keep])
            all_classes.append(class_ids[keep])
            all_scores.append(class_scores[keep])

        if not all_boxes:
            return []

        boxes = np.concatenate(all_boxes, axis=0)
        classes = np.concatenate(all_classes, axis=0)
        scores = np.concatenate(all_scores, axis=0)

        if boxes.shape[0] > self.config.max_candidates * 4:
            top_idx = np.argsort(scores)[-self.config.max_candidates * 4 :]
            boxes = boxes[top_idx]
            classes = classes[top_idx]
            scores = scores[top_idx]

        keep_indices: list[int] = []
        for class_id in sorted(set(int(item) for item in classes.tolist())):
            class_mask = classes == class_id
            class_indices = np.where(class_mask)[0]
            class_boxes = boxes[class_mask]
            class_scores = scores[class_mask]
            class_keep = self._nms_indices(class_boxes, class_scores, self.config.nms_threshold)
            keep_indices.extend(class_indices[idx] for idx in class_keep)

        if not keep_indices:
            return []

        keep_arr = np.array(keep_indices, dtype=np.int64)
        boxes = boxes[keep_arr]
        classes = classes[keep_arr]
        scores = scores[keep_arr]

        order = np.argsort(scores)[::-1]
        order = order[: self.config.max_candidates]
        boxes = boxes[order]
        classes = classes[order]
        scores = scores[order]

        detections: list[Detection] = []
        for idx in range(len(order)):
            class_id = int(classes[idx])
            label = self._label_for_class_id(class_id)
            x1, y1, x2, y2 = self._map_box_to_frame(
                box=boxes[idx],
                frame=frame,
                preprocess_meta=preprocess_meta,
            )
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append(
                Detection(
                    object_name=label,
                    object_class=label,
                    confidence=max(min(float(scores[idx]), 1.0), 0.0),
                    bbox=(x1, y1, x2, y2),
                    zone_id="entry_door",
                )
            )
        return detections

    def _box_process(self, position: Any) -> Any:
        import numpy as np

        if position.ndim != 4:
            raise ValueError(f"RKOPT position output ndim invalid: {position.ndim}")
        _, _, grid_h, grid_w = position.shape
        grid, stride = self._grid_and_stride(grid_h=grid_h, grid_w=grid_w)
        position = self._dfl(position)
        box_xy = grid + 0.5 - position[:, 0:2, :, :]
        box_xy2 = grid + 0.5 + position[:, 2:4, :, :]
        return np.concatenate((box_xy * stride, box_xy2 * stride), axis=1)

    def _grid_and_stride(self, *, grid_h: int, grid_w: int) -> tuple[Any, Any]:
        import numpy as np

        key = (grid_h, grid_w)
        cached = self._grid_cache.get(key)
        if cached is not None:
            return cached
        col, row = np.meshgrid(np.arange(0, grid_w), np.arange(0, grid_h))
        grid = np.concatenate(
            (
                col.reshape(1, 1, grid_h, grid_w),
                row.reshape(1, 1, grid_h, grid_w),
            ),
            axis=1,
        ).astype(np.float32)
        stride = np.array(
            [
                self.config.input_width / float(grid_w),
                self.config.input_height / float(grid_h),
            ],
            dtype=np.float32,
        ).reshape(1, 2, 1, 1)
        self._grid_cache[key] = (grid, stride)
        return grid, stride

    @staticmethod
    def _dfl(position: Any) -> Any:
        import numpy as np

        n, c, h, w = position.shape
        part = 4
        reg_max = c // part
        reshaped = position.reshape(n, part, reg_max, h, w)
        reshaped = reshaped - reshaped.max(axis=2, keepdims=True)
        exp = np.exp(reshaped)
        probs = exp / np.maximum(exp.sum(axis=2, keepdims=True), 1e-9)
        bins = np.arange(reg_max, dtype=np.float32).reshape(1, 1, reg_max, 1, 1)
        return (probs * bins).sum(axis=2)

    @staticmethod
    def _sp_flatten(value: Any) -> Any:
        import numpy as np

        array = np.asarray(value, dtype=np.float32)
        channels = array.shape[1]
        return array.transpose(0, 2, 3, 1).reshape(-1, channels)

    @staticmethod
    def _nms_indices(boxes: Any, scores: Any, iou_threshold: float) -> list[int]:
        import numpy as np

        if boxes.size == 0:
            return []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        order = np.argsort(scores)[::-1]
        keep: list[int] = []
        while order.size > 0:
            i = int(order[0])
            keep.append(i)
            if order.size == 1:
                break
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter_w = np.maximum(0.0, xx2 - xx1)
            inter_h = np.maximum(0.0, yy2 - yy1)
            inter = inter_w * inter_h
            union = areas[i] + areas[order[1:]] - inter
            iou = inter / np.maximum(union, 1e-9)
            remaining = np.where(iou <= iou_threshold)[0]
            order = order[remaining + 1]
        return keep

    @staticmethod
    def _map_box_to_frame(*, box: Any, frame: CapturedFrame, preprocess_meta: dict[str, float]) -> tuple[int, int, int, int]:
        scale = max(float(preprocess_meta.get("scale", 1.0)), 1e-9)
        pad_x = float(preprocess_meta.get("pad_x", 0.0))
        pad_y = float(preprocess_meta.get("pad_y", 0.0))
        x1 = (float(box[0]) - pad_x) / scale
        y1 = (float(box[1]) - pad_y) / scale
        x2 = (float(box[2]) - pad_x) / scale
        y2 = (float(box[3]) - pad_y) / scale
        width = max(int(frame.width), 1)
        height = max(int(frame.height), 1)
        left = max(min(int(round(x1)), width - 1), 0)
        top = max(min(int(round(y1)), height - 1), 0)
        right = max(min(int(round(x2)), width), 0)
        bottom = max(min(int(round(y2)), height), 0)
        return left, top, right, bottom

    def _label_for_class_id(self, class_id: int) -> str:
        if class_id < 0:
            return "unknown"
        if class_id < len(self.config.labels):
            return self.config.labels[class_id]
        return f"class_{class_id}"

    @staticmethod
    def _normalize_bbox(
        *,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        frame: CapturedFrame,
    ) -> tuple[int, int, int, int]:
        width = max(int(frame.width), 1)
        height = max(int(frame.height), 1)
        left = max(min(int(round(x1)), width - 1), 0)
        top = max(min(int(round(y1)), height - 1), 0)
        right = max(min(int(round(x2)), width), 0)
        bottom = max(min(int(round(y2)), height), 0)
        return left, top, right, bottom


def create_rknn_detector_from_env(*, min_confidence: float) -> RKNNDetector:
    raw_model_path = (os.getenv("EDGE_RKNN_MODEL_PATH") or "").strip()
    model_path = Path(raw_model_path) if raw_model_path else Path("./models/rknn/yolov8n_rockchip_opt_i8_rk3566.rknn")
    raw_model_version = (os.getenv("EDGE_RKNN_MODEL_VERSION") or "").strip()
    model_version = raw_model_version or (model_path.stem or "rknn-main")
    input_width, input_height = _parse_input_size(os.getenv("EDGE_RKNN_INPUT_SIZE", "640x640"))
    nms_threshold = _parse_float(os.getenv("EDGE_RKNN_NMS_THRESHOLD"), fallback=0.45)
    max_candidates = _parse_int(os.getenv("EDGE_RKNN_MAX_CANDIDATES"), fallback=64, minimum=1, maximum=512)
    labels_path = _resolve_labels_path(model_path=model_path)
    if labels_path is not None:
        labels = _parse_labels_file(labels_path)
    else:
        labels = _parse_labels(os.getenv("EDGE_RKNN_LABELS", COCO80_LABELS_CSV))
    return RKNNDetector(
        config=RKNNDetectorConfig(
            model_path=model_path,
            model_version=model_version,
            min_confidence=min_confidence,
            input_width=input_width,
            input_height=input_height,
            nms_threshold=nms_threshold,
            max_candidates=max_candidates,
            labels=labels,
        )
    )


def _parse_labels(raw: str) -> tuple[str, ...]:
    labels = tuple(item.strip() for item in raw.split(",") if item.strip())
    return labels or COCO80_LABELS


def _parse_labels_file(path: Path) -> tuple[str, ...]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return COCO80_LABELS
    labels = tuple(line.strip() for line in content.splitlines() if line.strip())
    if labels:
        return labels
    return COCO80_LABELS


def _resolve_labels_path(*, model_path: Path) -> Path | None:
    raw = (os.getenv("EDGE_RKNN_LABELS_PATH") or "").strip()
    if raw:
        path = Path(raw)
        if path.exists():
            return path
        return None
    if "oiv7" in model_path.name.lower():
        auto = Path("./config/labels/openimages_v7_601.txt")
        if auto.exists():
            return auto
    return None


def _parse_input_size(raw: str) -> tuple[int, int]:
    text = (raw or "").strip().lower()
    if "x" not in text:
        return 640, 640
    left, right = text.split("x", 1)
    try:
        width = max(int(left), 1)
        height = max(int(right), 1)
        return width, height
    except ValueError:
        return 640, 640


def _parse_float(raw: str | None, *, fallback: float) -> float:
    if raw is None:
        return fallback
    try:
        value = float(raw)
    except ValueError:
        return fallback
    return value if value > 0 else fallback


def _parse_int(raw: str | None, *, fallback: int, minimum: int, maximum: int) -> int:
    if raw is None:
        return fallback
    try:
        value = int(raw)
    except ValueError:
        return fallback
    value = max(value, minimum)
    return min(value, maximum)
