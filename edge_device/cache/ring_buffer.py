"""Ring buffer cache for snapshots and clips."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


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
        self._snapshots: deque[SnapshotItem] = deque(maxlen=max(1, snapshot_capacity))
        self._clips: deque[ClipItem] = deque(maxlen=max(1, clip_capacity))

    def add_snapshot(self, item: SnapshotItem) -> None:
        self._snapshots.append(item)

    def add_clip(self, item: ClipItem) -> None:
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
            return None
        required = max(int(duration_sec), 1)
        for clip in reversed(self._clips):
            if clip.duration_sec >= required:
                return clip
        return self._clips[-1]

    def snapshot_items(self) -> list[SnapshotItem]:
        return list(self._snapshots)

    def clip_items(self) -> list[ClipItem]:
        return list(self._clips)
