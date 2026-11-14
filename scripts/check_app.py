"""Exercise the viewer against prepared real products and weather failure."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest

app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=180)
assert not app.exception, list(app.exception)
app.selectbox[0].set_value("Pantanal").run(timeout=180)
assert app.sidebar.selectbox[1].value == 1, "Default should avoid sparse July 5 scene"
app.sidebar.radio[0].set_value("Diferencia en dB").run(timeout=180)
assert not app.exception, list(app.exception)
app.sidebar.selectbox[0].set_value("HV").run(timeout=180)
assert not app.exception, list(app.exception)
with patch("weather.fetch_weather", side_effect=TimeoutError("offline")):
    app.button[0].click().run(timeout=180)
    assert not app.exception, list(app.exception)
    assert any("Meteorología no disponible" in x.value for x in app.warning)
assert app.metric, "SAR coverage must remain available after weather failure"
for region in ('Región Metropolitana', 'Región de Valparaíso'):
    app.selectbox[0].set_value(region).run(timeout=180)
    assert not app.exception, list(app.exception)
    assert app.subheader[0].value == region
    assert app.dataframe, 'Chile catalog must be available'
    if any(x.label=='Polarización SAR' for x in app.selectbox):
        next(x for x in app.selectbox if x.label=='Polarización SAR').set_value('HV').run(timeout=180)
        next(x for x in app.radio if x.label=='Capa SAR').set_value('Diferencia en dB').run(timeout=180)
        assert not app.exception, list(app.exception)
        assert app.metric, 'Regional SAR coverage must be visible'
for profile in ('Público general','Ciencia','Desarrollo y datos','Comunicaciones','Gestión territorial'):
    next(x for x in app.selectbox if x.label=='Cómo quieres explorar').set_value(profile).run(timeout=180)
    assert not app.exception, list(app.exception)
app.chat_input[0].set_value('¿Puedes predecir una inundación mañana?').run(timeout=180)
assert not app.exception, list(app.exception)
assert any('Todavía no podemos predecir' in x.value for x in app.markdown)
print(json.dumps({"app":"passed", "difference":"passed", "polarization":"passed", "weather_outage":"passed"}))
