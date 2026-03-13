"""Track assignment module for edge runtime."""

from __future__ import annotations

from dataclasses import replace
from itertools import count

from edge_device.inference.detector import Detection


class LightweightTracker:
    """Assign stable track IDs per (class, zone) key for lightweight tracking."""

    def __init__(self) -> None:
        self._counter = count(1)
        self._active_tracks: dict[tuple[str, str], str] = {}

    def assign_tracks(self, detections: list[Detection]) -> list[Detection]:
        tracked: list[Detection] = []
        for det in detections:
            if det.track_id:
                tracked.append(det)
                continue
            key = (det.object_class, det.zone_id or "global")
            track_id = self._active_tracks.get(key)
            if track_id is None:
                track_id = f"trk-{next(self._counter):05d}"
                self._active_tracks[key] = track_id
            tracked.append(replace(det, track_id=track_id))
        return tracked
