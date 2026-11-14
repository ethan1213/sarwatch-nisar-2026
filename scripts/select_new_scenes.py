"""Find new NISAR GCOV granules that share geometry with an existing AOI series (CMR query, no login)."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def geometry_key(granule):
    parts = granule.split("_")
    return tuple(parts[5:11])  # track, direction, frame, mode, polarization, frequency


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="catalog/scenes.json", help="Catalogo del AOI con bbox_wgs84 y escenas existentes")
    parser.add_argument("--output", default="catalog/pantanal_candidates.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / args.catalog).read_text(encoding="utf-8"))
    keys = {geometry_key(s["granulo"]) for s in catalog["scenes"]}
    known = {s["id"] for s in catalog["scenes"]}
    latest = max(s["fecha_observacion"] for s in catalog["scenes"])
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = "https://cmr.earthdata.nasa.gov/search/granules.json?" + urlencode({"short_name": "NISAR_L2_GCOV_PROVISIONAL_V1", "bounding_box": ",".join(map(str, catalog["bbox_wgs84"])), "temporal": f"{latest},{end}", "page_size": 100, "sort_key": "-start_date"})
    with urlopen(url, timeout=60) as response:
        entries = json.load(response)["feed"]["entry"]
    candidates = []
    for e in entries:
        if e["id"] in known or geometry_key(e["producer_granule_id"]) not in keys:
            continue
        candidates.append({"id": e["id"], "granulo": e["producer_granule_id"], "fecha_observacion": e["time_start"], "url_metadatos": f"https://cmr.earthdata.nasa.gov/search/concepts/{e['id']}.umm_json", "estimated_mib": float(e.get("granule_size", 0)), "url_hdf5": next((x["href"] for x in e.get("links", []) if x.get("href", "").endswith(".h5") and x.get("href", "").startswith("https://")), None)})
    candidates.sort(key=lambda c: c["fecha_observacion"])
    (root / args.output).write_text(json.dumps({"query": url, "retrieved_utc": end, "geometry_keys": [list(k) for k in keys], "candidates": candidates, "status": "candidatos con misma geometria nominal; descargar, verificar checksum y preparar antes de usar"}, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in candidates:
        print(c["id"], c["fecha_observacion"][:10], round(c["estimated_mib"]), "MiB")
    print(len(candidates), "candidatos nuevos ->", args.output)


if __name__ == "__main__":
    main()
