"""Static covariates on the NISAR grid: DEM, slope, HAND proxy, JRC water history, WorldCover.

Writes data/<aoi>/covariates/*.tif and covariates/manifest.json. No credentials required.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.covariates import PERMANENT_WATER_OCCURRENCE, WORLDCOVER, hand_proxy, permanent_water_mask
from sarwatch.ml.features import slope_degrees
from sarwatch.ml.grids import geobox_from_manifest, load_manifest, manifest_grid, write_cog

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def load_band(catalog, collection, band, manifest, sign, resampling, pick=None):
    """Load one band of a collection onto the AOI geobox; merge several items by nan-aware reduction."""
    import odc.stac
    items = list(catalog.search(collections=[collection], bbox=manifest["bbox_wgs84"]).items())
    if pick:
        items = [i for i in items if pick(i)]
    if not items:
        raise ValueError(f"Sin items de {collection} para el AOI")
    data = odc.stac.load(items, bands=[band], geobox=geobox_from_manifest(manifest), groupby="solar_day", resampling=resampling, patch_url=sign, chunks=None)
    array = data[band]
    nodata = array.attrs.get("nodata")
    stack = array.values.astype("float64") if "time" in array.dims else array.values[None].astype("float64")
    if nodata is not None and np.isfinite(nodata):
        stack[stack == nodata] = np.nan
    with np.errstate(all="ignore"):
        merged = np.nanmax(stack, axis=0) if resampling == "nearest" else np.nanmean(stack, axis=0)
    return merged, [i.id for i in items]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", required=True)
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()
    import planetary_computer
    import pystac_client
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    crs, transform, _ = manifest_grid(manifest)
    resolution = abs(transform.a)
    catalog = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    sign = planetary_computer.sign
    out = root / "covariates"
    sources = {}

    dem, ids = load_band(catalog, "cop-dem-glo-30", "data", manifest, sign, "bilinear")
    dem = dem.astype("float32")
    sources["dem"] = {"collection": "cop-dem-glo-30", "items": ids, "resampling": "bilinear 30 m -> grilla NISAR"}
    write_cog(out / "dem.tif", dem, transform, crs, np.nan, "float32", {"source": "Copernicus DEM GLO-30", "unit": "m"})
    write_cog(out / "slope.tif", slope_degrees(dem, resolution), transform, crs, np.nan, "float32", {"source": "derivada de dem.tif (Horn)", "unit": "grados"})

    occurrence, ids = load_band(catalog, "jrc-gsw", "occurrence", manifest, sign, "nearest")
    occurrence = occurrence.astype("float32")
    occurrence[(occurrence > 100) | (occurrence < 0)] = np.nan
    sources["jrc_occurrence"] = {"collection": "jrc-gsw", "items": ids}
    write_cog(out / "jrc_occurrence.tif", occurrence, transform, crs, np.nan, "float32", {"source": "JRC Global Surface Water v1.4 (1984-2021)", "unit": "porcentaje de observaciones con agua"})
    seasonality, _ = load_band(catalog, "jrc-gsw", "seasonality", manifest, sign, "nearest")
    write_cog(out / "jrc_seasonality.tif", np.nan_to_num(seasonality, nan=255).astype("uint8"), transform, crs, 255, "uint8", {"source": "JRC GSW seasonality", "unit": "meses con agua en el ultimo ano de referencia"})

    permanent = permanent_water_mask(occurrence)
    height, distance = hand_proxy(dem, permanent, resolution)
    write_cog(out / "hand_proxy.tif", height, transform, crs, np.nan, "float32", {"source": f"dem.tif menos DEM del pixel de agua permanente mas cercano (JRC occurrence >= {PERMANENT_WATER_OCCURRENCE})", "unit": "m", "note": "proxy de HAND sin red de drenaje enrutada"})
    write_cog(out / "dist_water.tif", distance, transform, crs, np.nan, "float32", {"source": "distancia euclidea al agua permanente JRC", "unit": "m"})

    worldcover, ids = load_band(catalog, "esa-worldcover", "map", manifest, sign, "nearest", pick=lambda i: "2021_v200" in i.id)
    worldcover = np.nan_to_num(worldcover, nan=0).astype("uint8")
    sources["worldcover"] = {"collection": "esa-worldcover", "items": ids, "classes": WORLDCOVER}
    write_cog(out / "worldcover.tif", worldcover, transform, crs, 0, "uint8", {"source": "ESA WorldCover 10 m 2021 v200", "classes": json.dumps(WORLDCOVER, ensure_ascii=False)})

    values, counts = np.unique(worldcover, return_counts=True)
    fractions = {WORLDCOVER.get(int(v), str(int(v))): float(c / worldcover.size) for v, c in zip(values, counts)}
    summary = {"aoi": args.aoi, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "stac": STAC, "resolution_m": resolution, "sources": sources, "permanent_water_fraction": float(permanent.mean()), "worldcover_fractions": fractions, "limits": ["HAND es un proxy basado en agua permanente observada, no en drenaje enrutado.", "DEM de 30 m remuestreado a 20 m: la pendiente local está suavizada.", "WorldCover 2021 es anterior a las observaciones NISAR de 2026."]}
    (out / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("aoi", "permanent_water_fraction", "worldcover_fractions")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
