"""Lightweight detection stub with RKNN-ready interface boundary."""

from __future__ import annotations

from dataclasses import dataclass

from edge_device.capture.camera import CapturedFrame


@dataclass(frozen=True)
class Detection:
    object_name: str
    object_class: str
    confidence: float
    bbox: tuple[int, int, int, int]
    zone_id: str | None = None
    track_id: str | None = None


class LightweightDetector:
    """Stub detector that can be replaced by RKNN model inference."""

    def __init__(self, *, model_version: str = "stub-detector-v1", min_confidence: float = 0.35) -> None:
        self.model_version = model_version
        self.min_confidence = min_confidence

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
