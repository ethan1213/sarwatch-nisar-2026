"""Exercise the viewer against prepared real products and weather failure."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest

app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=180)
assert not app.exception, list(app.exception)
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
print(json.dumps({"app":"passed", "difference":"passed", "polarization":"passed", "weather_outage":"passed"}))
