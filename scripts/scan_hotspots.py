"""Where did GOES-19 see confident hot spots? Site selection for fire work, before downloading any NISAR scene.

Counts ABI-L2-FDCF fire pixels (classes processed, saturated, high probability) over a region and period on a
regular lat/lon grid, and joins each 1-degree cell with the NISAR GCOV catalogue index (catalog/global).
Public NOAA bucket, no credentials. Writes catalog/hotspot_scan.json.

    python scripts/scan_hotspots.py --bbox -82 -56 -34 13 --start 2026-07-01 --end 2026-11-13 --hours 15 16 17 18 19 20
"""
import argparse
import io
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_thermal import BUCKET, START, RangeFile, axis, list_keys
from sarwatch.ml.thermal import CONFIDENT_FIRE, aoi_window, fire_class, latlon

_SESSION = None


def fire_pixels(job):
    """(stamp, rows, cols, classes, navigation) of every fire pixel inside the bbox window of one FDC file."""
    global _SESSION
    import h5py
    import requests
    if _SESSION is None:
        _SESSION = requests.Session()
    stamp, key, bbox = job
    for attempt in range(4):
        try:
            handle = RangeFile(BUCKET + key, _SESSION, block=1 << 20)
            with h5py.File(io.BufferedReader(handle, buffer_size=handle.block), "r") as source:
                proj = {k: float(np.asarray(v).ravel()[0]) for k, v in source["goes_imager_projection"].attrs.items() if k in ("semi_major_axis", "semi_minor_axis", "perspective_point_height", "longitude_of_projection_origin")}
                navigation = (axis(source["x"]), axis(source["y"]), tuple(sorted(proj.items())))
                row0, row1, col0, col1 = aoi_window(bbox, navigation[0], navigation[1], proj, pad=0)
                classes = fire_class(source["Mask"][row0:row1, col0:col1])
            rows, cols = np.nonzero(classes)
            return stamp, (rows + row0).astype(np.int32), (cols + col0).astype(np.int32), classes[rows, cols], navigation, None
        except Exception as error:
            failure = f"{type(error).__name__}: {error}"
            time.sleep(2 ** attempt)
    return stamp, None, None, None, None, {"key": key, "error": failure}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--hours", nargs="+", type=int, default=[15, 16, 17, 18, 19, 20], help="horas UTC muestreadas (un archivo por hora)")
    parser.add_argument("--cell-degrees", type=float, default=0.25)
    parser.add_argument("--min-detections", type=int, default=5, help="celdas con menos detecciones confiables no se escriben")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--output", default="catalog/hotspot_scan.json")
    args = parser.parse_args()
    import requests
    session = requests.Session()
    first, last = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc), datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    started = time.time()
    with ThreadPoolExecutor(16) as pool:
        listings = list(pool.map(lambda day: list_keys(session, "ABI-L2-FDCF/" + day.strftime("%Y/%j/")), days))
    keys = {}
    for listing in listings:
        for key in listing:
            match = START.search(key)
            if match and match.group(1)[9:11] == "00" and int(match.group(1)[7:9]) in args.hours:
                keys[match.group(1)] = key
    if not keys:
        raise SystemExit("Sin archivos FDC en el período")
    size = args.cell_degrees
    grid = defaultdict(lambda: {"confident": 0, "any": 0, "days": set(), "pixels": set(), "months": defaultdict(int)})
    failures, navigation, files = [], None, 0
    with ProcessPoolExecutor(args.workers) as pool:
        for stamp, rows, cols, classes, nav, failure in pool.map(fire_pixels, [(s, k, args.bbox) for s, k in sorted(keys.items())], chunksize=4):
            if failure:
                failures.append(failure)
                continue
            files += 1
            if navigation is None:
                navigation = nav
            elif nav != navigation:
                raise SystemExit(f"Navegación distinta en {stamp}")
            if not rows.size:
                continue
            proj = dict(navigation[2])
            lat, lon = latlon(navigation[0][1] + navigation[0][0] * cols, navigation[1][1] + navigation[1][0] * rows, proj)
            day = stamp[:7]
            month = datetime.strptime(day, "%Y%j").strftime("%Y-%m")
            for la, lo, row, col, code in zip(lat, lon, rows, cols, classes):
                if not (args.bbox[0] <= lo <= args.bbox[2] and args.bbox[1] <= la <= args.bbox[3]):
                    continue
                cell = grid[(float(np.floor(lo / size) * size), float(np.floor(la / size) * size))]
                cell["any"] += 1
                if int(code) in CONFIDENT_FIRE:
                    cell["confident"] += 1
                    cell["days"].add(day)
                    cell["pixels"].add((int(row), int(col)))
                    cell["months"][month] += 1
    coverage = {}
    index = Path("catalog/global/coverage_1deg.json")
    if index.is_file():
        coverage = {(c["lon"], c["lat"]): c for c in json.loads(index.read_text(encoding="utf-8"))["cells"]}
    cells = []
    for (west, south), cell in grid.items():
        if cell["confident"] < args.min_detections:
            continue
        nisar = coverage.get((int(np.floor(west)), int(np.floor(south))))
        cells.append({"west": round(west, 4), "south": round(south, 4), "confident_detections": cell["confident"], "all_detections": cell["any"], "days_with_confident": len(cell["days"]), "goes_pixels_with_confident": len(cell["pixels"]), "confident_by_month": dict(sorted(cell["months"].items())),
                      "nisar_1deg": {k: nisar[k] for k in ("granules", "dates", "geometries", "first_date", "last_date")} if nisar else None})
    cells.sort(key=lambda c: -c["goes_pixels_with_confident"])
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(), "source": BUCKET + "ABI-L2-FDCF", "bbox_wgs84": args.bbox, "period_utc": [args.start, args.end], "hours_utc": args.hours, "files_read": files, "failures": failures,
           "cell_degrees": size, "confident_classes": list(CONFIDENT_FIRE), "min_detections": args.min_detections, "cells_written": len(cells),
           "note": "Una muestra por hora en las horas indicadas: es un piso de la actividad, no un inventario. Las fechas NISAR son del índice CMR por celda de 1 grado (disponibilidad en catálogo, no cobertura útil validada).", "cells": cells}
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{files} archivos, {len(failures)} fallos, {len(cells)} celdas con ≥ {args.min_detections} detecciones confiables, {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
