"""Does NISAR backscatter differ between burned and unburned forest after a fire? Per radar date.

Label: Sentinel-2 dNBR severity (scripts/fetch_fire_dnbr.py) on the NISAR grid. Population: WorldCover tree
cover, so that the comparison is forest against forest. Per date: median HV, HH and HH - HV per severity
class, and the AUC with which each quantity separates high severity from unburned forest, on all pixels and
per spatial fold of blocks (the spread across folds shows whether the separation holds everywhere).

This is a cross-section after the fire, without a pre-fire radar pass: stands that burned may already have
differed before. It describes a radar difference that is consistent with a burn scar; it does not prove it.

    python scripts/evaluate_burn_scar.py --aoi concepcion_penco
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.fire import rank_auc
from sarwatch.ml.grids import load_manifest, manifest_grid, read_layer
from sarwatch.ml.wildfire import CLASSES, NODATA

TREES, BLOCK_PIXELS, FOLDS, MAX_SAMPLE, MIN_PIXELS = 10, 128, 5, 200_000, 1000


def separation(value, high, unburned, rng):
    """AUC of 'lower value = burned' on a balanced-size random sample; None with too few pixels."""
    a, b = value[high], value[unburned]
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if a.size < MIN_PIXELS or b.size < MIN_PIXELS:
        return None
    a = rng.choice(a, MAX_SAMPLE, replace=False) if a.size > MAX_SAMPLE else a
    b = rng.choice(b, MAX_SAMPLE, replace=False) if b.size > MAX_SAMPLE else b
    return rank_auc(np.r_[-a, -b], np.r_[np.ones(a.size, bool), np.zeros(b.size, bool)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="docs/burn_scar_benchmark.json")
    args = parser.parse_args()
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    _, transform, shape = manifest_grid(manifest)
    severity, severity_transform, _ = read_layer(root / "wildfire" / "severity.tif")
    cover, cover_transform, _ = read_layer(root / "covariates" / "worldcover.tif")
    if severity.shape != tuple(shape) or severity_transform != transform or cover.shape != tuple(shape) or cover_transform != transform:
        raise SystemExit("Severidad, cobertura y SAR en grillas distintas")
    severity, trees = np.asarray(severity), np.asarray(cover) == TREES
    rows, cols = np.indices(shape)
    fold = ((rows // BLOCK_PIXELS) * 7919 + cols // BLOCK_PIXELS) % FOLDS  # every block falls in one fold
    area_km2 = abs(transform.a * transform.e) / 1e6
    high, unburned = trees & (severity == 4), trees & (severity == 0)
    rng = np.random.default_rng(0)
    dates = []
    for scene in manifest["scenes"]:
        hh, hh_transform, _ = read_layer(root / scene["products"]["HH"])
        hv, _, _ = read_layer(root / scene["products"]["HV"])
        if hh.shape != tuple(shape) or hh_transform != transform:
            raise SystemExit(f"Escena {scene['id']} fuera de la grilla del manifiesto")
        layers = {"hv_db": hv, "hh_db": hh, "hh_menos_hv_db": hh - hv}
        entry = {"date": scene["fecha_observacion"][:10], "valid_fraction_hv": scene["finite_positive_fraction"]["HV"], "median_by_class": {}, "separation_high_vs_unburned": {}}
        for code, name in CLASSES.items():
            mask = trees & (severity == code)
            entry["median_by_class"][name] = {"pixels_with_radar": int(np.isfinite(hv[mask]).sum()), **{k: (round(float(np.nanmedian(v[mask])), 3) if np.isfinite(v[mask]).any() else None) for k, v in layers.items()}}
        for key, value in layers.items():
            signed = -value if key == "hh_menos_hv_db" else value  # burned forest: lower HV, higher HH - HV
            per_fold = [separation(signed, high & (fold == f), unburned & (fold == f), rng) for f in range(FOLDS)]
            per_fold = [round(x, 3) for x in per_fold if x is not None]
            overall = separation(signed, high, unburned, rng)
            entry["separation_high_vs_unburned"][key] = {"auc": None if overall is None else round(overall, 3), "auc_by_spatial_fold": per_fold, "direction": "mayor en quemado" if key == "hh_menos_hv_db" else "menor en quemado"}
        dates.append(entry)
        print(entry["date"], {k: v["auc"] for k, v in entry["separation_high_vs_unburned"].items()}, flush=True)
    fire = json.loads((root / "wildfire" / "manifest.json").read_text(encoding="utf-8"))
    land = (np.asarray(cover) != 80) & (np.asarray(cover) != 0)
    result = {"generated_utc": datetime.now(timezone.utc).isoformat(), "aoi": args.aoi, "method": __doc__.strip().split("\n\n")[0],
              "label": {"source": "dNBR Sentinel-2 L2A (Planetary Computer)", "pre_window": fire["pre_window"], "post_window": fire["post_window"], "pre_valid_fraction": fire["pre_valid_fraction"], "post_valid_fraction": fire["post_valid_fraction"]},
              "area_km2": {"land_by_class": {name: round(float(((severity == code) & land).sum() * area_km2), 1) for code, name in CLASSES.items()}, "forest_by_class": {name: round(float(((severity == code) & trees).sum() * area_km2), 1) for code, name in CLASSES.items()}},
              "parameters": {"population": "WorldCover 2021 clase 10 (árboles)", "block_pixels": BLOCK_PIXELS, "spatial_folds": FOLDS, "max_sample_per_class": MAX_SAMPLE, "min_pixels": MIN_PIXELS},
              "dates": dates,
              "limits": ["Corte transversal posterior al incendio: no hay pasada NISAR previa de la misma geometría, así que no mide cambio.", "Los rodales quemados pudieron diferir antes del fuego (edad, especie, manejo).", "dNBR también responde a cosecha, sequía estival y cambios de uso entre las dos ventanas ópticas.", "WorldCover es de 2021: una plantación cosechada después sigue contando como árboles.", "No es área quemada oficial; confirmar perímetro con CONAF."]}
    out = Path(args.output)
    existing = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {"aois": {}}
    existing["aois"][args.aoi] = result
    out.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
