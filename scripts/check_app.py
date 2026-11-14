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
# Evaluated detection layers: Chile change checkbox and Pantanal water layer selector, when products exist.
if any(x.label=='Mostrar cambio estadísticamente significativo' for x in app.checkbox):
    next(x for x in app.checkbox if x.label=='Mostrar cambio estadísticamente significativo').check().run(timeout=180)
    assert not app.exception, list(app.exception)
    assert any('Conradsen' in x.value for x in app.caption), 'Change layer must explain its test'
app.selectbox[0].set_value('Mundo · cobertura NISAR').run(timeout=240)
assert not app.exception, list(app.exception)
if Path('catalog/global/coverage_1deg.json').is_file():
    assert any('granulos' in x.value for x in app.caption), 'World view must describe the CMR index'
    assert app.dataframe, 'World view must list repeat geometries for the default point'
app.selectbox[0].set_value('Pantanal').run(timeout=180)
if any(x.label=='Capa de detección evaluada' for x in app.selectbox):
    layer=next(x for x in app.selectbox if x.label=='Capa de detección evaluada')
    layer.set_value(layer.options[1]).run(timeout=180)
    assert not app.exception, list(app.exception)
    assert any('F1' in x.value for x in app.caption), 'Water layer must show its evaluation'
    app.chat_input[0].set_value('¿Cuánta agua hay?').run(timeout=180)
    assert not app.exception, list(app.exception)
    assert any('km²' in x.value for x in app.markdown), 'Assistant must quantify water from the evaluated reference'
# Heat view: GOES thermal cells crossed with NISAR, when thermal products exist for the region.
heat = "skipped"
if any(x.label=='Qué quieres mirar' for x in app.button_group):
    topic=next(x for x in app.button_group if x.label=='Qué quieres mirar')
    topic.set_value('Calor y focos · térmico + radar').run(timeout=180)
    assert not app.exception, list(app.exception)
    assert any('GOES-19' in x.value for x in app.caption), 'Heat view must name its thermal sensor'
    assert any('no hablamos de riesgo' in x.value for x in app.markdown), 'Heat view must state what it cannot claim'
    layer=next(x for x in app.selectbox if x.label=='Capa del mapa')
    for option in layer.options:
        layer.set_value(option).run(timeout=180)
        assert not app.exception, (option, list(app.exception))
    period=next(x for x in app.selectbox if x.label=='Período')
    period.set_value(period.options[-1]).run(timeout=180)
    assert not app.exception, list(app.exception)
    next(x for x in app.button_group if x.label=='Qué quieres mirar').set_value('Cambio de superficie · radar').run(timeout=180)
    assert not app.exception, list(app.exception)
    heat = "passed"
print(json.dumps({"app":"passed", "heat_view":heat, "difference":"passed", "polarization":"passed", "weather_outage":"passed"}))
