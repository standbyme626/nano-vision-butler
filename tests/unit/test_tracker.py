from __future__ import annotations

import unittest

from edge_device.inference.detector import Detection
from edge_device.tracking.tracker import LightweightTracker


class LightweightTrackerUnitTests(unittest.TestCase):
    def test_track_id_keeps_stable_when_crossing_zone_boundary(self) -> None:
        tracker = LightweightTracker(
            iou_threshold=0.2,
            max_missed_frames=4,
            zone_layout="left:0.0-0.5,right:0.5-1.0",
        )
        first = tracker.assign_tracks(
            [Detection("person", "person", 0.92, (420, 100, 560, 520))],
            frame_width=1000,
        )[0]
        second = tracker.assign_tracks(
            [Detection("person", "person", 0.93, (458, 100, 598, 520))],
            frame_width=1000,
        )[0]
        third = tracker.assign_tracks(
            [Detection("person", "person", 0.94, (530, 100, 670, 520))],
            frame_width=1000,
        )[0]

        self.assertEqual(first.track_id, second.track_id)
        self.assertEqual(second.track_id, third.track_id)
        self.assertEqual(first.zone_id, "left")
        self.assertEqual(second.zone_id, "left")
        self.assertEqual(third.zone_id, "right")

    def test_zone_hysteresis_avoids_boundary_flapping(self) -> None:
        tracker = LightweightTracker(
            iou_threshold=0.2,
            max_missed_frames=4,
            zone_layout="entry:0.0-0.5,hallway:0.5-1.0",
        )
        frames = [
            Detection("person", "person", 0.9, (420, 120, 560, 520)),
            Detection("person", "person", 0.9, (435, 120, 575, 520)),
            Detection("person", "person", 0.9, (425, 120, 565, 520)),
        ]
        zones = [
            tracker.assign_tracks([det], frame_width=1000)[0].zone_id
            for det in frames
        ]
        self.assertEqual(zones, ["entry", "entry", "entry"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
