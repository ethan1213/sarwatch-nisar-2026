"""Reproducible experimental CO2 + DEM terrain screening; no model training at runtime."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.emissions import co2_emitted
from sarwatch.ml.debris_volume import relative_depth_index, gartner_emergency_volume
from sarwatch.ml.grids import write_cog
from sarwatch.ml.hydrology import coarsen_mean, flow_direction, flow_accumulation, subbasin_labels


def estimate(root, aoi):
    site = Path(root) / aoi
    names = {"severity": "wildfire/severity.tif", "worldcover": "covariates/worldcover.tif",
             "dem": "covariates/dem.tif", "slope": "covariates/slope.tif"}
    arrays, sources, grid = {}, {}, None
    for key, name in names.items():
        path = site / name
        with rasterio.open(path) as src:
            current = (src.shape, src.transform, src.crs)
            if grid is not None and grid != current:
                raise ValueError(f"Grilla incompatible: {path}")
            grid = current
            arrays[key] = src.read(1, masked=True).astype(float).filled(np.nan)
        sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    shape, transform, crs = grid
    if not crs.is_projected or any(unit.lower() not in ("metre", "meter") for unit in (crs.linear_units,)):
        raise ValueError("Se requiere CRS proyectado en metros")
    area = abs(transform.a * transform.e - transform.b * transform.d)
    emissions = co2_emitted(arrays["severity"], arrays["worldcover"], area)
    factor = 5
    dem = coarsen_mean(arrays["dem"], factor)
    slope = coarsen_mean(arrays["slope"], factor)
    severity = arrays["severity"]
    high = np.where(np.isin(severity, [0, 1, 2, 3, 4]), np.isin(severity, [3, 4]).astype(float), np.nan)
    fraction = coarsen_mean(high, factor)
    direction = flow_direction(dem)
    acc = flow_accumulation(dem, direction)
    index = relative_depth_index(acc, slope, fraction)
    coarse_transform = transform * transform.scale(factor, factor)
    output = site / "postfire" / "relative_concentration.tif"
    write_cog(output, index, coarse_transform, crs, np.nan, "float32",
              {"method": "heuristic log accumulation * clipped slope/45 * moderate-high fraction",
               "units": "dimensionless 0-1, NOT metres", "validation": "unvalidated experimental"})
    # Partition into sink-draining catchments, not a claim of surveyed watershed delineation.
    seeds = (direction == -1) & np.isfinite(dem)
    labels = subbasin_labels(direction, seeds)
    rows = []
    for label in np.unique(labels):
        if label == 0:
            continue
        mask = labels == label
        valid = mask & np.isfinite(index)
        if not valid.any():
            continue
        rows.append({"basin_id": int(label), "area_km2": float(mask.sum() * area * factor**2 / 1e6),
                     "burned_moderate_high_km2": float(np.nansum(fraction[mask]) * area * factor**2 / 1e6),
                     "relief_m": float(np.nanmax(dem[mask]) - np.nanmin(dem[mask])),
                     "relative_index_max": float(np.max(index[valid])), "relative_index_mean": float(np.mean(index[valid]))})
    rows.sort(key=lambda row: row["relative_index_max"], reverse=True)
    result = {"aoi": aoi, "generated_utc": datetime.now(timezone.utc).isoformat(),
              "input_sha256": sources, "pixel_area_m2": area, "emissions": emissions,
              "wildfire_provenance": json.loads((site / "wildfire/manifest.json").read_text(encoding="utf-8")),
              "terrain": {"status": "experimental_unvalidated", "operational": False,
                          "raster": str(output.relative_to(Path(root))).replace("\\", "/"),
                          "n_basins": len(rows), "top_basins": rows[:50],
                          "volume": gartner_emergency_volume(None, 0, 0),
                          "limitations": ["Índice relativo 0–1; no profundidad en metros, probabilidad, accesibilidad ni ruta segura.",
                              "DEM remuestreado y reducido; D8 sin relleno de depresiones, cuencas aproximadas.",
                              "No validado contra depósitos medidos; no cumple compuerta de publicación de modelos operativos."]}}
    for destination in (Path("catalog/fire_impacts_reference.json"), Path("docs/fire_impacts_estimate.json")):
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--aoi", default="metropolitana", choices=["metropolitana"])
    args = parser.parse_args()
    result = estimate(args.data_dir, args.aoi)
    print(json.dumps({"aoi": result["aoi"], "co2_t": result["emissions"]["total_co2_t"], "n_basins": result["terrain"]["n_basins"]}))
