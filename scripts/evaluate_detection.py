"""Evaluate observed-change detectors on held-out spatial blocks and dates; write masks, cards and a benchmark.

Pantanal (labels available): Otsu / Kittler-Illingworth water thresholds and a LightGBM pixel classifier
are scored against Sentinel-2 MNDWI labels on held-out spatial blocks and on a held-out date.
Chile (no change labels): Conradsen diagonal test and MAD log-ratio masks are produced and compared
with each other; no accuracy is claimed.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.change import NODATA as CHANGE_NODATA, change_fractions, change_mask_from_delta, change_mask_from_pvalue, conradsen_diagonal_test, enl_estimate, log_ratio_db, mad_threshold
from sarwatch.ml.covariates import WORLDCOVER
from sarwatch.ml.experiments import record
from sarwatch.ml.grids import load_manifest, manifest_grid, read_layer, write_cog
from sarwatch.ml.labels import NODATA as LABEL_NODATA
from sarwatch.ml.metrics import binary_scores, scores_by_group
from sarwatch.ml.pixel_classifier import feature_importance, features_matrix, load_covariates, predict_proba, scene_features, subsample_balanced, train_lightgbm, write_model_card
from sarwatch.ml.splits import assert_blocks_not_shared, block_ids, spatial_block_split
from sarwatch.ml.water import area_km2, kittler_illingworth_threshold, otsu_threshold, water_mask

MAX_HAND_M = 20.0
MAX_SLOPE_DEG = 10.0
BLOCK = 64
TEST_FRACTION = 0.25
BUFFER_BLOCKS = 1
MAX_PER_CLASS_PER_DATE = 150_000


def scene_arrays(root, scene):
    hh, transform, crs = read_layer(root / scene["products"]["HH"])
    hv, _, _ = read_layer(root / scene["products"]["HV"])
    return hh, hv, transform, crs


def labeled_scenes(root, manifest):
    labels_manifest = json.loads((root / "labels" / "manifest.json").read_text(encoding="utf-8"))
    ok = {entry["scene_id"]: entry for entry in labels_manifest["labels"] if entry.get("status") == "ok"}
    return [(scene, root / "labels" / ok[scene["id"]]["label"]) for scene in manifest["scenes"] if scene["id"] in ok], labels_manifest


def evaluate_water(root, out_dir, models_dir, aoi_name):
    manifest = load_manifest(root)
    crs, transform, shape = manifest_grid(manifest)
    resolution = abs(transform.a)
    scenes, labels_manifest = labeled_scenes(root, manifest)
    if len(scenes) < 2:
        raise SystemExit("Se requieren al menos dos fechas etiquetadas")
    covariates = load_covariates(root)
    worldcover, _, _ = read_layer(root / "covariates" / "worldcover.tif")
    worldcover = np.asarray(worldcover).astype(np.int32)
    ids = block_ids(shape, BLOCK)
    results = {"aoi": aoi_name, "label_source": labels_manifest["rule"], "dates": [], "thresholds": {}, "lightgbm": {}}
    train_X, train_y, test_X, test_y, test_groups = [], [], [], [], []
    per_date = {}
    detections = out_dir
    detections.mkdir(parents=True, exist_ok=True)
    hand = covariates.get("hand_proxy")
    slope = covariates.get("slope")
    for scene, label_path in scenes:
        date = scene["fecha_observacion"][:10]
        hh, hv, _, _ = scene_arrays(root, scene)
        label, _, _ = read_layer(label_path)
        label = np.asarray(label)
        labeled = label != LABEL_NODATA
        valid_sar = np.isfinite(hh) & np.isfinite(hv)
        threshold_rows = {}
        for method, fn in (("otsu", otsu_threshold), ("kittler_illingworth", kittler_illingworth_threshold)):
            threshold = fn(hh, valid_sar)
            mask = water_mask(hh, threshold, hand, MAX_HAND_M, slope, MAX_SLOPE_DEG)
            evaluable = labeled & (mask != 255)
            scores = binary_scores(label[evaluable] == 1, mask[evaluable] == 1)
            by_class = scores_by_group(label[evaluable] == 1, mask[evaluable] == 1, worldcover[evaluable], WORLDCOVER)
            threshold_rows[method] = {"threshold_db": threshold, "area_km2": area_km2(mask, resolution), "scores": scores, "by_worldcover": {k: {m: v[m] for m in ("n", "f1", "iou", "precision", "recall")} for k, v in by_class.items()}}
            suffix = "otsu" if method == "otsu" else "ki"
            write_cog(detections / f"{date}_water_{suffix}.tif", mask, transform, crs, 255, "uint8", {"method": f"HH < {threshold:.2f} dB ({'Otsu' if method == 'otsu' else 'Kittler-Illingworth'}); HAND <= {MAX_HAND_M} m; pendiente <= {MAX_SLOPE_DEG} grados", "values": "1 agua, 0 no agua, 255 sin dato", "nisar_scene": scene["granulo"], "status": "estimacion, no verdad de terreno"})
        layers = scene_features(hh, hv, covariates)
        X, valid, names = features_matrix(layers)
        y_grid = np.where(label == 1, 1, 0)
        usable = valid & labeled
        train_mask, test_mask = spatial_block_split(ids, usable, TEST_FRACTION, seed=0, buffer_blocks=BUFFER_BLOCKS)
        assert_blocks_not_shared(ids, train_mask, test_mask)
        Xg = np.full(shape + (len(names),), np.nan, dtype=np.float32)
        Xg[valid] = X
        Xt, yt = subsample_balanced(Xg[train_mask], y_grid[train_mask], MAX_PER_CLASS_PER_DATE, seed=1)
        train_X.append(Xt)
        train_y.append(yt)
        test_X.append(Xg[test_mask])
        test_y.append(y_grid[test_mask])
        test_groups.append(worldcover[test_mask])
        per_date[date] = {"scene": scene, "Xg": Xg, "valid": valid, "label": label, "labeled": labeled, "label_water_km2": area_km2(np.where(label == 1, 1, 0), resolution)}
        results["dates"].append({"date": date, "scene_id": scene["id"], "label_water_km2": per_date[date]["label_water_km2"], "labeled_fraction": float(labeled.mean()), "thresholds": threshold_rows})
        print(date, {m: round(r["scores"]["f1"] or 0, 3) for m, r in threshold_rows.items()}, flush=True)
    names_used = names
    X_train = np.concatenate(train_X)
    y_train = np.concatenate(train_y)
    rng = np.random.default_rng(0)
    order = rng.permutation(X_train.shape[0])
    cut = int(order.size * 0.9)
    booster = train_lightgbm(X_train[order[:cut]], y_train[order[:cut]], X_train[order[cut:]], y_train[order[cut:]])
    X_test = np.concatenate(test_X)
    y_test = np.concatenate(test_y)
    g_test = np.concatenate(test_groups)
    proba = predict_proba(booster, X_test)
    spatial_scores = binary_scores(y_test == 1, proba > 0.5)
    spatial_by_class = scores_by_group(y_test == 1, proba > 0.5, g_test, WORLDCOVER)
    # Temporal holdout: train on every labeled date but the last, test on the last date (all blocks).
    dates = sorted(per_date)
    hold = dates[-1]
    Xh = np.concatenate([subsample_balanced(per_date[d]["Xg"][per_date[d]["valid"] & per_date[d]["labeled"]], np.where(per_date[d]["label"] == 1, 1, 0)[per_date[d]["valid"] & per_date[d]["labeled"]], MAX_PER_CLASS_PER_DATE, seed=2)[0] for d in dates[:-1]])
    yh = np.concatenate([subsample_balanced(per_date[d]["Xg"][per_date[d]["valid"] & per_date[d]["labeled"]], np.where(per_date[d]["label"] == 1, 1, 0)[per_date[d]["valid"] & per_date[d]["labeled"]], MAX_PER_CLASS_PER_DATE, seed=2)[1] for d in dates[:-1]])
    booster_temporal = train_lightgbm(Xh, yh)
    sel = per_date[hold]["valid"] & per_date[hold]["labeled"]
    proba_hold = predict_proba(booster_temporal, per_date[hold]["Xg"][sel])
    temporal_scores = binary_scores(per_date[hold]["label"][sel] == 1, proba_hold > 0.5)
    for date in dates:
        info = per_date[date]
        p = predict_proba(booster, info["Xg"][info["valid"]])
        mask = np.full(shape, 255, dtype=np.uint8)
        mask[info["valid"]] = (p > 0.5).astype(np.uint8)
        write_cog(detections / f"{date}_water_lgbm.tif", mask, transform, crs, 255, "uint8", {"method": "LightGBM por pixel entrenado con etiquetas Sentinel-2 MNDWI; umbral 0.5", "values": "1 agua, 0 no agua, 255 sin dato", "nisar_scene": info["scene"]["granulo"], "status": "estimacion evaluada en bloques retenidos; no verdad de terreno"})
        for row in results["dates"]:
            if row["date"] == date:
                row["lightgbm_area_km2"] = area_km2(mask, resolution)
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"{aoi_name}_water_lgbm.txt"
    booster.save_model(str(model_path))
    importance = feature_importance(booster, names_used)
    results["lightgbm"] = {"features": names_used, "n_train": int(X_train.shape[0]), "n_test": int(X_test.shape[0]), "spatial_block_holdout": spatial_scores, "spatial_by_worldcover": {k: {m: v[m] for m in ("n", "f1", "iou", "precision", "recall")} for k, v in spatial_by_class.items()}, "temporal_holdout": {"test_date": hold, "train_dates": dates[:-1], **temporal_scores}, "feature_importance_gain": importance, "model": str(model_path)}
    results["split"] = {"block_pixels": BLOCK, "test_fraction": TEST_FRACTION, "buffer_blocks": BUFFER_BLOCKS, "rule": "bloques completos en un solo conjunto; anillo de bloques excluido alrededor de la prueba; fecha final retenida para la prueba temporal"}
    write_model_card(models_dir / f"{aoi_name}_water_lgbm.card.json", f"{aoi_name}_water_lgbm", "agua abierta por pixel (binario) en NISAR GCOV HH/HV + terreno", {"aoi": aoi_name, "dates": dates, "labels": labels_manifest["rule"], "label_window_days": labels_manifest["window_days"]}, results["split"], {"spatial_block_holdout": spatial_scores, "temporal_holdout": results["lightgbm"]["temporal_holdout"]}, names_used, ["Etiquetas opticas de agua abierta: el agua bajo vegetacion no esta etiquetada y no se evalua.", "Un solo AOI y una temporada: no demuestra generalizacion a otras cuencas.", "La prueba temporal usa una unica fecha retenida.", "No es un detector de inundacion ni de riesgo; describe agua abierta observada."], {"feature_importance_gain": importance})
    record(f"detection_{aoi_name}", {"dataset": {"aoi": aoi_name, "dates": dates}, "split": results["split"], "metrics": {"thresholds": {r["date"]: {m: t["scores"]["f1"] for m, t in r["thresholds"].items()} for r in results["dates"]}, "lightgbm_spatial_f1": spatial_scores["f1"], "lightgbm_temporal_f1": temporal_scores["f1"]}})
    print("LightGBM F1 bloques:", round(spatial_scores["f1"] or 0, 3), "F1 fecha retenida:", round(temporal_scores["f1"] or 0, 3), flush=True)
    return results


def evaluate_change(root, out_dir, aoi_name, alpha=0.01, min_pixels=4):
    manifest = load_manifest(root)
    crs, transform, shape = manifest_grid(manifest)
    scenes = manifest["scenes"]
    before, after = scenes[0], scenes[-1]
    hh0, hv0, _, _ = scene_arrays(root, before)
    hh1, hv1, _, _ = scene_arrays(root, after)
    worldcover, _, _ = read_layer(root / "covariates" / "worldcover.tif") if (root / "covariates" / "worldcover.tif").is_file() else (None, None, None)
    linear = lambda db: np.where(np.isfinite(db), 10 ** (np.asarray(db, dtype=np.float64) / 10), np.nan)
    looks = []
    for scene, hh in ((before, hh0), (after, hh1)):
        name = (scene.get("ancillary") or {}).get("looks")
        if name and (root / name).is_file():
            values, _, _ = read_layer(root / name)
            looks.append(values)
            source = "numberOfLooks del producto"
        else:
            homogeneous = np.isfinite(hh)
            if worldcover is not None:
                homogeneous &= np.isin(worldcover, [30, 40, 60])  # grassland, cropland, bare: closer to homogeneous targets
            looks.append(enl_estimate(linear(hh), homogeneous))
            source = "ENL estimado (media^2/varianza) sobre pastizal, cultivo y suelo desnudo"
    statistic, p = conradsen_diagonal_test([linear(hh0), linear(hv0)], [linear(hh1), linear(hv1)], looks[0], looks[1])
    delta = log_ratio_db(hh0, hh1)
    conradsen = change_mask_from_pvalue(p, delta, alpha, min_pixels)
    lower, upper = mad_threshold(delta)
    mad = change_mask_from_delta(delta, lower, upper, min_pixels)
    out_dir.mkdir(parents=True, exist_ok=True)
    pair = f"{before['fecha_observacion'][:10]}_{after['fecha_observacion'][:10]}"
    write_cog(out_dir / f"{pair}_change_conradsen.tif", conradsen, transform, crs, 255, "uint8", {"method": f"prueba omnibus de Conradsen (caso diagonal HH,HV), alpha={alpha}, objetos >= {min_pixels} px", "looks": source, "values": "1 disminucion significativa, 2 aumento significativo, 0 sin cambio, 255 sin dato", "status": "cambio estadistico de la senal; no clasifica la causa"})
    write_cog(out_dir / f"{pair}_change_mad.tif", mad, transform, crs, 255, "uint8", {"method": f"HH log-ratio fuera de mediana +/- 3*1.4826*MAD [{lower:.2f},{upper:.2f}] dB, objetos >= {min_pixels} px", "values": "1 disminucion, 2 aumento, 0 sin cambio, 255 sin dato", "status": "cambio de senal; no clasifica la causa"})
    write_cog(out_dir / f"{pair}_pvalue_conradsen.tif", p, transform, crs, np.nan, "float32", {"meaning": "valor p de la prueba de Conradsen; menor = cambio mas probable"})
    both_valid = (conradsen != CHANGE_NODATA) & (mad != CHANGE_NODATA)
    a = conradsen[both_valid] != 0
    b = mad[both_valid] != 0
    agreement = binary_scores(a, b)
    groups = worldcover.astype(np.int32) if worldcover is not None else None
    result = {"aoi": aoi_name, "pair": {"before": before["fecha_observacion"], "after": after["fecha_observacion"]}, "looks_source": source, "looks_median": [float(np.nanmedian(l)) if isinstance(l, np.ndarray) else float(l) for l in looks], "alpha": alpha, "min_pixels": min_pixels, "mad_thresholds_db": [lower, upper], "conradsen_fractions": change_fractions(conradsen, groups, WORLDCOVER), "mad_fractions": change_fractions(mad, groups, WORLDCOVER), "agreement_conradsen_vs_mad": {"iou": agreement["iou"], "n": agreement["n"]}, "limits": ["Sin etiquetas independientes de cambio urbano: no se reporta exactitud.", "Dos fechas: el cambio detectado incluye humedad, vegetacion y geometria, no solo construccion o dano.", "La prueba asume canales independientes porque el GCOV publicado solo trae terminos diagonales."]}
    record(f"change_{aoi_name}", {"dataset": result["pair"], "split": "sin etiquetas; comparacion entre metodos", "metrics": {"agreement_iou": agreement["iou"], "conradsen_change_fraction": result["conradsen_fractions"]["all"]}})
    print(aoi_name, "cambio Conradsen:", result["conradsen_fractions"]["all"], "IoU con MAD:", round(agreement["iou"] or 0, 3), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--water-aois", nargs="*", default=["."])
    parser.add_argument("--change-aois", nargs="*", default=["metropolitana", "valparaiso"])
    parser.add_argument("--output", default="docs/detection_benchmark.json")
    args = parser.parse_args()
    data = Path(args.data_dir)
    benchmark = {"generated_utc": datetime.now(timezone.utc).isoformat(), "water": [], "change": []}
    for aoi in args.water_aois:
        name = "pantanal" if aoi == "." else aoi
        benchmark["water"].append(evaluate_water(data / aoi, data / aoi / "detections", Path("models"), name))
    for aoi in args.change_aois:
        if (data / aoi / "manifest.json").is_file():
            benchmark["change"].append(evaluate_change(data / aoi, data / aoi / "detections", aoi))
    dump = lambda v: float(v) if isinstance(v, np.floating) else int(v) if isinstance(v, np.integer) else str(v)
    Path(args.output).write_text(json.dumps(benchmark, ensure_ascii=False, indent=2, default=dump), encoding="utf-8")
    Path("catalog/detection_reference.json").write_text(json.dumps(viewer_reference(benchmark), ensure_ascii=False, indent=2, default=dump), encoding="utf-8")
    print("->", args.output)


def viewer_reference(benchmark):
    """Compact, viewer-facing summary: the app shows only what has an evaluation here."""
    reference = {"generated_utc": benchmark["generated_utc"], "water": {}, "change": {}}
    for block in benchmark["water"]:
        thresholds = {}
        for method in ("otsu", "kittler_illingworth"):
            f1 = [r["thresholds"][method]["scores"]["f1"] for r in block["dates"] if r["thresholds"][method]["scores"]["f1"] is not None]
            thresholds[method] = {"n_dates": len(f1), "mean_f1": float(np.mean(f1)) if f1 else None}
        lg = block["lightgbm"]
        reference["water"][block["aoi"]] = {"label_source": block["label_source"], "thresholds": thresholds, "lightgbm": {"spatial_f1": lg["spatial_block_holdout"]["f1"], "spatial_iou": lg["spatial_block_holdout"]["iou"], "temporal_f1": lg["temporal_holdout"]["f1"], "temporal_test_date": lg["temporal_holdout"]["test_date"], "n_test": lg["n_test"]}, "areas": [{"date": r["date"], "label_km2": r["label_water_km2"], "otsu_km2": r["thresholds"]["otsu"]["area_km2"], "ki_km2": r["thresholds"]["kittler_illingworth"]["area_km2"], "lightgbm_km2": r.get("lightgbm_area_km2")} for r in block["dates"]], "split": block["split"]}
    for block in benchmark["change"]:
        fractions = block["conradsen_fractions"]
        land_keys = [k for k in fractions if k not in ("all", "agua permanente")]
        n_land = sum(fractions[k]["n"] for k in land_keys)
        land = {"n": n_land, "decrease": sum((fractions[k]["decrease"] or 0) * fractions[k]["n"] for k in land_keys) / n_land if n_land else None, "increase": sum((fractions[k]["increase"] or 0) * fractions[k]["n"] for k in land_keys) / n_land if n_land else None}
        reference["change"][block["aoi"]] = {"pair": block["pair"], "alpha": block["alpha"], "looks_source": block["looks_source"], "all": fractions["all"], "land": land, "permanent_water": fractions.get("agua permanente", {}), "by_worldcover": {k: v for k, v in fractions.items() if k != "all"}, "agreement_iou_with_mad": block["agreement_conradsen_vs_mad"]["iou"], "limits": block["limits"]}
    return reference


if __name__ == "__main__":
    main()
