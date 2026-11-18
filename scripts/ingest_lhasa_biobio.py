"""Archive dated NASA LHASA regional samples without downloading global rasters."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.windows import Window


DATES = ("20260131", "20261116")
BOUNDS = (-74.0, -39.0, -70.0, -36.0)  # west, south, east, north
ROOT = Path("catalog/lhasa_biobio")
SOURCE = "https://portal.nccs.nasa.gov/datashare/landslides/nrt/hazard/tif"


def ingest(date: str) -> dict:
    url = f"{SOURCE}/{date}T0000.tif"
    with rasterio.open(f"/vsicurl/{url}") as src:
        if str(src.crs) != "EPSG:4326" or src.count != 1:
            raise ValueError(f"Unexpected LHASA grid: {url}")
        west, south, east, north = BOUNDS
        corners = [src.index(west, south), src.index(east, north)]
        rows, cols = zip(*corners)
        window = Window(min(cols), min(rows), abs(cols[1] - cols[0]) + 1, abs(rows[1] - rows[0]) + 1)
        values = src.read(1, window=window)
        # NASA's GeoTIFF is south-up. Flip it to conventional north-up for local use.
        source_transform = src.window_transform(window)
        if source_transform.e < 0:
            raise ValueError("Unexpected north-up source; review the transform before ingest")
        transform = Affine(source_transform.a, 0, source_transform.c,
                           0, -source_transform.e, source_transform.f + values.shape[0] * source_transform.e)
        values = values[::-1].astype("float32")
        valid = np.isfinite(values) & (values != src.nodata)
        if not valid.any():
            raise ValueError(f"No valid LHASA cells for Biobío on {date}")
        if float(values[valid].min()) < 0 or float(values[valid].max()) > 1:
            raise ValueError("LHASA values outside probability range")
        path = ROOT / f"lhasa_{date}.tif"
        profile = {
            "driver": "GTiff", "height": values.shape[0], "width": values.shape[1],
            "count": 1, "dtype": "float32", "crs": src.crs, "transform": transform,
            "nodata": -9999.0, "compress": "deflate", "predictor": 3, "tiled": True,
            "blockxsize": 256, "blockysize": 256,
        }
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(np.where(valid, values, -9999.0), 1)
        return {
            "date_utc": f"{date[:4]}-{date[4:6]}-{date[6:]}T00:00:00Z",
            "source_url": url,
            "asset": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "width": values.shape[1], "height": values.shape[0],
            "valid_cells": int(valid.sum()), "total_cells": int(valid.size),
            "min_probability": float(values[valid].min()),
            "max_probability": float(values[valid].max()),
        }


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    products = [ingest(date) for date in DATES]
    manifest = {
        "product": "NASA LHASA rainfall-triggered landslide nowcast",
        "publisher_version": "2.1.1",
        "version_note": "La versión procede de la documentación NASA; el GeoTIFF no contiene una etiqueta de versión.",
        "documentation": "https://github.com/nasa/LHASA/blob/master/README.md",
        "source_resolution_arcsec": 30,
        "bounds_requested_wsen": BOUNDS,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "operational_alert": False,
        "limits": [
            "Regional model probability at about 1 km, not a slope or GPX segment measurement.",
            "Archived dates; no guarantee that the newest file remains current.",
            "No independent validation for Biobío and no safe-route inference.",
            "Does not cover every type of slope failure or rockfall.",
        ],
        "products": products,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for product in products:
        print(product["asset"], product["valid_cells"], product["sha256"])
