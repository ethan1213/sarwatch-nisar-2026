"""Build a world index of every NISAR GCOV granule from CMR metadata (no imagery download).

Writes catalog/global/gcov_index.csv.gz (one row per granule) and catalog/global/coverage_1deg.json
(per 1-degree cell: granule count, distinct dates, repeat geometries) for the global coverage map.
"""
import argparse
import csv
import gzip
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
OUT = Path("catalog/global")


def pages(short_name, page_size=2000):
    search_after = None
    while True:
        query = urlencode({"short_name": short_name, "page_size": page_size, "sort_key": "-start_date"})
        request = Request(f"{CMR}?{query}", headers={"CMR-Search-After": search_after} if search_after else {})
        for attempt in range(4):
            try:
                with urlopen(request, timeout=120) as response:
                    body = json.load(response)
                    search_after = response.headers.get("CMR-Search-After")
                    hits = int(response.headers.get("CMR-Hits", 0))
                break
            except Exception as exc:
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        entries = body["feed"]["entry"]
        if not entries:
            return
        yield hits, entries
        if not search_after:
            return


def bbox_of(entry):
    """Approximate lon/lat bounding box from the CMR polygon (lat lon pairs)."""
    lats, lons = [], []
    for group in entry.get("polygons", []):
        for ring in group:
            values = list(map(float, ring.split()))
            lats += values[0::2]
            lons += values[1::2]
    if not lats:
        for box in entry.get("boxes", []):
            s, w, n, e = map(float, box.split())
            lats += [s, n]
            lons += [w, e]
    if not lats:
        return None
    return min(lons), min(lats), max(lons), max(lats)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--short-name", default="NISAR_L2_GCOV_PROVISIONAL_V1")
    parser.add_argument("--max-pages", type=int, default=0, help="0 = todas")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    index_path = OUT / "gcov_index.csv.gz"
    cells = defaultdict(lambda: {"granules": 0, "dates": set(), "geometries": set(), "bytes": 0.0})
    n = 0
    t0 = time.perf_counter()
    with gzip.open(index_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "granule", "time_start", "track", "direction", "frame", "mode", "polarization", "frequency", "size_mib", "west", "south", "east", "north"])
        for page, (hits, entries) in enumerate(pages(args.short_name), start=1):
            for e in entries:
                parts = e["producer_granule_id"].split("_")
                key = parts[5:11] if len(parts) > 11 else [""] * 6
                bbox = bbox_of(e)
                size = float(e.get("granule_size", 0) or 0)
                writer.writerow([e["id"], e["producer_granule_id"], e["time_start"], *key, round(size, 1), *(round(v, 4) for v in bbox)] if bbox else [e["id"], e["producer_granule_id"], e["time_start"], *key, round(size, 1), "", "", "", ""])
                n += 1
                if bbox and (bbox[2] - bbox[0]) < 20:  # skip antimeridian-wrapping footprints in the grid summary
                    w, s, ea, no = bbox
                    for lat in range(int(s // 1), int(no // 1) + 1):
                        for lon in range(int(w // 1), int(ea // 1) + 1):
                            cell = cells[(lon, lat)]
                            cell["granules"] += 1
                            cell["dates"].add(e["time_start"][:10])
                            cell["geometries"].add("_".join(key[:3]))
                            cell["bytes"] += size * 1024 * 1024
            print(f"página {page}: {n}/{hits} granulos, {time.perf_counter() - t0:.0f} s", flush=True)
            if args.max_pages and page >= args.max_pages:
                break
    coverage = {"generated_utc": datetime.now(timezone.utc).isoformat(), "short_name": args.short_name, "granules_indexed": n, "cells": [{"lon": lon, "lat": lat, "granules": c["granules"], "dates": len(c["dates"]), "geometries": len(c["geometries"]), "first_date": min(c["dates"]), "last_date": max(c["dates"])} for (lon, lat), c in cells.items()], "note": "Celdas de 1 grado tocadas por la huella nominal; cuenta disponibilidad en el catálogo, no cobertura útil validada ni datos descargados."}
    (OUT / "coverage_1deg.json").write_text(json.dumps(coverage, ensure_ascii=False), encoding="utf-8")
    total_tb = sum(c["bytes"] for c in cells.values()) / 1e12
    print(json.dumps({"granules": n, "cells": len(cells), "index": str(index_path), "approx_tb_counted_per_cell": round(total_tb, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
