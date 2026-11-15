"""Raster-to-PNG helpers for the API. Mirrors the reprojection and colour logic in
sarwatch/maps.py::raster_map and sarwatch/detections.py::categorical_overlay exactly, but
returns a plain RGBA array in EPSG:4326 instead of a folium layer - this process never
imports sarwatch.maps (pulls in streamlit/streamlit_folium at module scope).
"""
import base64
import io

import numpy as np
from PIL import Image
from rasterio.transform import array_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject

from sarwatch.detections import display_grid

SIZE = 600
LOW = np.array([32, 91, 135.0])
MID = np.array([242, 242, 232.0])
HIGH = np.array([198, 96, 28.0])
WATER_COLOR = (23, 112, 140, 200)
CHANGE_COLORS = {1: (32, 91, 135, 210), 2: (198, 96, 28, 210)}


def png_data_url(rgba):
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def sar_overlay(values, transform, crs, changes):
    """Blue-neutral-orange diverging scale: +-6 dB for differences, -30..10 dB for intensity.
    Returns (rgba uint8 HxWx4, bounds dict) with bounds in EPSG:4326."""
    height, width = values.shape
    bounds = array_bounds(height, width, transform)
    dst_transform, w, h = calculate_default_transform(crs, "EPSG:4326", width, height, *bounds, dst_width=SIZE, dst_height=SIZE)
    output = np.full((h, w), np.nan, dtype="float32")
    reproject(values, output, src_transform=transform, src_crs=crs, src_nodata=np.nan, dst_transform=dst_transform, dst_crs="EPSG:4326", dst_nodata=np.nan, resampling=Resampling.nearest)
    west, south, east, north = array_bounds(h, w, dst_transform)
    normalized = np.clip((output + 6) / 12 if changes else (output + 30) / 40, 0, 1)
    rgba = np.zeros((h, w, 4), dtype="uint8")
    z = np.nan_to_num(normalized)
    rgb = np.where((z <= 0.5)[:, :, None], LOW + (MID - LOW) * (z * 2)[:, :, None], MID + (HIGH - MID) * ((z - 0.5) * 2)[:, :, None])
    rgba[:, :, :3] = rgb.astype("uint8")
    rgba[:, :, 3] = np.isfinite(output).astype("uint8") * 190
    return rgba, {"south": south, "west": west, "east": east, "north": north}


def categorical_rgba(mask, transform, crs, kind):
    """kind: 'water' (class 1 teal) or 'change' (1 blue decrease, 2 orange increase)."""
    grid, bounds = display_grid(mask, transform, crs)
    (south, west), (north, east) = bounds
    rgba = np.zeros(grid.shape + (4,), dtype="uint8")
    if kind == "water":
        rgba[grid == 1] = WATER_COLOR
    else:
        for value, color in CHANGE_COLORS.items():
            rgba[grid == value] = color
    return rgba, {"south": south, "west": west, "east": east, "north": north}
