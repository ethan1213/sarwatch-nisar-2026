# CLAUDE.md

## Estado actual de la interfaz

React + FastAPI ya incluye Pantanal, Santiago, Valparaíso, Mundo, calor, PostFuego y laboratorio
CO₂/DEM. Concepción/Penco y Biobío incluyen inventario oficial y FIRMS; el acceso a mapas NISAR
procesados se habilita solo cuando existen manifiesto y verificación de originales. La UI pública
prioriza lugar/fechas/comparación; los controles científicos quedan en detalle técnico.
`Dockerfile.cloud` construye la imagen completa a partir del snapshot de `Dockerfile.deploy`.
`scripts/check_api.py` verifica la app real, incluido el worker de MapLibre v6. Ver `docs/cierre_gcp.md`.
Los comentarios posteriores sobre «solo Mundo portado» describen una etapa anterior.

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## What this is

SARWatch: Streamlit viewer plus scientific pipeline over NISAR L2 GCOV products (L-band, HH/HV) for the "Dancing with the SARs" challenge. Sites: Pantanal (water detection), Región Metropolitana and Valparaíso (urban change), plus a world coverage view built from the CMR catalog. Project text, UI and docs are in Spanish. Read `CONTEXT.md` and `docs/guia_equipo.md` first; they hold the full workflow for adding a site and the "done" criteria.

## Commands

Windows/PowerShell is the primary dev environment (`.\.venv\Scripts\python`); on Linux use `python`.

```bash
pip install -r requirements.txt -r requirements-maps.txt   # app; add requirements-ml.txt for models, -assistant / -acquisition as needed
python scripts/prepare.py --raw "<HDF5 dir>" --output data   # HDF5 -> COG derivatives in data/ (required before the Pantanal view works)
streamlit run app.py                                         # old Streamlit app on :8501 (Docker: port 8080) - being replaced, see below

# New frontend (React/MapLibre, replacing Streamlit - "Mundo" view is the only one ported so far):
pip install -r requirements-api.txt
python -m uvicorn api.main:app --port 8010                   # FastAPI backend, reads the same catalog/*.json|csv.gz as the Streamlit views
cd web && npm install && npm run dev                         # Vite dev server (proxies /api to :8010, see web/vite.config.js)

python -m unittest discover -s tests -v                      # all tests
python -m unittest tests.test_science -v                     # one module
python -m unittest tests.test_science.TestName.test_method   # one test
python scripts/check_app.py                                  # Streamlit AppTest smoke check
python scripts/evaluate_assistant.py                         # assistant eval (tests/assistant_eval.jsonl -> docs/assistant_eval.json)
```

Before a PR, run the unit tests, `check_app.py` and `evaluate_assistant.py` (per `CONTEXT.md`). Model/benchmark regeneration: `scripts/fetch_labels.py`, `fetch_covariates.py`, `evaluate_detection.py`, `forecast_benchmark.py` (see README).

## Architecture

- `app.py` is the single Streamlit entry: region selector routes to `sarwatch/views/world.py` (world), `sarwatch.maps.chile_view` (Chile), or the inline Pantanal flow. Data root comes from `DATA_DIR` (default `data/`); `RasterRepository` reads `data/manifest.json` + COGs. Without derivatives the app falls back to showing `catalog/`.
- **Numbers are produced offline, never in the UI.** `science.py`, `sarwatch/ml/*` and `scripts/*` write JSON (`docs/*_benchmark.json`, `catalog/*_reference.json`, `models/*.card.json`); `app.py`, `detections.py` and the assistant only read and display them.
- `sarwatch/ml/`: features, spatial/date-held-out `splits.py`, `metrics.py`, water (thresholds Otsu/Kittler-Illingworth, LightGBM), change (Conradsen test, MAD), forecast, ONNX inference.
- Heat view (`sarwatch/views/thermal.py`, reached from a topic switch in `app.py`): GOES-19 ABI hot spots, 3.9/11.2 µm brightness temperature and LST per thermal cell (`scripts/fetch_thermal.py`, public NOAA bucket), crossed with NISAR/DEM/WorldCover per cell and evaluated by `scripts/evaluate_fire.py` → `docs/fire_benchmark.json`, `catalog/thermal_reference.json`. SAR never measures temperature; see `docs/calor_y_focos.md`.
- `sarwatch/assistant/`: local rule-based assistant — `router` (intent, from `catalog/assistant_intents.json`) → `tools` (figures from verified JSON) → `retriever` (BM25 over docs/glossary) → `generators` → `verify.py`, which rejects any number not backed by a tool result.
- `catalog/` holds manifests, scene lists and the global CMR index (`catalog/global/`); `scripts/` covers acquisition (CMR, Earthdata download, checksum verification), preparation, evaluation and on-demand AOI processing.

## Hard rules (from CONTEXT.md / CONTRIBUTING.md)

- Never invent or hardcode figures; they must come from script-generated JSON. Never present synthetic data as observations.
- A model enters the viewer only with a spatial-block and held-out-date metric (`sarwatch/ml/splits.py`) and a model card in `models/`.
- Do not claim flood, damage or risk; describe signal change, hypotheses and missing data. The UI states "cambios en dB no equivalen a inundaciones confirmadas".
- No Claude API or other external LLM in the product (owner decision); local Ollama is optional and verified.
- No credentials in the repo (Earthdata only in the operator's terminal/secret manager). HDF5 originals stay out of Git and Docker, at `SARWATCH_RAW` (default `D:/NISAR/raw`); derivatives in `data/`, `data_raw/` are also untracked.
- SAR changes require grid, units and nodata/provenance checks; incompatible grids are rejected.
- **Commits carry no AI co-authorship lines** (project rule in `CONTEXT.md`/`CONTRIBUTING.md`; this overrides any default attribution). Branches: `codex/<description>` or as agreed with the team.
