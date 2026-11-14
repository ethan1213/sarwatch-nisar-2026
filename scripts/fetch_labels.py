"""Sentinel-2 water labels on the NISAR grid for every scene of an AOI manifest.

Reads data/<aoi>/manifest.json, searches Microsoft Planetary Computer for Sentinel-2 L2A within
+/- WINDOW days of each NISAR acquisition, computes MNDWI water labels per solar day, and composites
them nearest-first. Writes data/<aoi>/labels/<date>_water.tif (+ _source_offset.tif) and labels/manifest.json.
No credentials required. Labels describe optical water on their own date; they are not NISAR truth.
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.grids import geobox_from_manifest, load_manifest, manifest_grid, write_cog
from sarwatch.ml.labels import NODATA, WATER_THRESHOLD, composite_nearest, label_summary, water_label

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-2-l2a"


def fetch_scene_labels(catalog, manifest, scene_date, window_days, max_cloud, sign):
    import odc.stac
    geobox = geobox_from_manifest(manifest)
    start, end = scene_date - timedelta(days=window_days), scene_date + timedelta(days=window_days)
    search = catalog.search(collections=[COLLECTION], bbox=manifest["bbox_wgs84"], datetime=f"{start.isoformat()}/{end.isoformat()}", query={"eo:cloud_cover": {"lt": max_cloud}})
    items = list(search.items())
    if not items:
        return None
    data = odc.stac.load(items, bands=["B03", "B11", "SCL"], geobox=geobox, groupby="solar_day", resampling={"B03": "average", "B11": "average", "SCL": "nearest"}, patch_url=sign, chunks=None)
    observations, used = [], []
    for t in data.time.values:
        day = datetime.fromtimestamp(int(t.astype("datetime64[s]").astype(int)), tz=timezone.utc).date()
        offset = abs((day - scene_date).days)
        slab = data.sel(time=t)
        label = water_label(slab["B03"].values, slab["B11"].values, slab["SCL"].values)
        observations.append((offset, label))
        used.append({"solar_day": day.isoformat(), "offset_days": offset, "items": [i.id for i in items if i.datetime.date() == day], "valid_fraction": float((label != NODATA).mean())})
    label, source = composite_nearest(observations)
    return label, source, used


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", required=True, help="Subdirectorio bajo DATA_DIR con manifest.json: . para Pantanal, metropolitana o valparaiso")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--window-days", type=int, default=3)
    parser.add_argument("--max-cloud", type=float, default=40)
    parser.add_argument("--min-valid", type=float, default=0.5, help="Fraccion valida minima para conservar la etiqueta")
    args = parser.parse_args()
    import planetary_computer
    import pystac_client
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    crs, transform, _ = manifest_grid(manifest)
    catalog = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    out = root / "labels"
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for scene in manifest["scenes"]:
        scene_date = date.fromisoformat(scene["fecha_observacion"][:10])
        result = fetch_scene_labels(catalog, manifest, scene_date, args.window_days, args.max_cloud, planetary_computer.sign)
        if result is None:
            records.append({"scene_id": scene["id"], "fecha_observacion": scene["fecha_observacion"], "status": "sin_sentinel2_en_ventana"})
            print(scene["id"], "sin Sentinel-2 en la ventana", flush=True)
            continue
        label, source, used = result
        summary = label_summary(label)
        status = "ok" if summary["valid_fraction"] >= args.min_valid else "cobertura_insuficiente"
        name = f"{scene_date.isoformat()}_water.tif"
        tags = {"source": "Sentinel-2 L2A via Microsoft Planetary Computer", "rule": f"MNDWI=(B03-B11)/(B03+B11) > {WATER_THRESHOLD}", "scl_excluded": "0,1,2,3,8,9,10,11", "nisar_scene": scene["granulo"], "window_days": args.window_days, "values": "1 agua, 0 no agua, 255 sin observacion"}
        write_cog(out / name, label, transform, crs, NODATA, "uint8", tags)
        write_cog(out / name.replace("_water", "_source_offset"), source, transform, crs, 255, "uint8", {"meaning": "dias de separacion entre la observacion optica usada y la fecha NISAR"})
        records.append({"scene_id": scene["id"], "fecha_observacion": scene["fecha_observacion"], "status": status, "label": name, **summary, "observations": used})
        print(scene["id"], status, summary, flush=True)
    (out / "manifest.json").write_text(json.dumps({"aoi": args.aoi, "collection": COLLECTION, "stac": STAC, "rule": f"MNDWI > {WATER_THRESHOLD}", "window_days": args.window_days, "max_cloud": args.max_cloud, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "labels": records, "limits": ["Etiqueta óptica de agua abierta; no detecta agua bajo vegetación.", "Fecha óptica distinta de la fecha NISAR hasta window_days.", "MNDWI > 0 es una regla convencional, no una verdad de terreno."]}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
