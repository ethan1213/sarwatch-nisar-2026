"""Shared presentation components: evidence board, story entry and plain-language legends."""
import json
from pathlib import Path

import streamlit as st

EVIDENCE_LEVELS = {"observado": ("Observado", "#1f6f8b"), "estimado": ("Estimado y evaluado", "#b8860b"), "hipotesis": ("Hipótesis", "#8a5a2b"), "ausente": ("Dato ausente", "#7a7a7a")}
AOI_SLUGS = {"Pantanal": "pantanal", "Región Metropolitana": "metropolitana", "Región de Valparaíso": "valparaiso"}


def _load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MODEL_NAMES = {"climatology": "promedio de las fechas anteriores", "persistence": "repetir el valor anterior", "ridge": "regresión lineal"}


def short_date(iso):
    """'2026-10-05' -> '5 oct 2026'; anything else is returned unchanged."""
    try:
        year, month, day = (int(part) for part in iso[:10].split("-"))
        return f"{day} {MONTHS[month - 1]} {year}"
    except (ValueError, IndexError):
        return iso


def percent(fraction, digits=0):
    return f"{100 * fraction:.{digits}f}".replace(".", ",") + " %"


def evidence_board(items):
    """items: list of (level, text). Each entry is labelled with how much we know about it."""
    for level, text in items:
        label, color = EVIDENCE_LEVELS[level]
        st.markdown(f"<div class='sw-evidence' style='--sw-level:{color}'><span class='sw-level'>{label}</span><p>{text}</p></div>", unsafe_allow_html=True)


def story(region, before, after, polarization, statistics, profile):
    """Place -> dates -> what changed -> what it may mean -> what we do not know."""
    detection = _load("catalog/detection_reference.json") or {}
    forecast = _load("catalog/prediction_reference.json") or {}
    slug = AOI_SLUGS.get(region, region)
    st.markdown(f"#### {short_date(before)} → {short_date(after)}")
    items = []
    if statistics.get("median_db") is None:
        items.append(("ausente", "No hay píxeles comparables entre estas fechas; no describimos el cambio."))
    else:
        move = "aumentó" if statistics["median_db"] > 0 else "disminuyó" if statistics["median_db"] < 0 else "se mantuvo"
        items.append(("observado", f"La respuesta típica del radar ({polarization}) {move}: diferencia mediana {statistics['median_db']:+.2f} dB sobre el {percent(statistics['coverage'])} del recorte con dato válido en ambas fechas."))
    water = (detection.get("water") or {}).get(slug)
    if water:
        area = next((a for a in water["areas"] if a["date"] == after), None)
        lg = water["lightgbm"]
        if area and area.get("lightgbm_km2") is not None:
            items.append(("estimado", f"Agua abierta estimada el {after}: {area['lightgbm_km2']:.1f} km² (clasificador evaluado contra Sentinel-2: F1 {lg['spatial_f1']:.2f} en bloques retenidos, {lg['temporal_f1']:.2f} en la fecha retenida). No incluye agua bajo vegetación."))
    change = (detection.get("change") or {}).get(slug)
    if change:
        land = change["land"]
        pct = 100 * ((land.get("increase") or 0) + (land.get("decrease") or 0))
        items.append(("estimado", f"El {percent(pct / 100, 2)} de los píxeles de tierra cambió de forma estadísticamente significativa entre ambas fechas (prueba de Conradsen, α = {change['alpha']}). Sobre el mar y embalses el cambio refleja viento y oleaje."))
    items.append(("hipotesis", "Un cambio de señal puede deberse a humedad, vegetación, construcción, viento sobre el agua o geometría. La causa no se confirma con radar solo."))
    decision = forecast.get("best_model") or {}
    if decision.get("publishable"):
        items.append(("estimado", f"Pronóstico de referencia disponible para la mediana del recorte ({MODEL_NAMES.get(decision['model'], decision['model'])}); no es un pronóstico de inundación."))
    else:
        items.append(("ausente", "No hay pronóstico publicable: ningún modelo superó a repetir el valor anterior con intervalos calibrados. No anticipamos inundaciones ni daños."))
    items.append(("ausente", "Falta validación con observaciones de terreno y pruebas con personas de cada perfil."))
    evidence_board(items)
    if profile == "Comunicaciones":
        st.caption("Qué puedes afirmar: lo marcado como observado y estimado, citando la métrica. Qué no: causas, inundaciones confirmadas o riesgo futuro.")
    elif profile == "Gestión territorial":
        st.caption("Uso sugerido: orientar dónde revisar en terreno. No es una alerta operativa ni delimita daños.")


def color_legend(changes):
    if changes:
        st.caption("Azul: la señal bajó respecto de la primera fecha. Naranja: subió. Claro: casi sin cambio. Transparente: sin dato.")
    else:
        st.caption("Oscuro: poca respuesta del radar (agua calma, superficies lisas). Claro y naranja: mucha respuesta (ciudad, vegetación densa). Transparente: sin dato.")
