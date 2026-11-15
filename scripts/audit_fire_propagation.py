"""Generate a traceable propagation-readiness report from existing evidence, without fake inputs."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.propagation import audit_spread_inputs

if __name__ == "__main__":
    pack = Path("catalog/fire_story/story.json")
    story = json.loads(pack.read_text(encoding="utf-8"))
    # Context stays separate; dated official perimeters support a late-period research experiment.
    inputs={}
    perimeter_path=Path("catalog/official_fire_perimeters/manifest.json")
    if perimeter_path.is_file():
        perimeter=json.loads(perimeter_path.read_text(encoding="utf-8"))
        if len(perimeter["products"])>1:
            for key in ("initial_perimeter","validation_perimeters"):
                inputs[key]={"qualified_for_spread":True,"source":perimeter["source_url"],"units":"geometry_utc",
                    "time_reference":"2026-01-21/2026-01-25; no cubre el avance inicial 17–18",
                    "grid_reference":"EPSG:4326; originales georreferenciados",
                    "sha256":hashlib.sha256(perimeter_path.read_bytes()).hexdigest()}
    report = audit_spread_inputs(inputs)
    report.update({"generated_utc": datetime.now(timezone.utc).isoformat(),
                   "story_sha256": hashlib.sha256(pack.read_bytes()).hexdigest(),
                   "available_context": ["GOES-19: celdas térmicas horarias, no perímetros",
                       "ERA5: viento y humedad del aire en rejilla gruesa",
                       "DEM Copernicus y WorldCover agregados por celda",
                       "NISAR: observaciones posteriores al incendio de enero", "Copernicus EMSR859: delimitaciones oficiales del 21 al 25 de enero; originales verificados por SHA256"],
                   "existing_model": {"name": story["before"]["model"],
                       "target": "Prioridad de vigilancia de detecciones térmicas, no trayectoria del fuego",
                       "horizon_days": story["before"]["horizon_days"],
                       "evaluation": story["before"]["benchmark"]},
                   "sources": ["https://research.fs.usda.gov/treesearch/55928",
                       "https://owfflammaphelp62.firenet.gov/millerTutorials/miller-Input_a_FARSITE_Simulation.htm"]})
    Path("catalog/fire_propagation_readiness.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(report["status"])
