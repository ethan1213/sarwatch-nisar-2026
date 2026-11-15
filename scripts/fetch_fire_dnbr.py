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
from sarwatch.ml.wildfire import NODATA, boa_reflectance, dnbr, nbr, severity_class, severity_summary

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


MAX_ITEMS_PER_WINDOW = 6  # enough to mosaic adjacent MGRS tiles / relative orbits; see module docstring


def composite_nbr(catalog, bbox, start, end, geobox, sign, max_cloud, resampling, max_items=MAX_ITEMS_PER_WINDOW):
    """Mosaic several Sentinel-2 items into one NBR + validity layer on `geobox`.

    A single Sentinel-2 granule does not fill its whole nominal UTM tile square - the satellite's
    actual swath only covers a diagonal strip of it, so most of the square is legitimate no-data for
    that specific acquisition (confirmed here, 2026-11-14, by reading the raw source COG directly:
    within the geographically overlapping window the real pixel data was ~0.1% non-zero). Using a
    single lowest-cloud item therefore left ~99.9% of the AOI empty. The fix is to mosaic several
    items (adjacent tiles/orbits, nearby dates), filling each pixel from the first item in the
    priority order (lowest cloud first) that actually has a valid, unclouded value there.

    Returns (nbr_layer, valid_mask, items_used) where items_used lists only items that contributed
    at least one pixel.
    """
    import odc.stac
    items = list(catalog.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{start}/{end}", query={"eo:cloud_cover": {"lt": max_cloud}}).items())
    if not items:
        return None, None, []
    items.sort(key=lambda i: i.properties.get("eo:cloud_cover", 100))
    items = items[:max_items]
    nbr_layer = np.full(geobox.shape, np.nan, dtype=np.float32)
    valid_mask = np.zeros(geobox.shape, dtype=bool)
    used = []
    for item in items:
        if valid_mask.all():
            break
        data = odc.stac.load([item], bands=["B08", "B12", "SCL"], geobox=geobox, resampling=resampling, patch_url=sign, chunks=None)
        slab = data.isel(time=0)
        item_valid = ~np.isin(slab["SCL"].values, (0, 1, 2, 3, 8, 9, 10, 11))
        baseline = item.properties.get("s2:processing_baseline")
        if baseline is None:
            raise ValueError(f"{item.id}: sin versión de procesamiento; no se puede aplicar el offset de reflectancia")
        item_nbr = nbr(boa_reflectance(slab["B08"].values, baseline), boa_reflectance(slab["B12"].values, baseline))
        item_valid &= np.isfinite(item_nbr)
        fill = item_valid & ~valid_mask
        if not fill.any():
            continue
        nbr_layer[fill] = item_nbr[fill]
        valid_mask |= item_valid
        used.append({"id": item.id, "cloud_cover": item.properties.get("eo:cloud_cover"), "pixels_contributed": int(fill.sum())})
    return nbr_layer, valid_mask, used


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", default="metropolitana")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--pre-start", default="2025-11-01")
    parser.add_argument("--pre-end", default="2025-11-30")
    parser.add_argument("--post-start", default="2026-02-01")
    parser.add_argument("--post-end", default="2026-02-28")
    parser.add_argument("--max-cloud", type=float, default=30)
    parser.add_argument("--max-items", type=int, default=MAX_ITEMS_PER_WINDOW, help="escenas por ventana; las franjas angostas de menor nubosidad pueden agotar el cupo sin cubrir el recorte")
    args = parser.parse_args()
    import planetary_computer
    import pystac_client
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    crs, transform, shape = manifest_grid(manifest)
    geobox = geobox_from_manifest(manifest)
    catalog = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)

    # SCL is categorical (cloud/water/vegetation codes): averaging it produces fractional values that
    # match no real class. Only B08/B12 (continuous reflectance-like DNs) may be averaged.
    resampling = {"B08": "average", "B12": "average", "SCL": "nearest"}
    nbr_pre, valid_pre, used_pre = composite_nbr(catalog, manifest["bbox_wgs84"], args.pre_start, args.pre_end, geobox, planetary_computer.sign, args.max_cloud, resampling, args.max_items)
    nbr_post, valid_post, used_post = composite_nbr(catalog, manifest["bbox_wgs84"], args.post_start, args.post_end, geobox, planetary_computer.sign, args.max_cloud, resampling, args.max_items)
    if not used_pre or not used_post:
        raise SystemExit("Sin escenas Sentinel-2 con nubes aceptables en alguna de las dos ventanas; ampliar fechas o tolerancia de nubes")
    nbr_pre[~valid_pre] = np.nan
    nbr_post[~valid_post] = np.nan
    delta = dnbr(nbr_pre, nbr_post)
    severity = severity_class(delta)

    out = root / "wildfire"
    write_cog(out / "dnbr.tif", delta, transform, crs, np.nan, "float32", {"source": "Sentinel-2 L2A via Microsoft Planetary Computer, mosaico de varias escenas por ventana", "pre_items": ",".join(u["id"] for u in used_pre), "post_items": ",".join(u["id"] for u in used_post), "formula": "NBR_pre - NBR_post, NBR=(B08-B12)/(B08+B12) sobre reflectancia de superficie (DN - 1000)/10000 desde la versión de procesamiento 04.00"})
    write_cog(out / "severity.tif", severity, transform, crs, NODATA, "uint8", {"classes": "0 sin_quema_o_rebrote,1 baja,2 moderada_baja,3 moderada_alta,4 alta (USGS/UNSPIDER dNBR breaks)", "status": "ventanas de fecha elegidas por el operador; confirmar fecha y perímetro con CONAF"})
    summary = severity_summary(severity)
    manifest_out = {"aoi": args.aoi, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "pre_window": [args.pre_start, args.pre_end], "post_window": [args.post_start, args.post_end], "pre_items_used": used_pre, "post_items_used": used_post, "pre_valid_fraction": float(valid_pre.mean()), "post_valid_fraction": float(valid_post.mean()), "severity_summary": summary, "limits": ["Ventanas de fecha de ejemplo; confirmar fecha y perímetro real del incendio con CONAF/Sernageomin antes de publicar.", "dNBR describe daño a la vegetación observado por óptico, no humedad ni estabilidad del suelo.", "Mosaico de varias escenas por ventana (distintas fechas/orbitas/teselas); cada píxel usa la primera escena sin nubes que lo cubre, no necesariamente la misma fecha en todo el recorte.", "Nubes pueden dejar huecos; revisar severity_summary.n frente al total de píxeles del AOI."]}
    (out / "manifest.json").write_text(json.dumps(manifest_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pre_valid_fraction": manifest_out["pre_valid_fraction"], "post_valid_fraction": manifest_out["post_valid_fraction"], "severity_summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
