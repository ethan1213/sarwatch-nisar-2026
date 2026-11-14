# CONTEXT — SARWatch (NISAR, Space Apps 2026 «Dancing with the SARs»)

Resumen operativo para personas y asistentes de IA (Claude Code, Codex, Gemini). Si eres un asistente: lee esto, luego `docs/guia_equipo.md`, y no inventes cifras: todas salen de JSON generados por scripts.

## Qué es

Visor Streamlit + pipeline científico sobre productos NISAR L2 GCOV (banda L, HH/HV) que muestra y evalúa cambios de superficie: agua abierta en humedales (Pantanal, 9 fechas jul–oct 2026) y cambio urbano (Santiago y Valparaíso, 2 fechas oct 2026), más una vista mundial de cobertura construida desde el catálogo CMR (163 mil granulos, ~291 TB: no se descargan, se indexan).

## Reglas duras

1. Los números los producen `science.py`, `sarwatch/ml/*` y los scripts de `scripts/`; el asistente y la interfaz solo los muestran. El verificador (`sarwatch/assistant/verify.py`) rechaza cifras sin respaldo.
2. Nada entra al visor sin métrica en bloques espaciales y fechas retenidos (`sarwatch/ml/splits.py`) y tarjeta de modelo (`models/*.card.json`).
3. No afirmar inundación, daño ni riesgo; describir cambio de señal, hipótesis y datos ausentes.
4. Sin API de Claude ni LLM externos en el producto (decisión del propietario). Ollama local es opcional y verificado.
5. Credenciales Earthdata solo en la terminal del operador o en un gestor de secretos; HDF5 fuera de Git (`D:\NISAR\raw`, variable `SARWATCH_RAW`).
6. Commits sin líneas de coautoría de IA.

## Mapa del código

| Ruta | Qué hace |
|---|---|
| `app.py` | Flujo principal: selector de lugar, mapas, capas evaluadas, serie de punto, asistente |
| `sarwatch/maps.py`, `sarwatch/detections.py`, `sarwatch/views/` | Mapas, capas evaluadas, tablero de evidencia, vista mundial |
| `sarwatch/guidance.py`, `sarwatch/interpretation.py` | Lectura guiada por perfil, resúmenes, calculadora de escala |
| `sarwatch/assistant/` | Enrutador de intención, herramientas con cifras, BM25, generadores, verificador |
| `sarwatch/ml/` | Features, splits, métricas, agua (umbrales, LightGBM), cambio (Conradsen, MAD), pronóstico, inferencia ONNX, térmico GOES (`thermal.py`) y su cruce con NISAR por celda (`fire.py`) |
| `sarwatch/views/thermal.py` | Vista «Calor y focos»: celdas térmicas GOES-19 con radar, pendiente y cobertura; ver `docs/calor_y_focos.md` |
| `scripts/` | Adquisición (CMR, descarga, verificación), preparación (COG), etiquetas y covariables, evaluaciones, índice mundial, AOI bajo demanda |
| `catalog/` | Manifiestos, referencias que lee la app (`*_reference.json`), glosario, intenciones, índice mundial |
| `docs/` | Estado, inventario de modelos, benchmarks JSON, arquitectura, nube, estrategia, guía de equipo, pruebas de usuario |
| `tests/` | 51 pruebas unitarias + `scripts/check_app.py` (AppTest) + `tests/assistant_eval.jsonl` |

## Cómo verificar antes de un PR

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python scripts/check_app.py
.\.venv\Scripts\python scripts/evaluate_assistant.py
```

## Resultados vigentes (ver JSON para detalle)

Agua Pantanal (9 fechas, 8 etiquetadas): LightGBM F1 0,83 en bloques retenidos y 0,76 en la fecha retenida (21 oct); Kittler-Illingworth 0,68; Otsu 0,10. Cambio Chile: < 0,2 % de tierra con cambio significativo; 11 % sobre el mar por viento. Pronóstico: la climatología supera a la persistencia en la mediana HH (MAE 0,37 frente a 0,44 dB) y se muestra como referencia; en área de agua nada supera a la persistencia. Calor y focos (GOES-19, 1 jul–13 nov): 41 detecciones en Pantanal (7 confiables), 10 de probabilidad baja en la Región Metropolitana, 0 en Valparaíso; con eso no se puede evaluar respuesta del radar ni anticipación, y no se muestra predicción. Sitio con focos y pasadas NISAR: Araucanía, marzo–abril 2026 (`catalog/araucania_candidates.json`). Asistente: 60/60. COG float32 ocupan 1,03× su tamaño sin comprimir.

## Qué falta (resumen)

Licencia y repositorio abierto; sitios en otros continentes y otros tipos de cambio (incendio, glaciar); generalización del modelo entre humedales; animación temporal; inglés y accesibilidad; pruebas con personas; app pública (Cloud Run) y procesamiento junto a los datos (Lambda us-west-2). Orden y criterios en `docs/guia_equipo.md`.
