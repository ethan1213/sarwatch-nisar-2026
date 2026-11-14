import unittest
import numpy as np
from sarwatch.ml.fire import neighbour_fraction, rank_auc, window_any, zonal_fraction, zonal_mean, zonal_mean_db, zone_raster
from sarwatch.ml.thermal import aoi_window, decode, fire_class, footprint_km, hourly_anomaly, latlon, scan_angles, window_geometry, zonal_stats

PROJ = {"semi_major_axis": 6378137.0, "semi_minor_axis": 6356752.31414, "perspective_point_height": 35786023.0, "longitude_of_projection_origin": -75.0}
AXIS_X, AXIS_Y = (5.6e-05, -0.151844, 5424), (-5.6e-05, 0.151844, 5424)  # ABI full disk, 2 km


class Navigation(unittest.TestCase):
    def test_scan_angles_match_pyproj_geostationary(self):
        from pyproj import Proj
        geos = Proj(proj="geos", h=PROJ["perspective_point_height"], lon_0=-75, sweep="x", a=PROJ["semi_major_axis"], b=PROJ["semi_minor_axis"])
        lat, lon = np.array([-17.25, -33.05, -33.45, 0.0]), np.array([-57.25, -71.6, -70.66, -75.0])
        x, y = scan_angles(lat, lon, PROJ)
        ex, ey = geos(lon, lat)
        np.testing.assert_allclose(x, np.asarray(ex) / PROJ["perspective_point_height"], atol=1e-9)
        np.testing.assert_allclose(y, np.asarray(ey) / PROJ["perspective_point_height"], atol=1e-9)

    def test_roundtrip_and_far_side_is_nan(self):
        lat, lon = np.array([-17.25, -33.05]), np.array([-57.25, -71.6])
        back_lat, back_lon = latlon(*scan_angles(lat, lon, PROJ), PROJ)
        np.testing.assert_allclose(back_lat, lat, atol=1e-7)
        np.testing.assert_allclose(back_lon, lon, atol=1e-7)
        x, y = scan_angles(-19.2, 23.0, PROJ)  # Okavango: not visible from 75 W
        self.assertTrue(np.isnan(x) and np.isnan(y))
        self.assertTrue(np.isnan(latlon(0.16, 0.16, PROJ)[0]))  # off the disk

    def test_window_covers_bbox_and_rejects_invisible_aoi(self):
        bbox = [-57.5, -17.5, -57.0, -17.0]
        window = aoi_window(bbox, AXIS_X, AXIS_Y, PROJ)
        lat, lon, corner_lat, corner_lon = window_geometry(window, AXIS_X, AXIS_Y, PROJ)
        self.assertEqual(lat.shape, (window[1] - window[0], window[3] - window[2]))
        self.assertEqual(corner_lat.shape, (lat.shape[0] + 1, lat.shape[1] + 1))
        self.assertLessEqual(corner_lon.min(), bbox[0]); self.assertGreaterEqual(corner_lon.max(), bbox[2])
        self.assertLessEqual(corner_lat.min(), bbox[1]); self.assertGreaterEqual(corner_lat.max(), bbox[3])
        self.assertGreater(lat[0, 0], lat[-1, 0])  # rows run north to south
        self.assertLess(lon[0, 0], lon[0, -1])
        width, height = footprint_km(corner_lat, corner_lon)
        self.assertTrue(2.0 < np.median(width) < 2.6 and 2.0 < np.median(height) < 2.6)  # larger than the 2 km nadir pixel
        with self.assertRaises(ValueError):
            aoi_window([22.6, -19.6, 23.4, -18.8], AXIS_X, AXIS_Y, PROJ)


class Products(unittest.TestCase):
    def test_fire_classes_collapse_filtered_codes(self):
        mask = np.array([[10, 30, 13, 33], [15, 35, 100, 150], [-99, 0, 40, 127]])
        np.testing.assert_array_equal(fire_class(mask), [[10, 10, 13, 13], [15, 15, 0, 0], [0, 0, 0, 0]])

    def test_decode_handles_fill_scale_and_unsigned(self):
        raw = np.array([0, 100, -1], dtype=np.int16)  # stored signed, flagged unsigned: -1 is 65535
        out = decode(raw, {"_Unsigned": "true", "_FillValue": np.array([-1], dtype=np.int16), "scale_factor": np.array([0.01], dtype=np.float32), "add_offset": np.array([200.0], dtype=np.float32)})
        np.testing.assert_allclose(out[:2], [200.0, 201.0], atol=1e-4)
        self.assertTrue(np.isnan(out[2]))
        big = decode(np.array([-32768], dtype=np.int16), {"_Unsigned": "true", "scale_factor": np.array([1.0]), "add_offset": np.array([0.0])})
        self.assertEqual(float(big[0]), 32768.0)
        plain = decode(np.array([1.5, -9.0], dtype=np.float32), {"_FillValue": np.array([-9.0], dtype=np.float32)})
        self.assertTrue(plain[0] == 1.5 and np.isnan(plain[1]))


class Zones(unittest.TestCase):
    def test_zonal_stats_ignore_nan_and_negative_zones(self):
        values = np.array([[1.0, 3.0, np.nan], [10.0, 20.0, 99.0]])
        zones = np.array([[0, 0, 0], [1, 1, -1]])
        stats = zonal_stats(values, zones)
        self.assertEqual(stats[0], {"count": 2, "mean": 2.0, "max": 3.0})
        self.assertEqual(stats[1], {"count": 2, "mean": 15.0, "max": 20.0})
        with self.assertRaises(ValueError):
            zonal_stats(values, zones[:1])

    def test_hourly_anomaly_compares_a_pixel_with_itself_at_the_same_hour(self):
        rng = np.random.default_rng(0)
        hours = np.tile([6, 18], 20)
        cube = np.where(hours == 18, 310.0, 290.0)[:, None, None] + rng.normal(0, 1, (40, 2, 2))
        cube[39, 0, 0] = 330.0  # hot outlier at 18 UTC
        score = hourly_anomaly(cube.astype(np.float32), hours)
        self.assertGreater(score[39, 0, 0], 8)
        self.assertLess(np.nanmax(np.abs(score[:39])), 6)  # the day/night cycle alone is not an anomaly
        sparse = cube.copy(); sparse[4:, 1, 1] = np.nan
        self.assertTrue(np.isnan(hourly_anomaly(sparse, hours)[:, 1, 1]).all())
        with self.assertRaises(ValueError):
            hourly_anomaly(cube, hours[:3])


class FireCross(unittest.TestCase):
    def test_zone_raster_assigns_points_to_the_cell_that_contains_them(self):
        window = aoi_window([-57.5, -17.5, -57.0, -17.0], AXIS_X, AXIS_Y, PROJ)
        lat, lon, _, _ = window_geometry(window, AXIS_X, AXIS_Y, PROJ)
        zones = zone_raster(lat, lon, window, AXIS_X, AXIS_Y, PROJ)
        np.testing.assert_array_equal(zones, np.arange(lat.size).reshape(lat.shape))  # every cell centre maps to itself
        nudged = zone_raster(lat + 0.004, lon + 0.004, window, AXIS_X, AXIS_Y, PROJ)  # about 0.4 km: still inside
        np.testing.assert_array_equal(nudged, zones)
        self.assertEqual(int(zone_raster(np.array([-10.0]), np.array([-57.2]), window, AXIS_X, AXIS_Y, PROJ)[0]), -1)

    def test_zonal_means_average_power_not_decibels(self):
        zones = np.array([[0, 0, 1], [1, -1, 2]])
        db = np.array([[-10.0, -20.0, np.nan], [-13.0, 0.0, np.nan]])
        mean, fraction = zonal_mean_db(db, zones, 3)
        self.assertAlmostEqual(mean[0], 10 * np.log10((0.1 + 0.01) / 2), places=6)  # -12.6 dB, not -15
        self.assertAlmostEqual(mean[1], -13.0, places=6)
        self.assertTrue(np.isnan(mean[2]))
        np.testing.assert_allclose(fraction, [1.0, 0.5, 0.0])
        plain, _ = zonal_mean(np.array([[1.0, 3.0, 5.0], [7.0, 100.0, np.nan]]), zones, 3)
        np.testing.assert_allclose(plain[:2], [2.0, 6.0])
        share = zonal_fraction(np.array([[1, 0, 1], [1, 1, 0]]), np.ones((2, 3), bool), zones, 3)
        np.testing.assert_allclose(share, [0.5, 1.0, 0.0])

    def test_window_labels_exclude_the_start_and_include_the_end(self):
        times = np.array(["2026-09-03T09:00", "2026-09-03T10:00", "2026-09-15T09:00", "2026-09-15T10:00"], dtype="datetime64[m]")
        flags = np.zeros((4, 1, 3), dtype=bool)
        flags[0, 0, 0] = flags[2, 0, 1] = flags[3, 0, 2] = True
        np.testing.assert_array_equal(window_any(flags, times, "2026-09-03T09:00", "2026-09-15T09:00")[0], [False, True, False])
        self.assertFalse(window_any(flags, times, "2026-10-01T00:00", "2026-10-02T00:00").any())

    def test_neighbour_fraction_and_rank_auc(self):
        flags = np.zeros((3, 3), dtype=bool); flags[1, 1] = True
        share = neighbour_fraction(flags)
        self.assertAlmostEqual(share[0, 0], 1 / 3); self.assertAlmostEqual(share[0, 1], 1 / 5); self.assertEqual(share[1, 1], 0)
        self.assertEqual(rank_auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]), 1.0)
        self.assertEqual(rank_auc([1, 1, 1, 1], [0, 1, 0, 1]), 0.5)
        self.assertAlmostEqual(rank_auc([0.1, 0.9, 0.5, np.nan], [0, 0, 1, 1]), 0.5)
        self.assertIsNone(rank_auc([0.1, 0.2], [0, 0]))


if __name__ == "__main__":
    unittest.main()
