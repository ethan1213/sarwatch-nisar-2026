"""PostFuego: dynamic post-fire debris-flow threshold for an AOI (built for Las Condes / Quebrada Honda).

Combines: burn severity (scripts/fetch_fire_dnbr.py output), D8 flow concentration from the DEM
covariate, antecedent rainfall scenarios, and the most recently observed NISAR HH state (as a current
soil-moisture snapshot, NOT a retroactive predictor of a past event). Writes docs/postfire_benchmark.json
and catalog/postfire_reference.json (read by the viewer and the assistant).

Honesty, stated once here and repeated in every output file: this is an uncalibrated heuristic over two
known events in one quebrada. It is a worked proof of concept, not a validated hazard model. See
sarwatch/ml/debris_flow.py for the exact formula and docs/postfuego_las_condes.md for the full brief
this answers, its data gaps, and what would be needed to calibrate it for real.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.debris_flow import dynamic_threshold, explain, semaphore
from sarwatch.ml.grids import load_manifest, manifest_grid, read_layer, write_cog
from sarwatch.ml.hydrology import coarsen_mean, flow_accumulation, flow_direction
from sarwatch.ml.wildfire import NODATA as FIRE_NODATA

COARSEN_FACTOR = 5  # 20 m native -> ~100 m for flow routing; see sarwatch/ml/hydrology.py docstring
# Documented in the brief this script answers (DGA/CR2, Senapred, municipal report, June 2026).
SCENARIOS = {
    "enero": {"label": "31-enero (seco)", "antecedent_rain_mm": 2.0, "observed_30min_mm": 19.2, "note": "tormenta convectiva de verano; 11 a 28 viviendas con dano", "use_nisar": False},
    "octubre": {"label": "8-octubre (saturado)", "antecedent_rain_mm": 110.0, "observed_30min_mm": 8.8, "note": "frontal + baja segregada tras 70-140 mm el 6 y 7 de oct; 2015 viviendas afectadas", "use_nisar": True},
    "actual": {"label": "esta semana (por defecto, sin lluvia reciente)", "antecedent_rain_mm": 0.0, "observed_30min_mm": None, "note": "actualizar con la lluvia de los ultimos 3-7 dias antes de usar", "use_nisar": True},
}


def upsample_nearest(coarse, factor, shape):
    repeated = np.repeat(np.repeat(coarse, factor, axis=0), factor, axis=1)
    out = np.full(shape, np.nan, dtype=coarse.dtype)
    rows = min(repeated.shape[0], shape[0])
    cols = min(repeated.shape[1], shape[1])
    out[:rows, :cols] = repeated[:rows, :cols]
    return out


def era5_cross_check(lon, lat):
    from weather import fetch_weather
    totals = {}
    for key, window in (("enero", ("2026-01-24", "2026-01-31")), ("octubre", ("2026-10-01", "2026-10-08"))):
        result = fetch_weather(round(lat, 3), round(lon, 3), *window)
        total = sum(v for v in result["payload"]["daily"]["precipitation_sum"] if v is not None)
        totals[key] = round(total, 1)
    return totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", default="metropolitana")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--point", nargs=2, type=float, default=[-70.52, -33.40], metavar=("LON", "LAT"), help="Punto representativo (p.ej. Las Condes) para el cruce con ERA5")
    args = parser.parse_args()
    root = Path(args.data_dir) / args.aoi
    manifest = load_manifest(root)
    crs, transform, shape = manifest_grid(manifest)
    resolution = abs(transform.a)

    dem, _, _ = read_layer(root / "covariates" / "dem.tif")
    coarse_dem = coarsen_mean(dem, COARSEN_FACTOR)
    direction = flow_direction(coarse_dem)
    accumulation = flow_accumulation(coarse_dem, direction)
    reference_accumulation = float(np.nanmedian(accumulation[np.isfinite(coarse_dem)]))

    fire_path = root / "wildfire" / "severity.tif"
    if not fire_path.is_file():
        raise SystemExit(f"Falta {fire_path}. Ejecuta primero: python scripts/fetch_fire_dnbr.py --aoi {args.aoi}")
    severity, _, _ = read_layer(fire_path)
    high_mask = np.isin(severity, (3, 4)).astype(np.float64)
    high_mask[severity == FIRE_NODATA] = np.nan
    coarse_high_fraction = coarsen_mean(high_mask, COARSEN_FACTOR)
    wildfire_manifest = json.loads((root / "wildfire" / "manifest.json").read_text(encoding="utf-8"))

    scenes = sorted(manifest["scenes"], key=lambda s: s["fecha_observacion"])
    before_hh, _, _ = read_layer(root / scenes[0]["products"]["HH"])
    after_hh, _, _ = read_layer(root / scenes[-1]["products"]["HH"])
    delta_hh = after_hh - before_hh
    coarse_delta_hh = coarsen_mean(delta_hh, COARSEN_FACTOR)

    try:
        era5 = era5_cross_check(*args.point)
        era5_status = "ok"
    except Exception as exc:
        era5, era5_status = None, f"no disponible ({type(exc).__name__})"

    results = {}
    for key, scenario in SCENARIOS.items():
        threshold_coarse, factors = dynamic_threshold(coarse_high_fraction, scenario["antecedent_rain_mm"], accumulation, reference_accumulation, delta_hh_db=coarse_delta_hh if scenario["use_nisar"] else None)
        threshold_native = upsample_nearest(threshold_coarse.astype(np.float32), COARSEN_FACTOR, shape)
        sema_native = semaphore(threshold_native)
        out_dir = root / "postfire"
        write_cog(out_dir / f"umbral_{key}.tif", threshold_native, transform, crs, np.nan, "float32", {"method": "umbral dinamico heuristico PostFuego (sarwatch/ml/debris_flow.py), no calibrado", "scenario": scenario["label"]})
        write_cog(out_dir / f"semaforo_{key}.tif", sema_native, transform, crs, 255, "uint8", {"values": "0 rojo, 1 amarillo, 2 verde, 255 sin dato"})
        valid = np.isfinite(threshold_coarse)
        median_threshold = float(np.nanmedian(threshold_coarse))
        median_factors = {name: float(np.nanmedian(values)) for name, values in factors.items()}
        would_have = None if scenario["observed_30min_mm"] is None else bool(scenario["observed_30min_mm"] >= median_threshold)
        results[key] = {"label": scenario["label"], "antecedent_rain_mm": scenario["antecedent_rain_mm"], "observed_30min_mm": scenario["observed_30min_mm"], "note": scenario["note"], "era5_cross_check_mm": era5.get(key) if era5 else None, "median_threshold_mm_30min": round(median_threshold, 1), "min_threshold_mm_30min": round(float(np.nanmin(threshold_coarse[valid])), 1) if valid.any() else None, "fraction_rojo": float((sema_native == 0).mean()), "fraction_amarillo": float((sema_native == 1).mean()), "fraction_verde": float((sema_native == 2).mean()), "explain_median_cell": explain(median_factors, median_threshold), "would_have_triggered": would_have}

    output = {"aoi": args.aoi, "generated_utc": datetime.now(timezone.utc).isoformat(), "coarsen_factor": COARSEN_FACTOR, "resolution_m_native": resolution, "resolution_m_hydrology": resolution * COARSEN_FACTOR, "fire": {"pre_window": wildfire_manifest["pre_window"], "post_window": wildfire_manifest["post_window"], "pre_valid_fraction": wildfire_manifest["pre_valid_fraction"], "post_valid_fraction": wildfire_manifest["post_valid_fraction"], "severity_summary": wildfire_manifest["severity_summary"], "caveat": wildfire_manifest["limits"][0]}, "nisar_window": {"before": scenes[0]["fecha_observacion"], "after": scenes[-1]["fecha_observacion"], "note": "Delta HH entre estas dos fechas es el estado de humedad MAS RECIENTE disponible; NO es una prediccion retroactiva del evento de octubre, que ocurrio entre ambas fechas."}, "era5_cross_check_status": era5_status, "scenarios": results, "method": "sarwatch.ml.debris_flow.dynamic_threshold; ver docstring para la justificacion de cada factor", "limits": ["Heuristica no calibrada: dos eventos no entrenan ni validan un modelo.", "La ventana de fecha del incendio (dNBR) es un ejemplo pendiente de confirmar con CONAF/Sernageomin.", "No hay interferometria (GUNW) en este calculo todavia: el factor de carga de sedimento del cauce no esta incluido (ver catalog/las_condes_gunw_candidates.json).", "El umbral de 30 minutos se compara con lluvia observada historica, no con un pronostico en vivo.", f"Resolucion de hidrologia de {resolution * COARSEN_FACTOR:.0f} m: identifica que sub-cuencas concentran mas agua, no el cauce exacto metro a metro."]}
    Path("docs/postfire_benchmark.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    reference = {"aoi": args.aoi, "generated_utc": output["generated_utc"], "fire_severity_summary": wildfire_manifest["severity_summary"], "nisar_window": output["nisar_window"], "scenarios": results, "limits": output["limits"]}
    Path("catalog/postfire_reference.json").write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")
    for key, r in results.items():
        flag = "habria_disparado" if r["would_have_triggered"] else ("no_aplica" if r["would_have_triggered"] is None else "no_habria_disparado")
        print(key, "umbral mediano", r["median_threshold_mm_30min"], "mm/30min", flag, flush=True)
    print("->", "docs/postfire_benchmark.json", "catalog/postfire_reference.json")


if __name__ == "__main__":
    main()
