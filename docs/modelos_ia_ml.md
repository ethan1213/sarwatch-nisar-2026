# Modelos de IA y ML para SARWatch — inventario, veredicto y orden de uso

Fecha: 14 noviembre 2026. Decisiones del propietario: sin API de Claude en el producto (solo modelos locales); entrenamiento tabular en la laptop (i5 de 4 núcleos, 16 GB RAM, sin GPU CUDA) y deep learning en Google Colab gratuito; Pantanal (inundación) y Chile urbano (cambio) en paralelo.

Regla que gobierna todo el inventario: **los números salen del procesamiento científico; ningún modelo de lenguaje produce cifras**. Cada modelo entra al visor solo después de publicar su métrica en un conjunto retenido (bloques espaciales y fechas separadas) y su tarjeta de modelo.

## 1. Detección de agua y cambio en SAR

| Modelo / método | Para qué | Dónde corre | Veredicto |
|---|---|---|---|
| Umbral bimodal Otsu / Kittler-Illingworth sobre HH dB (y HV) | Agua abierta por escena; línea base interpretable | Laptop (scikit-image) | **Fase 2, primero.** Barato, explicable, publicable como baseline |
| Log-ratio de cambio + Otsu + prueba de bimodalidad | Máscara de cambio entre fechas con umbral justificado | Laptop | **Fase 2.** Sustituye la "diferencia visual" |
| Máscara HAND / pendiente desde DEM Copernicus GLO-30 | Excluir sombra radar y zonas donde no puede haber agua | Laptop (rasterio, numpy) | **Fase 1.** Reduce falsos positivos clásicos |
| LightGBM / Random Forest por píxel (HH, HV, HH−HV, diferencia, textura local, pendiente, HAND, ocurrencia JRC, distancia a drenaje) | Clasificador supervisado agua/no agua y cambio/no cambio con etiquetas ópticas | Laptop (minutos) | **Fase 2, modelo principal v1.** Tabular, rápido, con importancia de variables |
| Prueba de cambio polarimétrico de Conradsen (estadístico Wishart sobre la covarianza GCOV HHHH/HVHV/HHHV) | Cambio con significación estadística usando el producto completo | Laptop | **Fase 2 (Chile).** El GCOV ya es una matriz de covarianza; es el método nativo del producto |
| Cambio de punto por píxel (CUSUM / segmentación binaria, implementación propia en numpy; `ruptures` no compila en Python 3.14) | Fecha en que cambia cada píxel en la serie Pantanal | Laptop | **Fase 3.** Requiere ≥ 7 fechas; Pantanal ya las tiene |
| U-Net / SegFormer entrenados en Sen1Floods11, Kuro Siwo, UrbanSARFloods | Segmentación de inundación con deep learning | Colab T4 entrena; laptop infiere por ONNX Runtime | **Fase 4.** Solo si supera a LightGBM en bloques retenidos |
| Foundation models EO con Sentinel-1: TerraMind 1.0 (IBM/ESA), Clay v1.5, Galileo (Ai2), DOFA; Prithvi-EO-2.0 (NASA/IBM, óptico) | Inicialización con pocas etiquetas; fine-tuning con TerraTorch | Colab T4 | **Fase 4.** Entrenados en banda C; NISAR es banda L: usar como inicialización y **medir** la transferencia. Prithvi-EO-2.0 sirve para etiquetas ópticas, no como backbone SAR |
| Filtro de speckle (Lee refinado, multitemporal) | Limpiar antes de umbralizar | Laptop | Fase 2, opcional; GCOV ya es multilook, medir si mejora F1 |

## 2. Etiquetas y covariables (sin ellas no hay modelo validado)

| Fuente | Aporta | Acceso |
|---|---|---|
| Sentinel-2 L2A (MNDWI) | Máscara de agua contemporánea a cada fecha NISAR (±3 días, nubes < 20 %) | Microsoft Planetary Computer STAC, sin cuenta |
| JRC Global Surface Water | Ocurrencia y recurrencia de agua: permanente vs. estacional | Planetary Computer |
| Copernicus DEM GLO-30 | Pendiente, HAND, sombra | Planetary Computer |
| ESA WorldCover 10 m | Clase de superficie para métricas por tipo | Planetary Computer |
| GloFAS caudal (Open-Meteo Flood API) | Covariable hidrológica | HTTP sin clave; grilla gruesa, validar tramo |
| ERA5 lluvia antecedente (Open-Meteo archive) | Covariable meteorológica | Ya implementado en `weather.py` |
| OpenStreetMap / Microsoft Building Footprints | Edificaciones Santiago y Valparaíso | Overpass; GeoJSON |
| Sen1Floods11, Kuro Siwo, UrbanSARFloods, UFO | Preentrenar y validar segmentación | Descarga pública en Colab |

## 3. Pronóstico

| Modelo | Objetivo | Veredicto |
|---|---|---|
| Persistencia (MAE 0,45 dB en Pantanal, 4 evaluaciones) | Referencia mínima | Baseline obligatoria en cada comparación |
| Climatología estacional / mediana móvil | Segunda referencia | Fase 3 |
| Ridge / Lasso con lluvia antecedente, caudal GloFAS, valor previo | Área inundada o mediana dB a 12 días | **Fase 3, primer modelo real.** Interpretable; cabe en 7–10 fechas |
| LightGBM con rezagos + regresión cuantílica | Mismo objetivo con intervalos | Fase 3 |
| Predicción conforme (MAPIE) | Intervalos con cobertura garantizada | **Obligatoria** antes de mostrar un pronóstico |
| Regresión logística / LightGBM binario | Probabilidad de superar un umbral; Brier y calibración | Fase 3 |
| ConvLSTM y modelos temporales profundos | Pronóstico por píxel | **No ahora.** Insuficientes eventos; revisar con ≥ 30 fechas y varios eventos |

Regla de publicación: un pronóstico se muestra solo si supera a la persistencia en origen rodante y sus intervalos cubren ≥ 80 % en validación. Si no, el visor lo dice.

## 4. Asistente local

| Componente | Opción | Peso | Veredicto |
|---|---|---|---|
| Enrutador de intención | TF-IDF + regresión logística (scikit-learn) con ~200 preguntas | < 1 MB | Fase 5; reemplaza listas de palabras clave |
| Recuperador | BM25 sobre `docs/` y glosario (`rank_bm25`) | 0 | Fase 5 |
| Embeddings | `multilingual-e5-small` en ONNX (CPU) | ~470 MB | Fase 5, opcional si BM25 no basta |
| Redactor generativo | Qwen3-4B-Instruct-2507 Q4_K_M vía Ollama; alternativas Qwen3-1.7B, Gemma 3 4B, Llama 3.2 3B | ~2,5 GB disco, 4–5 GB RAM | Fase 5, detrás de la bandera `ASSISTANT_LLM=ollama` |
| Verificador | Cada número debe existir en el JSON de herramientas y cada cita en el índice; si falla, responde el motor de reglas | 0 | **Obligatorio** |
| Claude API | Excluida por decisión del propietario | — | Punto de enganche documentado, no implementado |

## 5. Comprensión para todos los públicos

Diccionario ES/EN propio; NLLB-200 destilado (Colab) solo para generar diccionarios adicionales una vez; Piper TTS local opcional; pruebas automáticas de contraste y teclado con axe-core. Ninguna prueba automática sustituye pruebas con personas reales de los cinco perfiles.

## 6. Escala mundial

No es un modelo: catálogo STAC interno + COG + teselas + procesamiento por área bajo demanda. Se demuestra con un cuarto AOI medido en tiempo, RAM y bytes. La compresión real de los COG actuales se mide y se incorpora a la calculadora, que hoy supone float32 sin comprimir como cota superior.

## 7. Memoria y disco esperados en la laptop

| Elemento | Disco | RAM |
|---|---|---|
| LightGBM agua/cambio por AOI | < 5 MB | < 200 MB |
| Segmentación ONNX | 100–400 MB | 1–2 GB por ventanas |
| Qwen3-4B Q4_K_M | ~2,5 GB | 4–5 GB |
| Etiquetas y covariables, 3 AOI | 1–2 GB | — |
| 4 pares HDF5 Chile adicionales | ~15 GB | fuera de Git |

## 8. Herramientas de desarrollo (Claude Code)

Claude no forma parte del producto. Como herramienta de construcción: Fable 5.1 para contratos científicos, protocolo de splits/métricas y revisión de afirmaciones; Opus 5 para pipelines numéricos (etiquetas, LightGBM, Wishart, pronóstico, notebooks, ONNX) y el verificador del asistente; Sonnet 5 para vistas, i18n, pruebas y Docker; Haiku 4.5 para generar preguntas de evaluación, glosario y limpieza mecánica, siempre revisado. Si una prueba falla dos veces en el mismo módulo, la tarea sube de modelo.

## 9. Implementado en la Fase 0

- `sarwatch/ml/features.py`: firma de grilla, apilado de capas con máscara común, textura local, pendiente, razón HH−HV.
- `sarwatch/ml/splits.py`: bloques espaciales con buffer, detección del reparto aleatorio de píxeles, holdout temporal y origen rodante.
- `sarwatch/ml/metrics.py`: precisión/recall/F1/IoU por grupo, MAE/sesgo/RMSE, skill, Brier, calibración, cobertura de intervalos.
- `sarwatch/ml/experiments.py`: registros JSON con versiones y SHA de Git en `experiments/` (fuera de Git).
- `requirements-ml.txt` separado del runtime web. `ruptures` quedó fuera por no compilar en Python 3.14.

## Fuentes

- Foundation models EO: https://arxiv.org/html/2607.07758v1 · https://github.com/Jack-bo1220/Awesome-Remote-Sensing-Foundation-Models · https://arxiv.org/pdf/2601.02315
- Datasets de inundación SAR: https://proceedings.neurips.cc/paper_files/paper/2024/file/43612b0662cb6a4986edf859fd6ebafe-Paper-Datasets_and_Benchmarks_Track.pdf · https://www.alphaxiv.org/abs/2406.04111v1 · https://arxiv.org/html/2604.23066 · https://arxiv.org/html/2504.19526v4
- Transferencia Sentinel-1 → NISAR: https://github.com/cs59300-deep-learning/nisar-flood-mapping · https://github.com/davnish/nisar-surface-water-bihar
- Conradsen et al., prueba de cambio para datos polarimétricos (Wishart), IEEE TGRS 2003 y 2016.
- NASA SBIR/STTR 2026–2027: https://www.nasa.gov/wp-content/uploads/2024/01/nasa-2026-2027-sbir-sttr-baa-appendix-26a-i-sbir.pdf
