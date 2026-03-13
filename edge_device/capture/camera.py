"""Capture layer for RK3566 edge runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count


def utc_now_iso8601() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class CapturedFrame:
    frame_id: str
    captured_at: str
    width: int
    height: int
    source: str
    pixel_format: str = "rgb24"


class StubCamera:
    """Minimal camera adapter while waiting for V4L2/GStreamer integration."""

    def __init__(self, *, source: str = "rk3566-camera-0", width: int = 1280, height: int = 720) -> None:
        self._source = source
        self._width = width
        self._height = height
        self._counter = count(1)

    def capture_latest_frame(self) -> CapturedFrame:
        seq = next(self._counter)
        return CapturedFrame(
            frame_id=f"frame-{seq:06d}",
            captured_at=utc_now_iso8601(),
            width=self._width,
            height=self._height,
            source=self._source,
        )
