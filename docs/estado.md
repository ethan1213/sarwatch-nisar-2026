# Estado de entrega — 14 noviembre 2026

## Actualización: modelos evaluados, asistente verificado y pronóstico honesto

Decisiones del propietario (14 nov): sin API de Claude en el producto; entrenamiento en la laptop y Colab; Pantanal y Chile en paralelo. Plan aprobado en ocho fases; inventario completo de modelos en [modelos_ia_ml.md](modelos_ia_ml.md).

**Etiquetas y covariables (Fase 1).** Sentinel-2 L2A vía Planetary Computer: agua óptica MNDWI > 0 para 6 de 7 fechas de Pantanal (el 5 de julio no tiene imagen sin nubes en ±3 días) y 1 de 2 fechas en cada recorte chileno. Covariables en la grilla NISAR: DEM Copernicus 30 m, pendiente, proxy de HAND, ocurrencia y estacionalidad JRC, WorldCover 2021. Pantanal: 67 % humedal herbáceo, 28 % árboles, 4 % agua permanente. CMR muestra dos escenas nuevas de Pantanal con la misma geometría (9 y 21 de octubre) en `catalog/pantanal_candidates.json`; su descarga requiere Earthdata Login interactivo (`scripts/download_scenes.py`).

**Detección observada (Fase 2).** Evaluación contra etiquetas ópticas en bloques espaciales retenidos de 64×64 px con anillo de separación, y en la última fecha retenida:

| Método | F1 (bloques) | F1 (fecha retenida 2026-09-27) | Comentario |
|---|---:|---:|---|
| Umbral Otsu HH | 0,10 medio en 6 fechas | — | Separa modos de tierra; con 1,5 % de agua no sirve |
| Umbral Kittler-Illingworth HH | 0,65 medio en 6 fechas | — | Baseline interpretable razonable |
| LightGBM por píxel (HH, HV, textura, terreno, JRC) | **0,83** (IoU 0,70) | **0,80** | Por clase: agua permanente 0,88; humedal herbáceo 0,43; árboles 0,25 |

Área de agua abierta estimada en Pantanal: 55–56 km² estables en las seis fechas (etiqueta óptica 37–53 km²; el 3 de septiembre la etiqueta tiene 62 % de cobertura por nubes). Importancia: HH 85 %. Máscaras en `data/detections/`, tarjeta en `models/pantanal_water_lgbm.card.json`. Las etiquetas son agua abierta óptica: el agua bajo vegetación no está evaluada.

Chile: prueba de cambio de Conradsen (forma diagonal HH/HV, looks del producto ≈ 9–10, α = 0,01). Tierra: 0,18 % de píxeles con cambio significativo en Santiago y 0,06 % en Valparaíso; sobre el mar de Valparaíso 11,3 % de aumento, atribuible a viento y oleaje. Sin etiquetas de cambio urbano no se reporta exactitud; el acuerdo con el umbral MAD es bajo (IoU 0,27 y 0,16), lo que indica que ambos métodos miden cosas distintas y se necesita referencia independiente.

**Pronóstico (Fase 3).** `scripts/forecast_benchmark.py` en origen rodante con lluvia ERA5 y caudal GloFAS como covariables: la persistencia gana (MAE 0,65 dB en la mediana HH; 0,23 km² en área de agua). Ridge y climatología son peores. **No se publica ningún pronóstico**; el visor y el asistente lo dicen explícitamente. La regla de publicación exige superar a la persistencia y cobertura de intervalos ≥ 80 %.

**Asistente local (Fase 5).** Enrutador TF-IDF + regresión logística (225 ejemplos, 12 intenciones), herramientas con cifras, recuperador BM25 sobre `docs/` y glosario (`catalog/glosario.json`), verificador que rechaza números sin respaldo, enlaces no citados y frases prohibidas. Evaluación `tests/assistant_eval.jsonl`: 60/60 casos; intención 100 %, trazabilidad 100 %, abstención y seguridad 100 % (`docs/assistant_eval.json`). Generador Ollama opcional (`ASSISTANT_LLM=ollama`), no instalado ni probado en este equipo.

**Vistas (Fase 6, parcial).** Tablero de evidencia (observado / estimado / hipótesis / dato ausente) al inicio de cada lugar; capas evaluadas en el mapa con su métrica; tabla por cobertura para Ciencia. Pendientes: multipágina, ES/EN, axe-core y pruebas con personas (`pruebas_usuarios.md`).

**Escala y estrategia (Fases 7–8, parcial).** `scripts/request_aoi.py` selecciona y prepara un AOI nuevo midiendo tiempo y compresión; falta ejecutarlo con un cuarto AOI (requiere descarga autenticada). `estrategia_comercial.md` documenta que SBIR/STTR exige empresa estadounidense y propone rutas realistas.

Verificación: 47 pruebas unitarias; `scripts/check_app.py` recorre Pantanal, Chile, perfiles, chat, capa de cambio y capa de agua. Imagen Docker: pendiente de reconstruir con `requirements-assistant.txt`.

## Actualizaciones anteriores

Ver historial de Git para el estado del 13 de noviembre (descarga verificada de Chile, mapas, perfiles, chat por reglas y benchmark de persistencia).
