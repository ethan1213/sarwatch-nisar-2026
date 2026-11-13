"""SARWatch exploratory viewer. No synthetic environmental observations."""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import rasterio
import streamlit as st
from pyproj import Transformer
from science import difference

st.set_page_config(page_title="SARWatch · NISAR", page_icon="🌎", layout="wide")
st.title("🌎 SARWatch")
st.caption("NISAR · Pantanal · Explorador de cambios de la superficie terrestre")
st.info("Prototipo científico exploratorio. Cambios en dB no equivalen a inundaciones confirmadas. Datos PROVISIONAL; evaluación detallada de calidad pendiente.")
root = Path(os.environ.get("DATA_DIR", "data"))
manifest_path = root / "manifest.json"
if not manifest_path.is_file():
    st.warning("No hay capas procesadas. Prepara los HDF5 con scripts/prepare.py; el catálogo identifica las siete escenas reales.")
    st.json(json.loads(Path("catalog/scenes.json").read_text(encoding="utf-8")))
    st.stop()
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
scenes = manifest["scenes"]
labels = [s["fecha_observacion"][:10] for s in scenes]
st.sidebar.header("Explorar observaciones")
pol = st.sidebar.selectbox("Polarización", ["HH", "HV"])
default_before = next((i for i, scene in enumerate(scenes) if scene["finite_positive_fraction"].get(pol, 0) >= .5), 0)
before = st.sidebar.selectbox("Fecha inicial", range(len(scenes)), index=default_before, format_func=lambda i: labels[i])
after = st.sidebar.selectbox("Fecha final", range(len(scenes)), index=len(scenes)-1, format_func=lambda i: labels[i])
mode = st.sidebar.radio("Vista", ["Antes y después", "Diferencia en dB"])
st.sidebar.caption("Frecuencia A · banda L. frequencyB es una subbanda, no la banda S.")


@st.cache_data(max_entries=16)
def read_layer(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform, str(src.crs)


a, transform, crs = read_layer(str(root/scenes[before]["products"][pol]))
b, transform_b, crs_b = read_layer(str(root/scenes[after]["products"][pol]))
if a.shape != b.shape or transform != transform_b or crs != crs_b:
    st.error("Las grillas no son comparables.")
    st.stop()
delta = difference(a, b)
valid = np.isfinite(delta)
st.metric("Cobertura comparable (finitos positivos)", f"{valid.mean():.1%}")
if valid.mean() < .1:
    st.warning("Menos del 10% del recorte tiene valores comparables. Umbral de aviso de interfaz, no criterio científico de calidad: revisa otras fechas antes de interpretar.")
with st.expander("Cobertura por fecha"):
    st.dataframe(pd.DataFrame([{"fecha":s["fecha_observacion"], **s["finite_positive_fraction"]} for s in scenes]), hide_index=True)


def figure(values, title, changes=False):
    # Display sampling only: the scientific arrays and point queries stay at native resolution.
    step = max(1, int(np.ceil(max(values.shape)/650)))
    z = values[::step, ::step]
    xs = transform.c + (np.arange(0, values.shape[1], step)+.5)*transform.a
    ys = transform.f + (np.arange(0, values.shape[0], step)+.5)*transform.e
    fig = go.Figure(go.Heatmap(z=z, x=xs, y=ys, zmin=-6 if changes else -30, zmax=6 if changes else 0, colorscale="RdBu" if changes else "Viridis", colorbar={"title":"dB"}, hoverongaps=False))
    fig.update_layout(title=title, xaxis_title=f"Este (m) · {crs}", yaxis_title="Norte (m)", height=540, margin={"l":45,"r":15,"t":45,"b":40})
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


if mode == "Antes y después":
    left, right = st.columns(2)
    left.plotly_chart(figure(a, labels[before]+" · "+pol), width="stretch")
    right.plotly_chart(figure(b, labels[after]+" · "+pol), width="stretch")
else:
    st.plotly_chart(figure(delta, f"{labels[after]} − {labels[before]}", True), width="stretch")
    st.caption("Positivo: mayor retrodispersión en la fecha final. Escala visual limitada a ±6 dB; no es umbral de clasificación.")
st.subheader("Serie temporal de un punto")
west, south, east, north = manifest["bbox_wgs84"]
c1, c2 = st.columns(2)
lon = c1.number_input("Longitud WGS84", min_value=float(west), max_value=float(east), value=(west+east)/2, format="%.5f")
lat = c2.number_input("Latitud WGS84", min_value=float(south), max_value=float(north), value=(south+north)/2, format="%.5f")
x, y = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(lon, lat)
row, col = rasterio.transform.rowcol(transform, x, y)
rows = []
for scene in scenes:
    values, t, c = read_layer(str(root/scene["products"][pol]))
    if t != transform or c != crs or values.shape != a.shape:
        st.error("Serie interrumpida por grilla incompatible.")
        st.stop()
    value = float(values[row, col]) if 0 <= row < values.shape[0] and 0 <= col < values.shape[1] else np.nan
    rows.append({"fecha":scene["fecha_observacion"], "dB":value, "granulo":scene["granulo"]})
frame = pd.DataFrame(rows)
st.plotly_chart(go.Figure(go.Scatter(x=frame.fecha, y=frame.dB, mode="lines+markers", connectgaps=False)).update_layout(yaxis_title=f"{pol} (dB)", xaxis_title="Adquisición UTC"), width="stretch")
st.download_button("Descargar serie CSV", frame.to_csv(index=False), "sarwatch-serie.csv", "text/csv")
with st.expander("Tiempo meteorológico · complemento opcional"):
    st.caption("Open-Meteo · CC BY 4.0. El histórico ERA5 es reanálisis en una grilla mucho más gruesa que SAR; el pronóstico es una estimación futura, no una medición NISAR.")
    weather_mode = st.radio("Información meteorológica", ["Histórico del período SAR", "Pronóstico de los próximos 7 días"])
    if st.button("Consultar meteorología del punto"):
        from weather import fetch_weather
        from datetime import date, timedelta

        @st.cache_data(ttl=3600, max_entries=32)
        def cached_weather(latitude, longitude, start, end):
            return fetch_weather(latitude, longitude, start, end)

        try:
            historical = weather_mode.startswith("Histórico")
            start = (date.fromisoformat(min(labels[before], labels[after]))-timedelta(days=7)).isoformat() if historical else None
            end = max(labels[before], labels[after]) if historical else None
            result = cached_weather(round(lat, 3), round(lon, 3), start, end)
            daily = result["payload"]["daily"]
            weather_frame = pd.DataFrame(daily).rename(columns={"time":"fecha"})
            st.dataframe(weather_frame, hide_index=True)
            st.caption(f"Tipo: {result['kind']} · Consulta UTC: {result['retrieved_utc']} · Unidades: {result['payload'].get('daily_units', {})}")
            st.download_button("Descargar meteorología y procedencia", json.dumps(result, ensure_ascii=False, indent=2), "sarwatch-weather.json", "application/json")
            st.markdown("[Fuente y modelos](https://open-meteo.com/) · [Licencia y condiciones](https://open-meteo.com/en/terms)")
        except Exception as exc:
            st.warning(f"Meteorología no disponible ({type(exc).__name__}). Las observaciones NISAR siguen disponibles; vuelve a consultar más tarde.")
with st.expander("Procedencia y límites científicos"):
    st.write(manifest["quality_status"])
    st.write("No se aplicó clasificación de agua, corrección hidrológica ni validación independiente. No se interpola entre fechas ausentes. Vista en coordenadas UTM nativas; mapa base geográfico y consulta con clic quedan para la siguiente etapa.")
    st.dataframe(frame, hide_index=True)
    st.json(manifest["scenes"][after])
st.caption("Proyecto independiente de Software Detective. NASA e ISRO son las fuentes de la misión; no se implica patrocinio ni respaldo.")
