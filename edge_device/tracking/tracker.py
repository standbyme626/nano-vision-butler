"""Track assignment module for edge runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from itertools import count

from edge_device.inference.detector import Detection


@dataclass(frozen=True)
class _TrackState:
    object_class: str
    zone_id: str
    bbox: tuple[int, int, int, int]
    last_seen_frame: int


@dataclass(frozen=True)
class _ZoneBand:
    zone_id: str
    start_ratio: float
    end_ratio: float


class LightweightTracker:
    """Assign stable track IDs with IoU matching and optional zone remapping."""

    def __init__(
        self,
        *,
        iou_threshold: float | None = None,
        max_missed_frames: int | None = None,
        zone_layout: str | None = None,
    ) -> None:
        self.iou_threshold = _clamp_float(
            _resolve_float(value=iou_threshold, env_key="EDGE_TRACK_IOU_THRESHOLD", fallback=0.4),
            lower=0.05,
            upper=0.95,
        )
        self.max_missed_frames = _resolve_int(
            value=max_missed_frames,
            env_key="EDGE_TRACK_MAX_MISSED_FRAMES",
            fallback=8,
            minimum=1,
        )
        self._zone_bands = _parse_zone_layout(
            zone_layout if zone_layout is not None else os.getenv("EDGE_TRACK_ZONE_LAYOUT"),
            fallback="entry_door:0.0-0.6,hallway:0.6-1.0",
        )
        self._counter = count(1)
        self._frame_index = 0
        self._tracks: dict[str, _TrackState] = {}

    def assign_tracks(
        self,
        detections: list[Detection],
        *,
        frame_width: int | None = None,
        frame_height: int | None = None,
    ) -> list[Detection]:
        del frame_height
        self._frame_index += 1
        self._expire_stale_tracks(current_frame=self._frame_index)

        used_track_ids: set[str] = set()
        tracked: list[Detection] = []
        for det in detections:
            zone_id = self._resolve_zone_id(det=det, frame_width=frame_width)
            if det.track_id:
                track_id = det.track_id
            else:
                track_id = self._match_existing_track(det=det, zone_id=zone_id, used_track_ids=used_track_ids)
                if track_id is None:
                    track_id = f"trk-{next(self._counter):05d}"

            used_track_ids.add(track_id)
            self._tracks[track_id] = _TrackState(
                object_class=det.object_class,
                zone_id=zone_id,
                bbox=det.bbox,
                last_seen_frame=self._frame_index,
            )
            tracked.append(replace(det, zone_id=zone_id, track_id=track_id))
        return tracked

    def _match_existing_track(
        self,
        *,
        det: Detection,
        zone_id: str,
        used_track_ids: set[str],
    ) -> str | None:
        matched_track_id: str | None = None
        matched_iou = 0.0
        for track_id, state in self._tracks.items():
            if track_id in used_track_ids:
                continue
            if state.object_class != det.object_class:
                continue
            if state.zone_id != zone_id:
                continue
            overlap = _bbox_iou(state.bbox, det.bbox)
            if overlap < self.iou_threshold:
                continue
            if overlap > matched_iou:
                matched_iou = overlap
                matched_track_id = track_id
        return matched_track_id

    def _expire_stale_tracks(self, *, current_frame: int) -> None:
        expired = [
            track_id
            for track_id, state in self._tracks.items()
            if current_frame - state.last_seen_frame > self.max_missed_frames
        ]
        for track_id in expired:
            self._tracks.pop(track_id, None)

    def _resolve_zone_id(self, *, det: Detection, frame_width: int | None) -> str:
        mapped_zone = self._map_zone_by_bbox(det=det, frame_width=frame_width)
        if mapped_zone is not None:
            return mapped_zone
        if det.zone_id and det.zone_id.strip():
            return det.zone_id.strip()
        return "global"

    def _map_zone_by_bbox(self, *, det: Detection, frame_width: int | None) -> str | None:
        if frame_width is None or frame_width <= 0:
            return None
        if not self._zone_bands:
            return None
        x1, _, x2, _ = det.bbox
        center_ratio = ((x1 + x2) / 2.0) / float(frame_width)
        center_ratio = _clamp_float(center_ratio, lower=0.0, upper=1.0)
        last_idx = len(self._zone_bands) - 1
        for idx, band in enumerate(self._zone_bands):
            right_inclusive = idx == last_idx
            if center_ratio < band.start_ratio:
                continue
            if center_ratio < band.end_ratio or (right_inclusive and center_ratio <= band.end_ratio):
                return band.zone_id
        return None


def _bbox_iou(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    inter_left = max(lx1, rx1)
    inter_top = max(ly1, ry1)
    inter_right = min(lx2, rx2)
    inter_bottom = min(ly2, ry2)
    inter_w = max(inter_right - inter_left, 0)
    inter_h = max(inter_bottom - inter_top, 0)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0
    left_area = max(lx2 - lx1, 0) * max(ly2 - ly1, 0)
    right_area = max(rx2 - rx1, 0) * max(ry2 - ry1, 0)
    union_area = left_area + right_area - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def _resolve_float(*, value: float | None, env_key: str, fallback: float) -> float:
    if value is not None:
        return float(value)
    raw = os.getenv(env_key)
    if raw is None:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def _resolve_int(*, value: int | None, env_key: str, fallback: int, minimum: int) -> int:
    parsed = fallback
    if value is not None:
        parsed = int(value)
    else:
        raw = os.getenv(env_key)
        if raw is not None:
            try:
                parsed = int(raw)
            except ValueError:
                parsed = fallback
    return max(parsed, minimum)


def _clamp_float(value: float, *, lower: float, upper: float) -> float:
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def _parse_zone_layout(value: str | None, *, fallback: str) -> tuple[_ZoneBand, ...]:
    text = (value or fallback).strip()
    bands: list[_ZoneBand] = []
    for item in text.split(","):
        segment = item.strip()
        if not segment or ":" not in segment:
            continue
        zone_id, raw_range = segment.split(":", 1)
        zone = zone_id.strip()
        normalized_range = raw_range.strip()
        if not zone or "-" not in normalized_range:
            continue
        raw_start, raw_end = normalized_range.split("-", 1)
        try:
            start = float(raw_start.strip())
            end = float(raw_end.strip())
        except ValueError:
            continue
        start = _clamp_float(start, lower=0.0, upper=1.0)
        end = _clamp_float(end, lower=0.0, upper=1.0)
        if end <= start:
            continue
        bands.append(_ZoneBand(zone_id=zone, start_ratio=start, end_ratio=end))

    if not bands and text != fallback:
        return _parse_zone_layout(None, fallback=fallback)
    return tuple(sorted(bands, key=lambda item: item.start_ratio))
