"""Hourly ERA5 fire weather over an AOI (Open-Meteo archive, no credentials): wind, gusts, air humidity,
temperature, vapour pressure deficit and rain on a regular grid of points.

Writes <data>/<aoi>/weather/{era5_hourly.npz,manifest.json}. ERA5 is a reanalysis of about 0.25 degrees:
the provider answers with the cell it used, so neighbouring requested points can share one cell.

    python scripts/fetch_fire_weather.py --aoi biobio_fuego --start 2026-01-01 --end 2026-05-21
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.grids import load_manifest
from weather import FIRE_HOURLY, fetch_fire_weather


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="inclusive, UTC")
    parser.add_argument("--step-degrees", type=float, default=0.25)
    parser.add_argument("--batch", type=int, default=6, help="puntos por petición")
    args = parser.parse_args()
    root = Path(args.data_dir) / args.aoi
    west, south, east, north = load_manifest(root)["bbox_wgs84"]
    half = args.step_degrees / 2
    points = [(round(float(lat), 4), round(float(lon), 4)) for lat in np.arange(south + half, north, args.step_degrees) for lon in np.arange(west + half, east, args.step_degrees)]
    cells, retrieved = [], []
    for first in range(0, len(points), args.batch):
        for attempt in range(5):
            try:
                result = fetch_fire_weather(points[first:first + args.batch], args.start, args.end)
                break
            except OSError:  # rate limit or network hiccup: wait and retry, never fill with invented values
                if attempt == 4:
                    raise
                time.sleep(15 * (attempt + 1))
        cells += result["cells"]
        retrieved.append(result["retrieved_utc"])
        print(f"{min(first + args.batch, len(points))}/{len(points)} puntos", flush=True)
        time.sleep(1)
    times = cells[0]["hourly"]["time"]
    if any(cell["hourly"]["time"] != times for cell in cells):
        raise SystemExit("Los puntos no comparten eje temporal")
    out = root / "weather"
    out.mkdir(parents=True, exist_ok=True)
    arrays = {name: np.array([[np.nan if v is None else v for v in cell["hourly"][name]] for cell in cells], dtype=np.float32) for name in FIRE_HOURLY}
    np.savez_compressed(out / "era5_hourly.npz", times=np.array(times), requested_lat=np.array([p[0] for p in points]), requested_lon=np.array([p[1] for p in points]),
                        cell_lat=np.array([c["latitude"] for c in cells]), cell_lon=np.array([c["longitude"] for c in cells]), cell_elevation_m=np.array([c.get("elevation", np.nan) for c in cells], dtype=np.float32), **arrays)
    manifest = {"aoi": args.aoi, "provider": "Open-Meteo Historical Weather API", "model": "ERA5 (reanálisis)", "license": "CC BY 4.0, atribución a Open-Meteo y Copernicus/ECMWF",
                "period_utc": [times[0], times[-1]], "hours": len(times), "points": len(points), "distinct_provider_cells": len({(c["latitude"], c["longitude"]) for c in cells}), "step_degrees": args.step_degrees,
                "units": cells[0]["hourly_units"], "missing_fraction": {name: round(float(np.isnan(a).mean()), 4) for name, a in arrays.items()}, "retrieved_utc": [retrieved[0], retrieved[-1]],
                "limitations": ["Reanálisis en rejilla gruesa: no es una estación ni el viento dentro de una quebrada.", "No es pronóstico: describe las horas pasadas del período.", "Los valores ausentes se conservan como NaN; no se rellenan."]}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
