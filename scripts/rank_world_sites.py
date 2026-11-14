"""Rank candidate sites by repeat-geometry depth in the global CMR index built by build_global_catalog.py.

Reads catalog/global/gcov_index.csv.gz (metadata only, already downloaded) and, for each named point of
interest, finds its best repeat-orbit series (same track/direction/frame = comparable dates) and the
estimated raw download size. Writes catalog/global/top_sites.json. No imagery is downloaded here.
"""
import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

INDEX = Path("catalog/global/gcov_index.csv.gz")

# name -> (lon, lat, why). Mix of the wetlands already proposed and Chile's declared priority (fire /
# post-fire debris flow). Edit this dict or pass --points-file to rank a different list.
DEFAULT_POINTS = {
    "Everglades (US, humedal)": (-80.75, 25.6, "humedal; mismo fenómeno que Pantanal, 27 fechas"),
    "Atacama / Calama (CL, minería)": (-68.9, -22.45, "minería y suelo desnudo; 27 fechas"),
    "Salar de Surire (CL, Ramsar)": (-69.05, -18.85, "humedal altiplánico; 27 fechas"),
    "Concepción / Biobío (CL, incendios)": (-72.9, -36.9, "megaincendios recurrentes; 19 fechas desde feb-2026"),
    "Ñuble / Chillán (CL, incendios)": (-72.1, -36.6, "misma geometría que Biobío; 19 fechas"),
    "Las Condes / RM (CL, aluvión post-incendio)": (-70.52, -33.40, "ya procesado; foco del caso Quebrada Honda"),
    "Valparaíso / Viña (CL, incendios urbanos)": (-71.55, -33.05, "ya procesado; interfaz urbano-forestal"),
    "Araucanía / Temuco (CL, incendios)": (-72.6, -38.7, "zona forestal recurrente; 9 fechas"),
    "Ibera (AR, humedal)": (-57.25, -28.5, "humedal sudamericano comparable a Pantanal; 10 fechas"),
    "Sundarbans (IN/BD, manglar)": (89.0, 21.9, "manglar y riesgo de inundación; 10 fechas"),
    "Mekong delta (VN, inundación/agricultura)": (105.8, 9.9, "delta agrícola e inundación estacional; 10 fechas"),
    "Kakadu (AU, humedal)": (132.6, -12.6, "humedal tropical; 10 fechas"),
    "Campo de Hielo Norte (CL, glaciar)": (-73.4, -47.0, "glaciar; 10 fechas"),
    "Bahía Lomas (CL, Ramsar)": (-69.0, -52.6, "humedal subantártico; 10 fechas"),
    "Doñana (ES, humedal)": (-6.4, 37.0, "humedal mediterráneo; 9 fechas"),
}


def load_index():
    if not INDEX.is_file():
        raise SystemExit("Falta catalog/global/gcov_index.csv.gz; ejecuta scripts/build_global_catalog.py primero")
    with gzip.open(INDEX, "rt", encoding="utf-8") as handle:
        frame = pd.read_csv(handle)
    frame["date"] = frame["time_start"].str[:10]
    return frame


def best_series(frame, lon, lat):
    hit = frame[(frame.west <= lon) & (frame.east >= lon) & (frame.south <= lat) & (frame.north >= lat)].copy()
    if hit.empty:
        return None
    hit["geometry"] = hit.track.astype(str) + "_" + hit.direction.astype(str) + "_" + hit.frame.astype(str)
    grouped = hit.groupby("geometry").agg(n_fechas=("date", "nunique"), primera=("date", "min"), ultima=("date", "max"), gb=("size_mib", lambda s: round(s.sum() / 1024, 1)))
    return grouped.sort_values("n_fechas", ascending=False).iloc[0], grouped.sort_values("n_fechas", ascending=False).index[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--points-file", help="JSON opcional {nombre: [lon, lat, motivo]} en vez de la lista por defecto")
    parser.add_argument("--output", default="catalog/global/top_sites.json")
    args = parser.parse_args()
    points = DEFAULT_POINTS
    if args.points_file:
        raw = json.loads(Path(args.points_file).read_text(encoding="utf-8"))
        points = {k: (v[0], v[1], v[2]) for k, v in raw.items()}
    frame = load_index()
    rows = []
    for name, (lon, lat, why) in points.items():
        result = best_series(frame, lon, lat)
        if result is None:
            rows.append({"name": name, "lon": lon, "lat": lat, "why": why, "n_fechas": 0})
            continue
        series, geometry = result
        rows.append({"name": name, "lon": lon, "lat": lat, "why": why, "geometry": geometry, "n_fechas": int(series.n_fechas), "primera_fecha": series.primera, "ultima_fecha": series.ultima, "descarga_estimada_gb": float(series.gb)})
    rows.sort(key=lambda r: -r["n_fechas"])
    top = rows[: args.top]
    output = {"generated_utc": datetime.now(timezone.utc).isoformat(), "source": "catalog/global/gcov_index.csv.gz (metadatos CMR, sin imágenes descargadas)", "rule": "mejor geometría de órbita repetida (misma track/dirección/frame) por punto; mide disponibilidad en catálogo, no calidad ni cobertura procesada", "top": top, "all_candidates": rows}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    for i, r in enumerate(top, 1):
        print(f"{i:2d}. {r['name']:45s} {r.get('n_fechas',0):3d} fechas  {r.get('descarga_estimada_gb','-')} GB  [{r.get('primera_fecha','-')} a {r.get('ultima_fecha','-')}]")
    print("->", args.output)


if __name__ == "__main__":
    main()
