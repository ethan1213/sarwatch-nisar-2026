"""Diagnose optical water labels of an AOI against NISAR backscatter and JRC surface-water history.

Answers, per labeled date: where the label puts water (WorldCover, JRC occurrence), how much of JRC
permanent water it recovers, and how dark HH is there. Between consecutive dates: whether pixels that
gain or lose the label change in HH. Optionally compares Sentinel-2 reflectance on two solar days
(--optical-days) to separate surface change from optical artefacts. Writes docs/<aoi>_label_diagnosis.json.
Describes label consistency only; it is not a validation of water extent.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.covariates import PERMANENT_WATER_OCCURRENCE, WORLDCOVER
from sarwatch.ml.grids import geobox_from_manifest, load_manifest, manifest_grid, read_layer
from sarwatch.ml.labels import NODATA

DARK_HH_DB = -18.0
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
BOA_OFFSET_BASELINE = 4.0  # Sentinel-2 processing baseline >= 04.00 stores reflectance DN with +1000


def layer(path):
    return np.asarray(read_layer(path)[0])


def median(values):
    values = values[np.isfinite(values)]
    return float(np.median(values)) if values.size else None


def fraction(mask):
    return float(mask.mean()) if mask.size else None


def optical(manifest, day):
    import odc.stac
    import planetary_computer
    import pystac_client
    catalog = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    items = list(catalog.search(collections=["sentinel-2-l2a"], bbox=manifest["bbox_wgs84"], datetime=day).items())
    if not items:
        raise SystemExit(f"Sin Sentinel-2 para {day}")
    data = odc.stac.load(items, bands=["B03", "B08", "B11", "SCL"], geobox=geobox_from_manifest(manifest), groupby="solar_day", resampling={"B03": "average", "B08": "average", "B11": "average", "SCL": "nearest"}, patch_url=planetary_computer.sign, chunks=None).isel(time=0)
    offset = 1000 if float(items[0].properties.get("s2:processing_baseline", "0")) >= BOA_OFFSET_BASELINE else 0
    bands = {name: (data[band].values.astype("float32") - offset) / 10000 for name, band in (("green", "B03"), ("nir", "B08"), ("swir1", "B11"))}
    return {**bands, "scl": data["SCL"].values, "items": [i.id for i in items], "boa_offset_dn": offset}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--optical-days", nargs=2, metavar=("DAY_A", "DAY_B"), help="Dos dias solares Sentinel-2 (AAAA-MM-DD) usados por las etiquetas de --optical-labels")
    parser.add_argument("--optical-labels", nargs=2, metavar=("DATE_A", "DATE_B"), help="Fechas NISAR cuyas etiquetas se comparan con --optical-days")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    _, transform, shape = manifest_grid(manifest)
    km2 = lambda mask: float(mask.sum()) * abs(transform.a) ** 2 / 1e6
    labels_manifest = json.loads((root / "labels" / "manifest.json").read_text(encoding="utf-8"))
    ok = {e["scene_id"]: e for e in labels_manifest["labels"] if e.get("status") == "ok"}
    scenes = {s["fecha_observacion"][:10]: s for s in manifest["scenes"] if s["id"] in ok}
    worldcover = layer(root / "covariates" / "worldcover.tif").astype(np.int32)
    occurrence = np.nan_to_num(layer(root / "covariates" / "jrc_occurrence.tif"), nan=0.0)
    permanent = occurrence >= PERMANENT_WATER_OCCURRENCE
    dates = sorted(scenes)
    label = {d: layer(root / "labels" / ok[scenes[d]["id"]]["label"]) for d in dates}
    hh = {d: layer(root / scenes[d]["products"]["HH"]) for d in dates}
    result = {"aoi": args.aoi, "generated_utc": datetime.now(timezone.utc).isoformat(), "label_rule": labels_manifest["rule"], "dark_hh_db": DARK_HH_DB, "aoi_km2": km2(np.ones(shape, bool)), "jrc_km2": {"permanent": km2(permanent), "ever_water": km2(occurrence >= 1)}, "dates": [], "transitions": []}
    for d in dates:
        water, not_water, seen = label[d] == 1, label[d] == 0, label[d] != NODATA
        result["dates"].append({
            "date": d,
            "sentinel2_days": [o["solar_day"] for o in ok[scenes[d]["id"]]["observations"]],
            "label_water_km2": km2(water),
            "label_water_by_worldcover_km2": {WORLDCOVER.get(c, str(c)): km2(water & (worldcover == c)) for c in np.unique(worldcover[water])},
            "label_water_outside_jrc_ever_water_km2": km2(water & (occurrence < 1)),
            "jrc_permanent_labeled_water_fraction": fraction(label[d][permanent & seen] == 1),
            "hh_median_db": {"label_water": median(hh[d][water]), "label_not_water": median(hh[d][not_water][::50]), "jrc_permanent": median(hh[d][permanent])},
            "label_water_dark_hh_fraction": fraction(hh[d][water] < DARK_HH_DB),
            "dark_hh_km2": km2(hh[d] < DARK_HH_DB),
        })
    for a, b in zip(dates[:-1], dates[1:]):
        both = (label[a] != NODATA) & (label[b] != NODATA)
        sets = {"lost": (label[a] == 1) & (label[b] == 0) & both, "gained": (label[a] == 0) & (label[b] == 1) & both, "kept": (label[a] == 1) & (label[b] == 1) & both}
        union = km2((label[a] == 1) | (label[b] == 1))
        result["transitions"].append({"from": a, "to": b, "label_iou": km2(sets["kept"]) / union if union else None, **{name: {"km2": km2(sel), "hh_median_db_from": median(hh[a][sel]), "hh_median_db_to": median(hh[b][sel])} for name, sel in sets.items()}})
    always_dark = np.all(np.stack([hh[d] < DARK_HH_DB for d in dates]), axis=0)
    times_water = np.sum(np.stack([label[d] == 1 for d in dates]), axis=0)
    result["persistence"] = {"n_dates": len(dates), "always_dark_hh_km2": km2(always_dark), "always_dark_never_labeled_water_km2": km2(always_dark & (times_water == 0)), "labeled_water_every_date_km2": km2(times_water == len(dates)), "labeled_water_once_km2": km2(times_water == 1)}
    if args.optical_days and args.optical_labels:
        la, lb = label[args.optical_labels[0]], label[args.optical_labels[1]]
        sets = {"label_lost": (la == 1) & (lb == 0), "label_kept": (la == 1) & (lb == 1), "jrc_permanent": permanent, "never_labeled_sample": (la == 0) & (lb == 0) & (np.random.default_rng(0).random(shape) < 0.02)}
        comparison = {"labels": args.optical_labels, "days": args.optical_days, "sets": {name: {"km2": km2(sel)} for name, sel in sets.items()}}
        for day in args.optical_days:
            obs = optical(manifest, day)
            comparison.setdefault("items", {})[day] = obs["items"]
            comparison.setdefault("boa_offset_dn", {})[day] = obs["boa_offset_dn"]
            for name, sel in sets.items():
                green, nir, swir = obs["green"][sel], obs["nir"][sel], obs["swir1"][sel]
                scl, counts = np.unique(obs["scl"][sel], return_counts=True)
                comparison["sets"][name][day] = {"green_median": median(green), "nir_median": median(nir), "swir1_median": median(swir), "green_gt_swir1_fraction": fraction(green > swir), "nir_lt_green_fraction": fraction(nir < green), "scl_fractions": {str(int(k)): float(v / counts.sum()) for k, v in zip(scl, counts)}}
        result["optical_comparison"] = comparison
    output = Path(args.output or f"docs/{args.aoi}_label_diagnosis.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("->", output)


if __name__ == "__main__":
    main()
