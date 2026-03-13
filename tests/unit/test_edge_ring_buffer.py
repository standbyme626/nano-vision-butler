from __future__ import annotations

import unittest

from edge_device.cache.ring_buffer import ClipItem, MediaRingBuffer, SnapshotItem


class MediaRingBufferUnitTests(unittest.TestCase):
    def test_snapshot_buffer_keeps_latest_items(self) -> None:
        buffer = MediaRingBuffer(snapshot_capacity=2, clip_capacity=2)
        buffer.add_snapshot(
            SnapshotItem("snap-1", "2026-03-13T00:00:00Z", "/tmp/s1.jpg", "file:///tmp/s1.jpg", 100, 100)
        )
        buffer.add_snapshot(
            SnapshotItem("snap-2", "2026-03-13T00:00:01Z", "/tmp/s2.jpg", "file:///tmp/s2.jpg", 100, 100)
        )
        buffer.add_snapshot(
            SnapshotItem("snap-3", "2026-03-13T00:00:02Z", "/tmp/s3.jpg", "file:///tmp/s3.jpg", 100, 100)
        )

        items = buffer.snapshot_items()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].snapshot_id, "snap-2")
        self.assertEqual(buffer.latest_snapshot().snapshot_id, "snap-3")

    def test_get_recent_clip_prefers_duration_match(self) -> None:
        buffer = MediaRingBuffer(snapshot_capacity=2, clip_capacity=3)
        buffer.add_clip(
            ClipItem("clip-1", "2026-03-13T00:00:00Z", "2026-03-13T00:00:03Z", 3, "/tmp/c1.mp4", "file:///tmp/c1.mp4")
        )
        buffer.add_clip(
            ClipItem("clip-2", "2026-03-13T00:00:03Z", "2026-03-13T00:00:09Z", 6, "/tmp/c2.mp4", "file:///tmp/c2.mp4")
        )

        match = buffer.get_recent_clip(5)
        fallback = buffer.get_recent_clip(10)

        self.assertEqual(match.clip_id, "clip-2")
        self.assertEqual(fallback.clip_id, "clip-2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
