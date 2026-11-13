import json
from pathlib import Path
from datetime import datetime
catalog = json.loads((Path(__file__).resolve().parents[1] / "catalog/scenes.json").read_text(encoding="utf-8"))
scenes = catalog["scenes"]
assert len(scenes) == 7
assert len({s["id"] for s in scenes}) == len(scenes)
for scene in scenes:
    assert datetime.fromisoformat(scene["fecha_observacion"].replace("Z", "+00:00")).year == 2026
    assert scene["url_hdf5"].startswith("https://nisar.asf.earthdatacloud.nasa.gov/")
    assert len(scene["sha256"]) == 64
    assert len(scene["md5_calculado"]) == 32
    assert scene["tamano_bytes"] > 0
print("Catálogo comprobado: 7 escenas reales identificadas, año 2026.")
