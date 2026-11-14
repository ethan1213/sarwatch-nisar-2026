"""Rolling-origin forecast benchmark for AOI summary series; writes docs/forecast_benchmark.json
and catalog/prediction_reference.json (read by the viewer). Supersedes evaluate_baseline.py.

Targets per date: median HH dB over the common valid mask of the whole series, and open-water area km2
from detections/<date>_water_{lgbm|ki|otsu}.tif when present (first available). Exogenous inputs end the day before each target
date: ERA5 antecedent rainfall (7 and 30 days) and GloFAS discharge (7-day mean) from Open-Meteo.
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.experiments import record
from sarwatch.ml.forecast import MODELS, antecedent_sum, build_design, publication_decision, rolling_evaluation
from sarwatch.ml.grids import load_manifest, manifest_grid, read_layer
from sarwatch.ml.water import area_km2

MIN_COVERAGE = 0.5


def summary_series(root, manifest):
    """Median HH dB per eligible date on the common finite mask, plus Otsu water area when available."""
    eligible = [s for s in manifest["scenes"] if s["finite_positive_fraction"]["HH"] >= MIN_COVERAGE]
    layers = []
    for scene in eligible:
        values, _, _ = read_layer(root / scene["products"]["HH"])
        layers.append(values)
    common = np.logical_and.reduce([np.isfinite(v) for v in layers])
    crs, transform, _ = manifest_grid(manifest)
    rows = []
    for scene, values in zip(eligible, layers):
        day = scene["fecha_observacion"][:10]
        water_path = next((root / "detections" / f"{day}_water_{m}.tif" for m in ("lgbm", "ki", "otsu") if (root / "detections" / f"{day}_water_{m}.tif").is_file()), root / "detections" / "missing.tif")
        area = None
        if water_path.is_file():
            mask, _, _ = read_layer(water_path)
            area = area_km2(mask, abs(transform.a))
        rows.append({"date": day, "scene_id": scene["id"], "median_hh_db": float(np.median(values[common])), "water_area_km2": area})
    return rows, float(common.mean())


def exogenous_daily(manifest, start, end, points=3):
    """Daily ERA5 rainfall at the AOI centre and max GloFAS discharge over a points x points grid."""
    from weather import fetch_river_discharge, fetch_weather
    west, south, east, north = manifest["bbox_wgs84"]
    lat, lon = (south + north) / 2, (west + east) / 2
    weather = fetch_weather(round(lat, 3), round(lon, 3), start, end)
    daily = weather["payload"]["daily"]
    rain = {"time": daily["time"], "values": [np.nan if v is None else float(v) for v in daily["precipitation_sum"]], "source": "ERA5 via Open-Meteo archive, centro del AOI"}
    discharge_stack, cells = [], []
    for la in np.linspace(south, north, points):
        for lo in np.linspace(west, east, points):
            result = fetch_river_discharge(round(float(la), 3), round(float(lo), 3), start, end)
            series = [np.nan if v is None else float(v) for v in result["payload"]["daily"]["river_discharge"]]
            discharge_stack.append(series)
            cells.append([result["cell_latitude"], result["cell_longitude"]])
            times = result["payload"]["daily"]["time"]
    stack = np.array(discharge_stack, dtype=float)
    with np.errstate(all="ignore"):
        maximum = np.nanmax(stack, axis=0)
    discharge = {"time": times, "values": maximum.tolist(), "cells": cells, "source": f"GloFAS via Open-Meteo Flood API; máximo diario entre {points*points} celdas del AOI"}
    return rain, discharge


def benchmark_target(rows, key, rain, discharge):
    dates = [r["date"] for r in rows if r[key] is not None]
    target = [r[key] for r in rows if r[key] is not None]
    if len(dates) < 4:
        return {"target": key, "status": "serie insuficiente", "n_dates": len(dates)}
    exo = {}
    if rain is not None:
        exo["rain_7d_mm"] = antecedent_sum(rain["time"], rain["values"], dates, 7, lag_days=1)
        exo["rain_30d_mm"] = antecedent_sum(rain["time"], rain["values"], dates, 30, lag_days=1)
    if discharge is not None:
        exo["discharge_7d_mean_m3s"] = antecedent_sum(discharge["time"], discharge["values"], dates, 7, lag_days=1) / 7
    d, y, X, names = build_design(dates, target, exo)
    results = rolling_evaluation(d, y, X)
    decision = publication_decision(results)
    return {"target": key, "n_dates": len(dates), "features": names, "models": results, "decision": decision}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--aoi", default=".")
    parser.add_argument("--offline", action="store_true", help="Sin covariables meteorológicas ni de caudal")
    args = parser.parse_args()
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    rows, common_coverage = summary_series(root, manifest)
    rain = discharge = None
    if not args.offline:
        start = (date.fromisoformat(rows[0]["date"]) - timedelta(days=40)).isoformat()
        end = rows[-1]["date"]
        try:
            rain, discharge = exogenous_daily(manifest, start, end)
        except Exception as exc:  # external providers must never block the benchmark
            print("Covariables externas no disponibles:", type(exc).__name__, exc, flush=True)
    output = {"aoi": manifest.get("region", args.aoi), "generated_utc": datetime.now(timezone.utc).isoformat(), "series": rows, "common_coverage": common_coverage, "exogenous": {"rain": None if rain is None else {k: rain[k] for k in ("source",)}, "discharge": None if discharge is None else {k: discharge[k] for k in ("source", "cells")}}, "targets": [benchmark_target(rows, "median_hh_db", rain, discharge), benchmark_target(rows, "water_area_km2", rain, discharge)], "kind": "retrospective_rolling_origin", "limits": ["Pocas fechas y un solo AOI: referencia metodológica, no servicio de pronóstico.", "Los objetivos son resúmenes del recorte, no inundación por píxel ni riesgo.", "ERA5 y GloFAS son modelos a escala mucho más gruesa que el SAR.", "Intervalos conformes calculados con muy pocos residuos pasados."]}
    Path("docs/forecast_benchmark.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, default=_jsonable), encoding="utf-8")
    median_block = output["targets"][0]
    persistence = median_block.get("models", {}).get("persistence", {}) if "models" in median_block else {}
    reference = {"target": "Mediana HH del recorte en píxeles comunes válidos", "method": "Comparación en origen rodante: persistencia, climatología, Ridge y Ridge sobre anomalías", "kind": "retrospective_reference_only", "n_evaluations": persistence.get("n_evaluations", 0), "mae_db": persistence.get("mae"), "best_model": median_block.get("decision"), "models_mae": {name: res.get("mae") for name, res in median_block.get("models", {}).items()}, "water_area": {"decision": output["targets"][1].get("decision"), "models_mae_km2": {name: res.get("mae") for name, res in output["targets"][1].get("models", {}).items()}} if "models" in output["targets"][1] else output["targets"][1], "limitations": output["limits"]}
    Path("catalog/prediction_reference.json").write_text(json.dumps(reference, ensure_ascii=False, indent=2, default=_jsonable), encoding="utf-8")
    record("forecast_" + ("pantanal" if args.aoi == "." else args.aoi), {"dataset": {"aoi": output["aoi"], "dates": [r["date"] for r in rows]}, "split": "rolling_origin", "metrics": {t["target"]: {name: res.get("mae") for name, res in t.get("models", {}).items()} for t in output["targets"]}})
    for t in output["targets"]:
        print(t["target"], {name: round(res["mae"], 4) for name, res in t.get("models", {}).items() if res.get("mae") is not None}, t.get("decision"), flush=True)


def _jsonable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return str(value)


if __name__ == "__main__":
    main()
