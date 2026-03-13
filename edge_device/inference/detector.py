"""Lightweight detection stub with RKNN-ready interface boundary."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from edge_device.capture.camera import CapturedFrame


@dataclass(frozen=True)
class Detection:
    object_name: str
    object_class: str
    confidence: float
    bbox: tuple[int, int, int, int]
    zone_id: str | None = None
    track_id: str | None = None


class DetectorProtocol(Protocol):
    model_version: str
    last_error: str | None

    def detect(self, frame: CapturedFrame) -> list[Detection]:
        ...


class LightweightDetector:
    """Stub detector that can be replaced by RKNN model inference."""

    def __init__(self, *, model_version: str = "stub-detector-v1", min_confidence: float = 0.35) -> None:
        self.model_version = model_version
        self.min_confidence = min_confidence
        self.last_error: str | None = None

    def detect(self, frame: CapturedFrame) -> list[Detection]:
        frame_seq = int(frame.frame_id.split("-")[-1])
        confidence = 0.82 if frame_seq % 2 else 0.66
        if confidence < self.min_confidence:
            return []
        label = "person" if frame_seq % 3 else "package"
        return [
            Detection(
                object_name=label,
                object_class=label,
                confidence=confidence,
                bbox=(120, 90, 680, 710),
                zone_id="entry_door",
            )
        ]


def create_detector_from_env() -> DetectorProtocol:
    min_confidence = _parse_float(
        os.getenv("EDGE_DETECT_MIN_CONFIDENCE"),
        fallback=0.35,
    )
    backend = (os.getenv("EDGE_DETECTOR_BACKEND", "auto") or "auto").strip().lower()
    if backend in {"lightweight", "stub"}:
        return LightweightDetector(
            model_version=os.getenv("EDGE_DETECT_MODEL_VERSION", "stub-detector-v1"),
            min_confidence=min_confidence,
        )

    if backend in {"rknn", "auto"}:
        from edge_device.inference.rknn_detector import create_rknn_detector_from_env

        return create_rknn_detector_from_env(min_confidence=min_confidence)

    return LightweightDetector(
        model_version=os.getenv("EDGE_DETECT_MODEL_VERSION", "stub-detector-v1"),
        min_confidence=min_confidence,
    )


def _parse_float(raw: str | None, *, fallback: float) -> float:
    if raw is None:
        return fallback
    try:
        value = float(raw)
    except ValueError:
        return fallback
    return value if value > 0 else fallback
