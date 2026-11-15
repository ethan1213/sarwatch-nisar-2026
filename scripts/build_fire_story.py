"""Pack the Biobío fire story for the viewer: small JSON and PNG files under catalog/fire_story/.

Everything here is derived from files other scripts already wrote (prepare, fetch_thermal, fetch_fire_weather,
fetch_fire_dnbr, evaluate_fire, evaluate_burn_scar); this script only selects, scores cells with the same
model the benchmark evaluated, and renders overlays. The viewer reads the pack and computes nothing.

    python scripts/build_fire_story.py
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from rasterio.transform import array_bounds, from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_fire import FEATURE_SETS, HORIZON_DAYS, fit_predict, samples
from sarwatch.ml.grids import load_manifest, read_layer
from sarwatch.ml.thermal import CONFIDENT_FIRE, fire_class

WIDTH = 1400
EVENT = ("2026-01-13T00:00", "2026-01-25T00:00")
RADAR_RAMP = np.array([[8, 12, 24], [34, 50, 94], [78, 122, 150], [170, 196, 178], [245, 240, 214]], dtype=np.float64)  # -24 .. -6 dB
SEVERITY_RGBA = {1: (250, 204, 82, 150), 2: (245, 140, 50, 215), 3: (224, 62, 40, 235), 4: (140, 16, 44, 245)}
MODEL = "radar_terreno"


def to_lonlat(values, transform, crs, resampling, nodata):
    height, width = values.shape
    west, south, east, north = transform_bounds(crs, "EPSG:4326", *array_bounds(height, width, transform), densify_pts=21)
    w, h = WIDTH, int(round(WIDTH * (north - south) / (east - west)))
    dst_transform = from_bounds(west, south, east, north, w, h)
    out = np.full((h, w), nodata, dtype=values.dtype)
    reproject(values, out, src_transform=transform, src_crs=crs, src_nodata=nodata, dst_transform=dst_transform, dst_crs="EPSG:4326", dst_nodata=nodata, resampling=resampling)
    west, south, east, north = array_bounds(h, w, dst_transform)
    return out, {"west": round(west, 6), "south": round(south, 6), "east": round(east, 6), "north": round(north, 6)}


def radar_png(path, db, transform, crs):
    grid, bounds = to_lonlat(db.astype("float32"), transform, crs, Resampling.average, np.nan)
    z = np.clip((np.nan_to_num(grid, nan=-24.0) + 24) / 18, 0, 1) * (len(RADAR_RAMP) - 1)
    low = np.floor(z).astype(int).clip(0, len(RADAR_RAMP) - 2)
    rgb = RADAR_RAMP[low] + (RADAR_RAMP[low + 1] - RADAR_RAMP[low]) * (z - low)[..., None]
    rgba = np.dstack([rgb, np.where(np.isfinite(grid), 255, 0)]).astype("uint8")
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)
    return bounds


def severity_png(path, severity, land, transform, crs):
    shown = np.where(land, severity, 255).astype("uint8")
    grid, bounds = to_lonlat(shown, transform, crs, Resampling.nearest, 255)
    rgba = np.zeros(grid.shape + (4,), dtype="uint8")
    for code, colour in SEVERITY_RGBA.items():
        rgba[grid == code] = colour
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)
    return bounds


def number(value, digits=2):
    return None if value is None or not np.isfinite(value) else round(float(value), digits)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--scar-aoi", default="concepcion_penco")
    parser.add_argument("--fire-aoi", default="biobio_fuego")
    parser.add_argument("--output", default="catalog/fire_story")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    # --- Después: radar per date and optical burn severity over the January scar -------------------------
    scar = Path(args.data_dir) / args.scar_aoi
    manifest = load_manifest(scar)
    severity, transform, crs = read_layer(scar / "wildfire" / "severity.tif")
    cover, _, _ = read_layer(scar / "covariates" / "worldcover.tif")
    land = (np.asarray(cover) != 80) & (np.asarray(cover) != 0)
    radar_layers = []
    for scene in manifest["scenes"]:
        hv, hv_transform, _ = read_layer(scar / scene["products"]["HV"])
        if hv_transform != transform or hv.shape != severity.shape:
            raise SystemExit("Radar y severidad en grillas distintas")
        date = scene["fecha_observacion"][:10]
        name = f"hv_{date}.png"
        bounds = radar_png(out / name, hv, transform, crs)
        radar_layers.append({"date": date, "png": name, "bounds": bounds, "valid_fraction": number(scene["finite_positive_fraction"]["HV"], 3), "granule": scene["granulo"]})
    severity_bounds = severity_png(out / "severity.png", np.asarray(severity), land, transform, crs)
    scar_benchmark = json.loads(Path("docs/burn_scar_benchmark.json").read_text(encoding="utf-8"))["aois"][args.scar_aoi]
    after = {"aoi": args.scar_aoi, "bbox_wgs84": manifest["bbox_wgs84"], "radar": radar_layers, "radar_scale_db": [-24, -6],
             "severity": {"png": "severity.png", "bounds": severity_bounds, "classes": {"1": "baja", "2": "moderada-baja", "3": "moderada-alta", "4": "alta"}, "label": scar_benchmark["label"]},
             "area_km2": scar_benchmark["area_km2"], "dates": scar_benchmark["dates"], "limits": scar_benchmark["limits"]}

    # --- Shared thermal cells of the wide window ------------------------------------------------------------
    fire = Path(args.data_dir) / args.fire_aoi
    cube = dict(np.load(fire / "thermal" / "cube.npz"))
    zones = json.loads((fire / "thermal" / "zones.json").read_text(encoding="utf-8"))
    thermal = json.loads((fire / "thermal" / "manifest.json").read_text(encoding="utf-8"))
    times = cube["times"].astype("U16").astype("datetime64[m]")
    shape = cube["lat"].shape
    n = cube["lat"].size
    as_array = lambda values: np.array([np.nan if v is None else v for v in values], dtype=np.float64)
    table = {"n_pixels": np.array(zones["n_pixels"]), **{k: as_array(v) for k, v in zones["static"].items()}}
    radar = [{"utc": f"{r['date']}T10:51:00", "hh_db": as_array(r["hh_db"]), "hv_db": as_array(r["hv_db"]), "fraccion_valida": as_array(r["fraccion_valida"])} for r in zones["radar"]]
    hot = np.isin(fire_class(cube["mask"]), CONFIDENT_FIRE)
    corner_lat, corner_lon = cube["corner_lat"], cube["corner_lon"]

    def polygon(index):
        row, col = divmod(int(index), shape[1])
        ring = [(corner_lon[row, col], corner_lat[row, col]), (corner_lon[row, col + 1], corner_lat[row, col + 1]), (corner_lon[row + 1, col + 1], corner_lat[row + 1, col + 1]), (corner_lon[row + 1, col], corner_lat[row + 1, col])]
        return {"type": "Polygon", "coordinates": [[[round(float(x), 5), round(float(y), 5)] for x, y in ring + ring[:1]]]}

    def terrain(index):
        return {"elev_m": number(table["elevacion_m"][index], 0), "slope_deg": number(table["pendiente_grados"][index], 1), "trees": number(table["cob_arboles"][index]), "crops": number(table["cob_cultivo"][index]), "grass": number(table["cob_pastizal"][index]), "urban": number(table["cob_urbano"][index], 3)}

    # --- Durante: hourly replay of the January event with ERA5 wind and air humidity ----------------------
    window = (times >= np.datetime64(EVENT[0])) & (times < np.datetime64(EVENT[1]))
    event_hot = hot[window].reshape(int(window.sum()), n)
    event_frp = cube["frp"][window].reshape(int(window.sum()), n)
    event_cells = np.flatnonzero(event_hot.any(axis=0))
    position = {int(cell): i for i, cell in enumerate(event_cells)}
    frames = []
    for t, flags, frp in zip(times[window], event_hot, event_frp):
        active = np.flatnonzero(flags)
        if active.size:
            frames.append({"t": str(t) + "Z", "cells": [position[int(c)] for c in active], "frp_mw": [number(frp[c], 0) for c in active]})
    weather = np.load(fire / "weather" / "era5_hourly.npz")
    weather_manifest = json.loads((fire / "weather" / "manifest.json").read_text(encoding="utf-8"))
    weather_times = weather["times"].astype("U16").astype("datetime64[m]")
    keep = (weather_times >= np.datetime64(EVENT[0])) & (weather_times < np.datetime64(EVENT[1]))
    short = {"temperature_2m": "t_c", "relative_humidity_2m": "rh_pct", "wind_speed_10m": "wind_kmh", "wind_direction_10m": "wind_from_deg", "wind_gusts_10m": "gust_kmh", "vapour_pressure_deficit": "vpd_kpa"}
    during = {"aoi": args.fire_aoi, "window_utc": [EVENT[0] + "Z", EVENT[1] + "Z"], "cell_km": [thermal["pixel_km_east_west"], thermal["pixel_km_north_south"]],
              "cells": {"type": "FeatureCollection", "features": [{"type": "Feature", "id": i, "geometry": polygon(c), "properties": {"i": i, "hours_hot": int(event_hot[:, c].sum()), "first": str(times[window][event_hot[:, c].argmax()]) + "Z", **terrain(c)}} for i, c in enumerate(event_cells)]},
              "frames": frames, "confident_detections": int(event_hot.sum()), "cells_hot": int(event_cells.size),
              "by_day": [{"date": str(day), "detections": int(event_hot[times[window].astype("datetime64[D]") == day].sum())} for day in np.unique(times[window].astype("datetime64[D]"))],
              "weather": {"provider": weather_manifest["provider"], "model": weather_manifest["model"], "license": weather_manifest["license"], "units": {"t_c": "°C", "rh_pct": "%", "wind_kmh": "km/h", "wind_from_deg": "° desde donde sopla", "gust_kmh": "km/h", "vpd_kpa": "kPa"},
                          "times": [str(t) + "Z" for t in weather_times[keep]],
                          "points": [{"lat": float(weather["requested_lat"][p]), "lon": float(weather["requested_lon"][p]), **{alias: [number(v, 1) for v in weather[name][p][keep]] for name, alias in short.items()}} for p in range(weather["requested_lat"].size)],
                          "limits": weather_manifest["limitations"]},
              "limits": ["Un foco GOES es una anomalía térmica dentro de una celda de unos 2 × 3 km: no es el frente ni el perímetro.", "Una observación por hora; la nube y el humo denso ocultan focos.", "El viento es reanálisis ERA5 en rejilla gruesa: orienta, no reemplaza la medición en terreno ni indica por dónde entrar."]}

    # --- Antes: cell ranking from the model the benchmark evaluated ---------------------------------------
    rows = samples(table, radar, cube, times, hot)
    columns = FEATURE_SETS[MODEL]
    stack = lambda selected: np.column_stack([np.concatenate([r["features"][c] for r in selected]) for c in columns])
    benchmark = json.loads(Path("docs/fire_benchmark_biobio.json").read_text(encoding="utf-8"))["aois"][args.fire_aoi]["anticipation"]
    test_dates = benchmark["split"]["temporal"]["test_dates"]
    cutoff = np.datetime64(test_dates[0]) - np.timedelta64(HORIZON_DAYS, "D")
    train = [r for r in rows if np.datetime64(r["date"]) <= cutoff]
    passes = {}
    for row in rows:
        if row["date"] in test_dates:
            probability = fit_predict(stack(train), np.concatenate([r["label"] for r in train]), stack([row]))
            passes[row["date"]] = {"cells": row["cells"], "score": probability, "label": row["label"], "kind": "fecha retenida: el modelo no vio esta pasada ni las posteriores"}
    latest = radar[-1]
    earlier = radar[-2]
    usable = (latest["fraccion_valida"] >= 0.5) & ~(table["cob_agua"] > 0.5) & (table["n_pixels"] > 0)
    current = {"hv_db": latest["hv_db"], "hh_db": latest["hh_db"], "hh_menos_hv_db": latest["hh_db"] - latest["hv_db"], "hv_cambio_db": latest["hv_db"] - earlier["hv_db"], "elevacion_m": table["elevacion_m"], "pendiente_grados": table["pendiente_grados"], **{k: v for k, v in table.items() if k.startswith("cob_")}}
    probability = fit_predict(stack(rows), np.concatenate([r["label"] for r in rows]), np.column_stack([current[c][usable] for c in columns]))
    latest_date = latest["utc"][:10]
    passes[latest_date] = {"cells": np.flatnonzero(usable), "score": probability, "label": None, "kind": "última pasada disponible: sin térmico posterior descargado, no se puede comprobar"}
    features, summary = [], {}
    for date, entry in passes.items():
        order = entry["score"].argsort().argsort() / max(entry["score"].size - 1, 1)  # rank within the pass, 0..1
        summary[date] = {"kind": entry["kind"], "cells": int(entry["score"].size)}
        if entry["label"] is not None:
            top = order >= 0.9
            summary[date].update(hot_next=int(entry["label"].sum()), hot_in_top_decile=int(entry["label"][top].sum()), top_decile_cells=int(top.sum()))
        entry["rank"] = dict(zip(entry["cells"].tolist(), order.tolist()))
        entry["hit"] = dict(zip(entry["cells"].tolist(), entry["label"].tolist())) if entry["label"] is not None else {}
    for cell in sorted(set().union(*[set(e["rank"]) for e in passes.values()])):
        properties = terrain(cell)
        for date, entry in passes.items():
            key = date.replace("-", "")
            if cell in entry["rank"]:
                properties[f"r{key}"] = round(entry["rank"][cell], 3)
                if entry["hit"]:
                    properties[f"h{key}"] = int(entry["hit"][cell])
        features.append({"type": "Feature", "id": int(cell), "geometry": polygon(cell), "properties": properties})
    scores = {name: {split: {k: number(v, 3) if isinstance(v, float) else v for k, v in model[split].items()} for split in ("spatial_blocks", "held_out_dates")} for name, model in benchmark["models"].items()}
    before = {"aoi": args.fire_aoi, "model": MODEL, "features": columns, "horizon_days": HORIZON_DAYS, "passes": summary, "held_out_dates": test_dates, "latest_date": latest_date, "train_until": str(cutoff),
              "benchmark": scores, "cells": {"type": "FeatureCollection", "features": features},
              "limits": ["Índice exploratorio: ordena celdas, no predice incendios ni mide riesgo.", "En fechas retenidas la ventaja sobre repetir dónde hubo calor es pequeña y descansa en pocas celdas con calor.", "Entrenado con pasadas de febrero a mayo: su orden para octubre queda fuera de esa temporada y no está comprobado.", "Muchos focos de marzo y abril coinciden con quemas agrícolas (hipótesis): el índice puede estar aprendiendo dónde hay cultivo."]}

    story = {"generated_utc": datetime.now(timezone.utc).isoformat(), "place": "Biobío: Concepción, Penco, Tomé y valle central",
             "sources": {"radar": "NISAR L2 GCOV PROVISIONAL, cuadro 003_A_159, HH/HV (ASF DAAC)", "heat": thermal["satellite"] + " · " + thermal["products"]["focos"], "weather": weather_manifest["provider"] + " · " + weather_manifest["model"], "optical": "Sentinel-2 L2A (Microsoft Planetary Computer)", "terrain": "Copernicus DEM 30 m · ESA WorldCover 2021"},
             "before": before, "during": during, "after": after}
    (out / "story.json").write_text(json.dumps(story, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"radar_layers": len(radar_layers), "event_cells": int(event_cells.size), "frames": len(frames), "ranked_cells": len(features), "passes": summary, "bytes": (out / "story.json").stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
