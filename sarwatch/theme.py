"""Visual treatment: the blue-to-orange radar scale is the identity; everything else stays quiet."""
import streamlit as st

LOW, NEUTRAL, HIGH = "#205b87", "#f2f2e8", "#c6601c"  # same stops as the map colour scale in sarwatch/maps.py

CSS = """<style>
.block-container {max-width: 1480px; padding-top: 2rem; padding-bottom: 4rem;}
h1 {font-size: 3.4rem !important; font-weight: 700 !important; letter-spacing: -.04em; line-height: .95; padding: 0 !important;}
h2, h3 {letter-spacing: -.02em; font-weight: 650 !important;}
h4 {font-weight: 600 !important; letter-spacing: -.01em;}
.sw-tagline {font-size: 1.05rem; max-width: 34rem; margin: .5rem 0 0; color: #3d5563;}
.sw-rule {height: 6px; margin: 1.1rem 0 1.6rem; border-radius: 3px; background: linear-gradient(90deg, #205b87, #f2f2e8 50%, #c6601c);}
.sw-scale {margin: .2rem 0 .7rem; max-width: 30rem;}
.sw-scale-bar {height: 12px; border-radius: 2px; border: 1px solid #d4dcd9; background: linear-gradient(90deg, #205b87, #f2f2e8 50%, #c6601c);}
.sw-scale-labels {display: flex; justify-content: space-between; font-size: .82rem; color: #3d5563; margin-top: .25rem;}
.sw-evidence {border-left: 3px solid var(--sw-level); padding: .1rem 0 .1rem .85rem; margin: 0 0 .95rem;}
.sw-evidence .sw-level {display: block; font-size: .85rem; font-weight: 700; color: var(--sw-level);}
.sw-evidence p {margin: .1rem 0 0; line-height: 1.45;}
[data-testid="stMetric"] {background: #fff; padding: .9rem 1.1rem; border: 1px solid #d4dcd9; border-radius: 4px;}
[data-testid="stMetricValue"] {font-family: 'Bricolage Grotesque', sans-serif; font-weight: 650; letter-spacing: -.02em;}
[data-testid="stExpander"] details {background: #fff; border-color: #d4dcd9;}
[data-testid="stAlert"] {background: #e7ece9; color: #10293a; border: 0; border-left: 3px solid #205b87; border-radius: 2px;}
[data-testid="stAlert"] p {color: #10293a;}
[data-testid="stSidebar"] {border-right: 1px solid #d4dcd9;}
iframe[title="streamlit_folium.st_folium"] {border: 1px solid #d4dcd9; border-radius: 4px;}
:focus-visible {outline: 2px solid #c6601c; outline-offset: 2px;}
</style>"""


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def header():
    """Title block; the rule under it is the colour scale used by every map."""
    st.title("SARWatch")
    st.markdown("<p class='sw-tagline'>Cómo cambia la superficie de la Tierra entre dos pasadas del radar NISAR, y qué se puede afirmar con eso.</p>", unsafe_allow_html=True)


def rule():
    st.markdown("<div class='sw-rule' role='presentation'></div>", unsafe_allow_html=True)


def scale_legend(changes):
    """Legend for the map overlay: difference between dates, or backscatter of one date."""
    labels = ("La señal bajó", "Casi sin cambio", "La señal subió") if changes else ("Poca respuesta: agua calma, superficies lisas", "", "Mucha respuesta: ciudad, vegetación densa")
    spans = "".join(f"<span>{label}</span>" for label in labels)
    st.markdown(f"<div class='sw-scale'><div class='sw-scale-bar' role='img' aria-label='Escala de color de azul a naranja'></div><div class='sw-scale-labels'>{spans}</div></div>", unsafe_allow_html=True)
