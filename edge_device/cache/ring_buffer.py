"""Ring buffer cache for snapshots and clips."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SnapshotItem:
    snapshot_id: str
    captured_at: str
    path: str
    uri: str
    width: int
    height: int


@dataclass(frozen=True)
class ClipItem:
    clip_id: str
    start_at: str
    end_at: str
    duration_sec: int
    path: str
    uri: str
    source_snapshot_id: str | None = None


class MediaRingBuffer:
    """Bounded in-memory cache to keep recent snapshot/clip references."""

    def __init__(self, *, snapshot_capacity: int = 32, clip_capacity: int = 16) -> None:
        self._snapshot_capacity = max(1, snapshot_capacity)
        self._clip_capacity = max(1, clip_capacity)
        self._snapshots: deque[SnapshotItem] = deque()
        self._clips: deque[ClipItem] = deque()
        self._snapshot_evictions = 0
        self._clip_evictions = 0
        self._last_clip_lookup: dict[str, Any] | None = None

    def add_snapshot(self, item: SnapshotItem) -> None:
        if len(self._snapshots) >= self._snapshot_capacity:
            self._snapshots.popleft()
            self._snapshot_evictions += 1
        self._snapshots.append(item)

    def add_clip(self, item: ClipItem) -> None:
        if len(self._clips) >= self._clip_capacity:
            self._clips.popleft()
            self._clip_evictions += 1
        self._clips.append(item)

    def latest_snapshot(self) -> SnapshotItem | None:
        if not self._snapshots:
            return None
        return self._snapshots[-1]

    def latest_clip(self) -> ClipItem | None:
        if not self._clips:
            return None
        return self._clips[-1]

    def get_recent_clip(self, duration_sec: int) -> ClipItem | None:
        if not self._clips:
            self._last_clip_lookup = {
                "requested_duration_sec": max(int(duration_sec), 1),
                "selected_clip_id": None,
                "decision": "empty_cache",
            }
            return None
        required = max(int(duration_sec), 1)
        matches = [clip for clip in self._clips if clip.duration_sec >= required]
        if matches:
            selected = min(
                matches,
                key=lambda clip: (
                    clip.duration_sec,
                    clip.end_at,
                    clip.clip_id,
                ),
            )
            self._last_clip_lookup = {
                "requested_duration_sec": required,
                "selected_clip_id": selected.clip_id,
                "decision": "duration_match",
            }
            return selected

        selected = self._clips[-1]
        self._last_clip_lookup = {
            "requested_duration_sec": required,
            "selected_clip_id": selected.clip_id,
            "decision": "duration_fallback_latest",
        }
        return selected

    def snapshot_items(self) -> list[SnapshotItem]:
        return list(self._snapshots)

    def clip_items(self) -> list[ClipItem]:
        return list(self._clips)

    def recent_snapshots(self, *, limit: int | None = None) -> list[SnapshotItem]:
        items = list(self._snapshots)
        if limit is None:
            return items
        capped = max(int(limit), 1)
        return items[-capped:]

    def cache_metrics(self) -> dict[str, Any]:
        return {
            "snapshot_capacity": self._snapshot_capacity,
            "clip_capacity": self._clip_capacity,
            "snapshot_count": len(self._snapshots),
            "clip_count": len(self._clips),
            "snapshot_evictions": self._snapshot_evictions,
            "clip_evictions": self._clip_evictions,
            "last_clip_lookup": dict(self._last_clip_lookup) if self._last_clip_lookup else None,
        }
