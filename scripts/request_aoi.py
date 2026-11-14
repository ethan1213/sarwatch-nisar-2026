"""On-demand AOI pipeline: CMR search -> same-geometry pair selection -> (download) -> prepare -> register.

Measures wall time, peak memory and bytes so that scaling claims rest on numbers. The download step needs an
interactive Earthdata login (scripts/download_scenes.py); everything else is unattended.

Example:
  python scripts/request_aoi.py select  --name curico --bbox -71.4 -35.2 -71.0 -34.9 --start 2026-09-01
  python scripts/download_scenes.py --candidates catalog/curico_candidates.json --target data_raw/curico
  python scripts/request_aoi.py prepare --name curico
"""
import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "aois.json"


def geometry_key(granule):
    return tuple(granule.split("_")[5:11])


def cmr_search(bbox, start, end):
    url = "https://cmr.earthdata.nasa.gov/search/granules.json?" + urlencode({"short_name": "NISAR_L2_GCOV_PROVISIONAL_V1", "bounding_box": ",".join(map(str, bbox)), "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z", "page_size": 200, "sort_key": "-start_date"})
    with urlopen(url, timeout=60) as response:
        return url, json.load(response)["feed"]["entry"]


def select_pairs(entries, min_scenes=2):
    """Group granules by nominal geometry; keep groups with at least min_scenes acquisitions."""
    groups = defaultdict(list)
    for e in entries:
        groups[geometry_key(e["producer_granule_id"])].append(e)
    result = []
    for key, scenes in groups.items():
        scenes.sort(key=lambda e: e["time_start"])
        if len(scenes) >= min_scenes:
            result.append((key, scenes))
    result.sort(key=lambda item: (-len(item[1]), item[1][-1]["time_start"]))
    return result


def to_scene(e):
    return {"id": e["id"], "granulo": e["producer_granule_id"], "fecha_observacion": e["time_start"], "url_metadatos": f"https://cmr.earthdata.nasa.gov/search/concepts/{e['id']}.umm_json", "estimated_mib": float(e.get("granule_size", 0)), "url_hdf5": next((x["href"] for x in e.get("links", []) if x.get("href", "").endswith(".h5") and x.get("href", "").startswith("https://")), None)}


def register(name, payload):
    registry = json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.is_file() else {"aois": {}}
    registry["aois"].setdefault(name, {}).update(payload)
    REGISTRY.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_select(args):
    t0 = time.perf_counter()
    end = args.end or datetime.now(timezone.utc).date().isoformat()
    url, entries = cmr_search(args.bbox, args.start, end)
    pairs = select_pairs(entries)
    if not pairs:
        raise SystemExit("Sin grupos de escenas con geometría repetida en el período")
    key, scenes = pairs[0]
    catalog = {"region": args.name, "bbox_wgs84": args.bbox, "status": "candidatos seleccionados por geometría nominal; pendiente descarga, checksum y preparación", "geometry_key": list(key), "scenes": [to_scene(e) for e in scenes]}
    (ROOT / "catalog" / f"{args.name}_scenes.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "catalog" / f"{args.name}_candidates.json").write_text(json.dumps({"query": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "candidates": catalog["scenes"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    estimated_gb = sum(s["estimated_mib"] for s in catalog["scenes"]) / 1024
    register(args.name, {"bbox_wgs84": args.bbox, "selected_utc": datetime.now(timezone.utc).isoformat(), "n_scenes": len(scenes), "geometry_key": list(key), "estimated_download_gb": round(estimated_gb, 2), "select_seconds": round(time.perf_counter() - t0, 2), "status": "seleccionado"})
    print(f"{args.name}: {len(scenes)} escenas con geometría {'_'.join(key)}, descarga estimada {estimated_gb:.1f} GB ({len(entries)} granulos consultados)")
    print(f"Siguiente paso: python scripts/download_scenes.py --candidates catalog/{args.name}_candidates.json --target data_raw/{args.name}")


def _prepare(args):
    catalog = ROOT / "catalog" / f"{args.name}_scenes.json"
    raw = ROOT / "data_raw" / args.name
    output = ROOT / "data" / args.name
    if not catalog.is_file():
        raise SystemExit("Primero ejecutar select")
    t0 = time.perf_counter()
    command = [sys.executable, str(ROOT / "scripts" / "prepare.py"), "--raw", str(raw), "--output", str(output), "--catalog", str(catalog)]
    completed = subprocess.run(command, capture_output=True, text=True)
    seconds = time.perf_counter() - t0
    if completed.returncode != 0:
        print(completed.stdout[-2000:], completed.stderr[-2000:])
        raise SystemExit("prepare.py falló")
    raw_bytes = sum(p.stat().st_size for p in raw.glob("*.h5"))
    derived_bytes = sum(p.stat().st_size for p in output.glob("*.tif"))
    payload = {"prepared_utc": datetime.now(timezone.utc).isoformat(), "prepare_seconds": round(seconds, 1), "raw_bytes": raw_bytes, "derived_bytes": derived_bytes, "compression_ratio_derived_vs_float32": None, "status": "preparado; etiquetas, covariables y evaluación pendientes"}
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    grid = manifest["grid"]
    uncompressed = grid["height"] * grid["width"] * 4 * 2 * len(manifest["scenes"])
    payload["compression_ratio_derived_vs_float32"] = round(uncompressed / derived_bytes, 2) if derived_bytes else None
    register(args.name, payload)
    print(json.dumps(payload, ensure_ascii=False))
    print(f"Siguiente: python scripts/fetch_labels.py --aoi {args.name} && python scripts/fetch_covariates.py --aoi {args.name}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("select")
    s.add_argument("--name", required=True)
    s.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    s.add_argument("--start", required=True)
    s.add_argument("--end")
    s.set_defaults(func=cmd_select)
    p = sub.add_parser("prepare")
    p.add_argument("--name", required=True)
    p.set_defaults(func=_prepare)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
