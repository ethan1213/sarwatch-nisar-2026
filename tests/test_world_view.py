import unittest
import pandas as pd
from sarwatch.views.world import granules_at, _color


class WorldIndex(unittest.TestCase):
    def test_point_lookup_groups_repeat_geometries(self):
        frame = pd.DataFrame([
            {"id": "a", "time_start": "2026-07-05T09:42:27.000Z", "track": 132, "direction": "A", "frame": 169, "size_mib": 1800, "west": -58, "south": -18, "east": -56, "north": -16},
            {"id": "b", "time_start": "2026-07-17T09:42:27.000Z", "track": 132, "direction": "A", "frame": 169, "size_mib": 1800, "west": -58, "south": -18, "east": -56, "north": -16},
            {"id": "c", "time_start": "2026-07-10T22:00:00.000Z", "track": 10, "direction": "D", "frame": 97, "size_mib": 1800, "west": -58, "south": -18, "east": -56, "north": -16},
            {"id": "d", "time_start": "2026-07-10T22:00:00.000Z", "track": 10, "direction": "D", "frame": 97, "size_mib": 1800, "west": 10, "south": 40, "east": 12, "north": 42},
        ])
        frame["date"] = frame["time_start"].str[:10]
        hit = granules_at(frame, -57.25, -17.25)
        self.assertEqual(sorted(hit.id), ["a", "b", "c"])
        self.assertEqual(hit.geometry.nunique(), 2)
        self.assertEqual(list(hit.date)[0], "2026-07-05")
        self.assertTrue(granules_at(frame, 0, 0).empty)

    def test_color_scale_by_dates(self):
        self.assertEqual(_color(1), "#cfdbe2")
        self.assertEqual(_color(3), "#8fb3c7")
        self.assertEqual(_color(9), "#c6601c")


if __name__ == "__main__":
    unittest.main()
