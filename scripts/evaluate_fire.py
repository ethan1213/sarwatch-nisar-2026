"""Cross GOES hot spots with NISAR backscatter, terrain and land cover per thermal cell; evaluate honestly.

For each AOI with data/<aoi>/thermal (scripts/fetch_thermal.py) this script:
1. assigns every NISAR pixel to its GOES cell (zones.tif) and aggregates HH/HV, DEM, slope and WorldCover per cell;
2. tests whether backscatter changes more in cells where GOES saw heat between two NISAR passes (response);
3. benchmarks the anticipation of hot cells in the 12 days after a NISAR pass from (a) fire history alone,
   (b) recent thermal state, (c) radar + terrain + land cover, (d) everything, on held-out spatial blocks
   and on held-out dates.
Writes data/<aoi>/thermal/{zones.tif,zones.json}, docs/fire_benchmark.json and catalog/thermal_reference.json.
No model is published by this script: it only reports whether one would be justified.
"""
import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.covariates import WORLDCOVER
from sarwatch.ml.fire import neighbour_fraction, rank_auc, window_any, zonal_fraction, zonal_mean, zonal_mean_db, zone_raster
from sarwatch.ml.grids import load_manifest, manifest_grid, read_layer, write_cog
from sarwatch.ml.thermal import CLOUD_CODES, CONFIDENT_FIRE, fire_class

HORIZON_DAYS = 12          # NISAR repeat cycle: the question is "before the next pass"
MIN_SAR_FRACTION = 0.5     # a cell needs half of its pixels with valid backscatter
MAX_WATER_FRACTION = 0.5   # cells dominated by permanent water are not candidates
BLOCK_CELLS = 4            # spatial blocks of 4 x 4 thermal cells (about 9 km)
MIN_POSITIVES = 10         # below this, no score is reported
DAY_HOURS_UTC = (15, 16, 17, 18, 19)  # early afternoon local time in both regions
COVER_GROUPS = {"arboles": (10,), "matorral": (20,), "pastizal": (30,), "cultivo": (40,), "urbano": (50,), "suelo_desnudo": (60,), "agua": (80,), "humedal": (90, 95)}
FEATURE_SETS = {
    "historial": ["calor_previo", "vecinos_previos"],
    "termico": ["calor_previo", "vecinos_previos", "lst_dia_k", "mir_menos_ir_max_k", "fraccion_despejada"],
    "radar_terreno": ["hv_db", "hh_db", "hh_menos_hv_db", "hv_cambio_db", "elevacion_m", "pendiente_grados"] + [f"cob_{k}" for k in COVER_GROUPS],
}
FEATURE_SETS["todo"] = FEATURE_SETS["termico"] + FEATURE_SETS["radar_terreno"]


def cell_table(root, manifest, thermal, cube):
    """Static and per-date radar aggregates of every thermal cell, plus the zone raster on the NISAR grid."""
    from pyproj import Transformer
    crs, transform, shape = manifest_grid(manifest)
    cols, rows = np.meshgrid(np.arange(shape[1]) + 0.5, np.arange(shape[0]) + 0.5)
    lon, lat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(transform.c + cols * transform.a, transform.f + rows * transform.e)
    navigation = thermal["navigation"]
    zones = zone_raster(lat, lon, thermal["window_rows_cols"], navigation["x"], navigation["y"], navigation["projection"])
    n = int(cube["lat"].size)
    table = {"n_pixels": np.bincount(zones[zones >= 0], minlength=n)}
    dem, dem_transform, _ = read_layer(root / "covariates" / "dem.tif")
    if dem.shape != tuple(shape) or dem_transform != transform:
        raise ValueError("Covariables y SAR en grillas distintas")
    slope, _, _ = read_layer(root / "covariates" / "slope.tif")
    cover, _, _ = read_layer(root / "covariates" / "worldcover.tif")
    cover = np.asarray(cover).astype(np.int32)
    table["elevacion_m"], _ = zonal_mean(dem, zones, n)
    table["pendiente_grados"], _ = zonal_mean(slope, zones, n)
    known = np.isin(cover, list(WORLDCOVER))
    for name, codes in COVER_GROUPS.items():
        table[f"cob_{name}"] = zonal_fraction(np.isin(cover, codes), known, zones, n)
    radar = []
    for scene in manifest["scenes"]:
        hh, hh_transform, _ = read_layer(root / scene["products"]["HH"])
        hv, _, _ = read_layer(root / scene["products"]["HV"])
        if hh.shape != tuple(shape) or hh_transform != transform:
            raise ValueError(f"Escena {scene['id']} fuera de la grilla del manifiesto")
        hh_db, fraction = zonal_mean_db(hh, zones, n)
        hv_db, _ = zonal_mean_db(hv, zones, n)
        radar.append({"utc": scene["fecha_observacion"], "hh_db": hh_db, "hv_db": hv_db, "fraccion_valida": fraction})
    return zones, table, radar, (crs, transform)


def thermal_state(cube, times, start, end):
    """Recent thermal state per cell in (start, end]: daytime LST median, max MIR - TIR, clear-sky fraction."""
    keep = (times > np.datetime64(start, "m")) & (times <= np.datetime64(end, "m"))
    hours = times.astype("datetime64[h]").astype(int) % 24
    day = keep & np.isin(hours, DAY_HOURS_UTC)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells (cloud, no retrieval) stay NaN
        lst = np.nanmedian(cube["lst"][day], axis=0) if day.any() else np.full(cube["lat"].shape, np.nan)
        difference = cube["bt_mir"][keep] - cube["bt_tir"][keep]
        difference[np.isin(cube["mask"][keep], CLOUD_CODES)] = np.nan
        spread = np.nanmax(difference, axis=0) if keep.any() else np.full(cube["lat"].shape, np.nan)
    processed = (cube["mask"][keep] >= 0).sum(axis=0)
    clear = 1 - np.isin(cube["mask"][keep], CLOUD_CODES).sum(axis=0) / np.maximum(processed, 1)
    return lst, spread, clear


def samples(table, radar, cube, times, hot):
    """One row per (cell, NISAR pass): features known at the pass, label = confident hot spot in the next 12 days."""
    shape = cube["lat"].shape
    n = cube["lat"].size
    cell_rows, cell_cols = np.divmod(np.arange(n), shape[1])
    block = (cell_rows // BLOCK_CELLS) * int(np.ceil(shape[1] / BLOCK_CELLS)) + cell_cols // BLOCK_CELLS
    rows, last = [], times[-1]
    for index, scene in enumerate(radar):
        when = np.datetime64(scene["utc"][:16], "m")
        horizon = when + np.timedelta64(HORIZON_DAYS, "D")
        if horizon > last or when - np.timedelta64(HORIZON_DAYS, "D") < times[0]:
            continue
        usable = (scene["fraccion_valida"] >= MIN_SAR_FRACTION) & ~(table["cob_agua"] > MAX_WATER_FRACTION) & (table["n_pixels"] > 0)
        if not usable.any():
            continue
        previous = window_any(hot, times, when - np.timedelta64(HORIZON_DAYS, "D"), when)
        lst, spread, clear = thermal_state(cube, times, when - np.timedelta64(HORIZON_DAYS, "D"), when)
        earlier = next((radar[j] for j in range(index - 1, -1, -1) if (radar[j]["fraccion_valida"] >= MIN_SAR_FRACTION).mean() > 0.5), None)
        change = scene["hv_db"] - earlier["hv_db"] if earlier else np.full(n, np.nan)
        features = {"calor_previo": previous.ravel().astype(float), "vecinos_previos": neighbour_fraction(previous).ravel(), "lst_dia_k": lst.ravel(), "mir_menos_ir_max_k": spread.ravel(), "fraccion_despejada": clear.ravel(), "hv_db": scene["hv_db"], "hh_db": scene["hh_db"], "hh_menos_hv_db": scene["hh_db"] - scene["hv_db"], "hv_cambio_db": change, "elevacion_m": table["elevacion_m"], "pendiente_grados": table["pendiente_grados"], **{k: v for k, v in table.items() if k.startswith("cob_")}}
        label = window_any(hot, times, when, horizon).ravel()
        rows.append({"date": scene["utc"][:10], "cells": np.flatnonzero(usable), "block": block[usable], "label": label[usable], "features": {k: np.asarray(v, dtype=np.float64)[usable] for k, v in features.items()}})
    return rows


def response(radar, table, times, hot, any_heat):
    """Did backscatter change differently in cells with confident heat between consecutive usable passes?"""
    usable_scene = [s for s in radar if (s["fraccion_valida"] >= MIN_SAR_FRACTION).mean() > 0.5]
    pairs, pooled = [], {"hv": ([], []), "hh": ([], [])}
    for before, after in zip(usable_scene, usable_scene[1:]):
        start, end = before["utc"][:16], after["utc"][:16]
        burned = window_any(hot, times, start, end).ravel()
        touched = window_any(any_heat, times, start, end).ravel()
        usable = (before["fraccion_valida"] >= MIN_SAR_FRACTION) & (after["fraccion_valida"] >= MIN_SAR_FRACTION) & ~(table["cob_agua"] > MAX_WATER_FRACTION)
        entry = {"before": start[:10], "after": end[:10], "cells_with_heat": int((burned & usable).sum()), "cells_without_heat": int((~touched & usable).sum())}
        for band in ("hv", "hh"):
            delta = after[f"{band}_db"] - before[f"{band}_db"]
            with_heat, without = delta[burned & usable], delta[~touched & usable]
            pooled[band][0].append(with_heat)
            pooled[band][1].append(without)
            if with_heat.size >= MIN_POSITIVES:
                entry[band] = summary(with_heat, without)
        pairs.append(entry)
    total = {band: summary(np.concatenate(pooled[band][0]), np.concatenate(pooled[band][1])) for band in pooled if pooled[band][0] and np.concatenate(pooled[band][0]).size >= MIN_POSITIVES}
    return {"pairs": pairs, "pooled": total, "definition": "Celda con calor: al menos un foco GOES de clase procesado, saturado o probabilidad alta entre las dos pasadas. Celda sin calor: ningún foco de ninguna clase. Cambio = dB después menos dB antes, promedio zonal en potencia."}


def summary(with_heat, without):
    with_heat, without = with_heat[np.isfinite(with_heat)], without[np.isfinite(without)]
    auc = rank_auc(np.r_[-with_heat, -without], np.r_[np.ones(with_heat.size, bool), np.zeros(without.size, bool)])
    return {"n_with_heat": int(with_heat.size), "n_without_heat": int(without.size), "median_change_with_heat_db": float(np.median(with_heat)), "median_change_without_heat_db": float(np.median(without)), "auc_decrease_separates_heat": auc, "auc_bootstrap_90": bootstrap_auc(-with_heat, -without)}


def bootstrap_auc(positive, negative, repeats=300, seed=0):
    rng = np.random.default_rng(seed)
    values = [rank_auc(np.r_[rng.choice(positive, positive.size), rng.choice(negative, negative.size)], np.r_[np.ones(positive.size, bool), np.zeros(negative.size, bool)]) for _ in range(repeats)]
    return [float(np.quantile(values, 0.05)), float(np.quantile(values, 0.95))]


def fit_predict(train_X, train_y, test_X):
    import lightgbm
    model = lightgbm.LGBMClassifier(n_estimators=150, learning_rate=0.05, num_leaves=7, min_child_samples=15, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0, is_unbalance=True, random_state=0, verbose=-1, n_jobs=2)
    model.fit(train_X, train_y)
    return model.predict_proba(test_X)[:, 1]


def score(label, probability):
    from sklearn.metrics import average_precision_score
    label = np.asarray(label, dtype=bool)
    if label.sum() < MIN_POSITIVES or (~label).sum() < MIN_POSITIVES:
        return {"n": int(label.size), "positives": int(label.sum()), "note": f"menos de {MIN_POSITIVES} positivos o negativos: sin métrica"}
    return {"n": int(label.size), "positives": int(label.sum()), "prevalence": float(label.mean()), "roc_auc": rank_auc(probability, label), "average_precision": float(average_precision_score(label, probability))}


def anticipation(rows):
    """Held-out spatial blocks (5 folds, all dates) and held-out dates (last third of the passes)."""
    if not rows:
        return {"note": "sin pasadas NISAR con ventana térmica completa antes y después"}
    label = np.concatenate([r["label"] for r in rows])
    block = np.concatenate([r["block"] for r in rows])
    date = np.concatenate([np.full(r["label"].size, r["date"]) for r in rows])
    result = {"horizon_days": HORIZON_DAYS, "passes": [{"date": r["date"], "cells": int(r["label"].size), "hot_next": int(r["label"].sum())} for r in rows], "samples": int(label.size), "positives": int(label.sum())}
    if label.sum() < 2 * MIN_POSITIVES:
        result["note"] = f"menos de {2 * MIN_POSITIVES} celdas con calor posterior: no se entrena ni se puntúa"
        return result
    dates = sorted(set(date.tolist()))
    n_test = max(1, len(dates) // 3)
    test_dates = dates[-n_test:]
    temporal_test = np.isin(date, test_dates)
    # A training label is only known HORIZON_DAYS after its pass: drop passes whose window overlaps the first test pass.
    cutoff = np.datetime64(test_dates[0]) - np.timedelta64(HORIZON_DAYS, "D")
    temporal_train = np.array([np.datetime64(d) <= cutoff for d in date])
    blocks = np.unique(block)
    fold_of = dict(zip(blocks.tolist(), (np.random.default_rng(0).permutation(blocks.size) % 5).tolist()))
    fold = np.array([fold_of[b] for b in block.tolist()])
    result["split"] = {"spatial": f"5 pliegues de bloques de {BLOCK_CELLS}x{BLOCK_CELLS} celdas térmicas; el bloque retenido lo está en todas las fechas", "temporal": {"train_until": str(cutoff), "test_dates": test_dates}}
    result["models"] = {}
    for name, columns in FEATURE_SETS.items():
        X = np.column_stack([np.concatenate([r["features"][c] for r in rows]) for c in columns])
        spatial = np.full(label.size, np.nan)
        for k in range(5):
            train, test = fold != k, fold == k
            if label[train].sum() >= MIN_POSITIVES and test.any():
                spatial[test] = fit_predict(X[train], label[train], X[test])
        entry = {"features": columns, "spatial_blocks": score(label[np.isfinite(spatial)], spatial[np.isfinite(spatial)])}
        if temporal_train.any() and label[temporal_train].sum() >= MIN_POSITIVES:
            entry["held_out_dates"] = score(label[temporal_test], fit_predict(X[temporal_train], label[temporal_train], X[temporal_test]))
        else:
            entry["held_out_dates"] = {"note": "sin positivos suficientes antes de las fechas retenidas"}
        result["models"][name] = entry
    previous = np.concatenate([r["features"]["calor_previo"] + 0.5 * r["features"]["vecinos_previos"] for r in rows])
    result["models"]["persistencia"] = {"features": ["calor_previo + 0,5 · vecinos_previos, sin entrenamiento"], "spatial_blocks": score(label, previous), "held_out_dates": score(label[temporal_test], previous[temporal_test])}
    return result


def evaluate(aoi, root):
    thermal = json.loads((root / "thermal" / "manifest.json").read_text(encoding="utf-8"))
    cube = dict(np.load(root / "thermal" / "cube.npz"))
    times = cube["times"].astype("U16").astype("datetime64[m]")
    manifest = load_manifest(root)
    zones, table, radar, (crs, transform) = cell_table(root, manifest, thermal, cube)
    write_cog(root / "thermal" / "zones.tif", zones, transform, crs, -1, "int32", {"source": "celda GOES-19 ABI que contiene cada píxel NISAR", "index": "fila * columnas + columna de thermal/cube.npz"})
    classes = fire_class(cube["mask"])
    hot, any_heat = np.isin(classes, CONFIDENT_FIRE), classes > 0
    covered = table["n_pixels"] > 0
    result = {
        "aoi": aoi, "thermal_period_utc": thermal["period_utc"], "step_minutes": thermal["step_minutes"], "cells": int(cube["lat"].size), "cells_with_sar": int(covered.sum()),
        "cell_km": [thermal["pixel_km_east_west"], thermal["pixel_km_north_south"]], "sar_dates": [s["utc"][:10] for s in radar],
        "hotspots": {"detections": int(any_heat.sum()), "confident_detections": int(hot.sum()), "days_with_hotspots": thermal["days_with_hotspots"], "cells_ever_hot": int(any_heat.any(axis=0).sum()), "cells_ever_confident": int(hot.any(axis=0).sum()), "cells_ever_confident_with_sar": int((hot.any(axis=0).ravel() & covered).sum()), "by_class": thermal["hotspot_detections_by_class"]},
        "cloud_fraction": thermal["cloud_fraction_of_processed"],
        "response": response(radar, table, times, hot, any_heat),
        "anticipation": anticipation(samples(table, radar, cube, times, hot)),
    }
    rounded = lambda values, digits=2: [None if not np.isfinite(v) else round(float(v), digits) for v in values]
    zones_json = {"aoi": aoi, "generated_utc": datetime.now(timezone.utc).isoformat(), "grid_shape": list(cube["lat"].shape), "sar_dates": result["sar_dates"], "n_pixels": table["n_pixels"].tolist(),
                  "static": {k: rounded(v, 3 if k.startswith("cob_") else 1) for k, v in table.items() if k != "n_pixels"},
                  "radar": [{"date": s["utc"][:10], "hv_db": rounded(s["hv_db"]), "hh_db": rounded(s["hh_db"]), "fraccion_valida": rounded(s["fraccion_valida"], 3)} for s in radar]}
    (root / "thermal" / "zones.json").write_text(json.dumps(zones_json, ensure_ascii=False), encoding="utf-8")
    return result


def viewer_reference(benchmark):
    """Compact figures the viewer and the assistant may quote."""
    out = {"generated_utc": benchmark["generated_utc"], "source": "docs/fire_benchmark.json", "aois": {}}
    for aoi, block in benchmark["aois"].items():
        entry = {"period_utc": block["thermal_period_utc"], "step_minutes": block["step_minutes"], "cell_km": block["cell_km"], "hotspots": block["hotspots"], "cloud_fraction": block["cloud_fraction"]}
        pooled = block["response"]["pooled"]
        entry["response"] = {band: {k: pooled[band][k] for k in ("n_with_heat", "n_without_heat", "median_change_with_heat_db", "median_change_without_heat_db", "auc_decrease_separates_heat", "auc_bootstrap_90")} for band in pooled} or None
        models = block["anticipation"].get("models")
        entry["anticipation"] = {name: {split: {k: m[split].get(k) for k in ("roc_auc", "average_precision", "prevalence", "positives", "n", "note") if k in m[split]} for split in ("spatial_blocks", "held_out_dates")} for name, m in models.items()} if models else {"note": block["anticipation"].get("note")}
        out["aois"][aoi] = entry
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", nargs="+", required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--benchmark", default="docs/fire_benchmark.json")
    parser.add_argument("--reference", default="catalog/thermal_reference.json")
    args = parser.parse_args()
    benchmark = {"generated_utc": datetime.now(timezone.utc).isoformat(), "method": __doc__.strip().split("\n\n")[0], "parameters": {"horizon_days": HORIZON_DAYS, "min_sar_fraction": MIN_SAR_FRACTION, "max_water_fraction": MAX_WATER_FRACTION, "block_cells": BLOCK_CELLS, "min_positives": MIN_POSITIVES, "confident_classes": list(CONFIDENT_FIRE)}, "aois": {}}
    for aoi in args.aoi:
        root = Path(args.data_dir) if aoi == "pantanal" else Path(args.data_dir) / aoi
        benchmark["aois"][aoi] = evaluate(aoi, root)
        print(aoi, json.dumps(benchmark["aois"][aoi]["hotspots"], ensure_ascii=False))
    Path(args.benchmark).write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.reference).write_text(json.dumps(viewer_reference(benchmark), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
