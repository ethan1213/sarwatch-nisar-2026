"""Pre/post-fire dNBR and burn severity on an AOI grid, from Sentinel-2 L2A via Planetary Computer.

Writes data/<aoi>/wildfire/dnbr.tif, severity.tif and wildfire/manifest.json. No credentials needed.
Dates default to a plausible window around the Las Condes-area fire this module was built for
(Dec 2025); THE TEAM MUST CONFIRM THE REAL FIRE DATE AND PERIMETER (e.g. from CONAF) and re-run
with --pre-start/--pre-end/--post-start/--post-end once known. Until then this is a worked example,
not a verified burn scar.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.grids import geobox_from_manifest, load_manifest, manifest_grid, write_cog
from sarwatch.ml.wildfire import NODATA, dnbr, nbr, severity_class, severity_summary

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def best_scene(catalog, bbox, start, end, sign, max_cloud=30):
    import odc.stac
    items = list(catalog.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{start}/{end}", query={"eo:cloud_cover": {"lt": max_cloud}}).items())
    if not items:
        return None, None
    items.sort(key=lambda i: i.properties.get("eo:cloud_cover", 100))
    chosen = items[0]
    return chosen, odc.stac.load([chosen], bands=["B08", "B12", "SCL"], patch_url=sign, chunks=None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", default="metropolitana")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--pre-start", default="2025-11-01")
    parser.add_argument("--pre-end", default="2025-11-30")
    parser.add_argument("--post-start", default="2026-02-01")
    parser.add_argument("--post-end", default="2026-02-28")
    parser.add_argument("--max-cloud", type=float, default=30)
    args = parser.parse_args()
    import planetary_computer
    import pystac_client
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    crs, transform, shape = manifest_grid(manifest)
    geobox = geobox_from_manifest(manifest)
    catalog = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)

    import odc.stac
    pre_item, _ = best_scene(catalog, manifest["bbox_wgs84"], args.pre_start, args.pre_end, planetary_computer.sign, args.max_cloud)
    post_item, _ = best_scene(catalog, manifest["bbox_wgs84"], args.post_start, args.post_end, planetary_computer.sign, args.max_cloud)
    if pre_item is None or post_item is None:
        raise SystemExit("Sin escenas Sentinel-2 con nubes aceptables en alguna de las dos ventanas; ampliar fechas o tolerancia de nubes")
    # SCL is categorical (cloud/water/vegetation codes): averaging it produces fractional values that
    # match no real class, which silently discarded ~99.9% of the AOI in an earlier run. Only B08/B12
    # (continuous reflectance-like DNs) may be averaged; SCL must use nearest-neighbour.
    data = odc.stac.load([pre_item, post_item], bands=["B08", "B12", "SCL"], geobox=geobox, groupby="solar_day", resampling={"B08": "average", "B12": "average", "SCL": "nearest"}, patch_url=planetary_computer.sign, chunks=None)
    order = sorted(range(data.time.size), key=lambda i: data.time.values[i])
    pre_slab, post_slab = data.isel(time=order[0]), data.isel(time=order[-1])
    valid_pre = ~np.isin(pre_slab["SCL"].values, (0, 1, 2, 3, 8, 9, 10, 11))
    valid_post = ~np.isin(post_slab["SCL"].values, (0, 1, 2, 3, 8, 9, 10, 11))
    nbr_pre = nbr(pre_slab["B08"].values, pre_slab["B12"].values)
    nbr_post = nbr(post_slab["B08"].values, post_slab["B12"].values)
    nbr_pre[~valid_pre] = np.nan
    nbr_post[~valid_post] = np.nan
    delta = dnbr(nbr_pre, nbr_post)
    severity = severity_class(delta)

    out = root / "wildfire"
    write_cog(out / "dnbr.tif", delta, transform, crs, np.nan, "float32", {"source": "Sentinel-2 L2A via Microsoft Planetary Computer", "pre_item": pre_item.id, "post_item": post_item.id, "pre_date": str(pre_item.datetime.date()), "post_date": str(post_item.datetime.date()), "formula": "NBR_pre - NBR_post, NBR=(B08-B12)/(B08+B12)"})
    write_cog(out / "severity.tif", severity, transform, crs, NODATA, "uint8", {"classes": "0 sin_quema_o_rebrote,1 baja,2 moderada_baja,3 moderada_alta,4 alta (USGS/UNSPIDER dNBR breaks)", "status": "ventanas de fecha por confirmar con CONAF; ver docstring del script"})
    summary = severity_summary(severity)
    manifest_out = {"aoi": args.aoi, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "pre_item": pre_item.id, "pre_date": str(pre_item.datetime.date()), "pre_cloud_cover": pre_item.properties.get("eo:cloud_cover"), "post_item": post_item.id, "post_date": str(post_item.datetime.date()), "post_cloud_cover": post_item.properties.get("eo:cloud_cover"), "severity_summary": summary, "limits": ["Ventanas de fecha de ejemplo; confirmar fecha y perímetro real del incendio con CONAF/Sernageomin antes de publicar.", "dNBR describe daño a la vegetación observado por óptico, no humedad ni estabilidad del suelo.", "Nubes pueden dejar huecos; revisar severity_summary.n frente al total de píxeles del AOI."]}
    (out / "manifest.json").write_text(json.dumps(manifest_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pre_date": manifest_out["pre_date"], "post_date": manifest_out["post_date"], "severity_summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
