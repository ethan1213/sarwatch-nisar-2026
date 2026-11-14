# Guía para el equipo — qué hay, qué falta y cómo terminarlo

Fecha: 14 noviembre 2026. Para Software Detective (seis personas). Léela antes de tocar el código. Complementa [CONTEXT.md](../CONTEXT.md) (resumen para humanos y asistentes de IA), [estado.md](estado.md) (verificaciones), [modelos_ia_ml.md](modelos_ia_ml.md) (inventario de modelos) y [arquitectura_nube.md](arquitectura_nube.md) / [nube_capas_gratuitas.md](nube_capas_gratuitas.md).

## 1. Qué pide el desafío y cómo lo cubrimos

"Dancing with the SARs" pide una **app interactiva abierta** que use datos NISAR para **rastrear y visualizar uno o más tipos de cambio de superficie en distintos lugares del mundo**, con visualizaciones intuitivas, hipótesis sobre los procesos físicos y contexto complementario.

| Requisito | Dónde está | Estado |
|---|---|---|
| App interactiva con NISAR real | `app.py`, Docker, localhost:8080 | Funcional; falta URL pública |
| Varios lugares del mundo | Pantanal (9 fechas), Santiago y Valparaíso (2 fechas) + vista «Mundo» con índice de 163 mil granulos | Tres sitios procesados; faltan sitios en otros continentes |
| Más de un tipo de cambio | Agua abierta en humedal (evaluado), cambio urbano (prueba estadística) | Faltan incendio, glaciar y agricultura |
| Visualizaciones y series | Mapa, diferencia dB, serie de punto, capas evaluadas, tablero de evidencia | Falta animación temporal y comparador deslizante |
| Hipótesis físicas y límites | Tablero observado / estimado / hipótesis / dato ausente; asistente verificado | Hecho; falta revisión científica externa |
| Contexto complementario | Sentinel-2, DEM, JRC, WorldCover, ERA5, GloFAS | Hecho |
| Código abierto | Repositorio privado | **Decidir licencia y abrir antes de entregar** |
| Comprensible para público amplio | Perfiles, glosario, asistente | Falta probar con personas (`pruebas_usuarios.md`) e inglés |

## 2. Cómo levantar todo en una máquina nueva

```powershell
git clone https://github.com/ethan1213/sarwatch-nisar-2026.git
cd sarwatch-nisar-2026
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -r requirements-maps.txt -r requirements-assistant.txt -r requirements-ml.txt
# Derivados: pedir a Ethan la carpeta data/ (unos 1,5 GB) o regenerarlos desde los HDF5 de D:\NISAR\raw con scripts/prepare.py
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python -m streamlit run app.py
```

Con Docker: `docker compose up --build -d` y abrir http://localhost:8080. Los HDF5 originales (1,8 GB cada uno) no se comparten por Git; están en el disco externo `D:\NISAR\raw` del equipo de Ethan y se descargan con Earthdata Login propio (`scripts/download_scenes.py`).

## 3. Flujo de datos completo (para un sitio nuevo)

1. `scripts/request_aoi.py select --name sitio --bbox W S E N --start 2026-07-01` → elige la geometría de órbita con más fechas y escribe `catalog/sitio_scenes.json`.
2. `scripts/download_scenes.py --candidates catalog/sitio_candidates.json --target D:/NISAR/raw/sitio` → descarga con tu Earthdata Login.
3. `scripts/verify_downloads.py --scenes catalog/sitio_candidates.json --raw D:/NISAR/raw/sitio --output catalog/sitio_verified.json` → MD5 oficial, SHA-256, grilla.
4. `scripts/request_aoi.py prepare --name sitio` → COG HH/HV/looks y manifiesto en `data/sitio/`, con tiempos y compresión en `catalog/aois.json`.
5. `scripts/fetch_labels.py --aoi sitio` y `scripts/fetch_covariates.py --aoi sitio` → etiquetas Sentinel-2 y covariables (sin credenciales).
6. `scripts/evaluate_detection.py --water-aois sitio` o `--change-aois sitio` → máscaras, tarjeta de modelo y métricas en bloques retenidos.
7. `scripts/forecast_benchmark.py --aoi sitio` → benchmark de pronóstico (la persistencia debe ser superada para publicar).
8. Para calor y focos: `scripts/fetch_thermal.py --aoi sitio --start … --end …` y `scripts/evaluate_fire.py --aoi sitio` (GOES-19, sin credenciales). Antes de elegir un sitio de incendio, `scripts/scan_hotspots.py` dice dónde hubo focos y cuántas fechas NISAR hay. Ver [calor_y_focos.md](calor_y_focos.md).
9. Añadir el sitio al selector de `app.py` y a `sarwatch/views/world.py` (`SITES`).

## 4. Qué falta, en orden, con criterio de "hecho"

| # | Tarea | Responsable sugerido | Hecho cuando |
|---|---|---|---|
| 1 | Licencia y repositorio abierto | Coordinación | LICENSE (Apache 2.0 o MIT) en el repo y visibilidad pública |
| 2 | Sitios en otros continentes: Iberá, Okavango, Tonlé Sap (humedal); un incendio 2026; un glaciar patagónico | Datos + Ciencia | Cada sitio con manifiesto, etiquetas y métricas en `docs/detection_benchmark.json` |
| 3 | Probar el modelo de Pantanal en humedales que nunca vio (generalización) | Ciencia | Tabla F1 por sitio sin reentrenar y con reentrenamiento multi-sitio en `docs/` |
| 4 | Incendio y glaciar: métodos específicos (caída de HV con etiquetas de área quemada; cambio estacional de hielo) | Ciencia + Procesamiento | Módulos en `sarwatch/ml/`, pruebas y tarjeta de modelo |
| 5 | Animación temporal y comparador deslizante en el visor | Interfaz | Serie de 9 fechas de Pantanal reproducible en la app |
| 6 | Vista multipágina, inglés, accesibilidad | Interfaz | `st.navigation`, diccionario ES/EN, `scripts/check_a11y.py` sin errores críticos |
| 7 | Pruebas con 5 personas reales | Comunicaciones | Notas según `pruebas_usuarios.md` y cambios derivados |
| 8 | App pública | DevOps | URL en Cloud Run (USD 300) según `nube_capas_gratuitas.md`, con presupuesto y alarma |
| 9 | Procesamiento junto a los datos | DevOps | Lambda en AWS us-west-2 que prepara un sitio y lo deja en S3; tiempo y GB-s medidos |
| 10 | Deep learning en Colab | Ciencia + ML | Cuaderno `notebooks/colab_01_*.ipynb` ejecutado; modelo ONNX evaluado contra LightGBM en los mismos bloques |
| 11 | Material de entrega | Comunicaciones | Video de 3 minutos, resumen por perfil, informe de validación con límites |

Reglas que no se negocian: ningún número en la app sin su JSON de origen; ningún modelo en el visor sin métrica en bloques y fechas retenidos; "inundación", "daño" y "riesgo" solo con evidencia independiente; nada de credenciales ni HDF5 en Git.

## 5. Mejores modelos y herramientas para hacer el trabajo

### Para programar (asistentes de código)

| Tarea | Modelo recomendado | Por qué |
|---|---|---|
| Contratos científicos, protocolo de evaluación, revisión de afirmaciones | Claude Fable 5.1 (el más capaz) o Claude Opus 5 | Un error de criterio aquí invalida todo lo demás |
| Pipelines numéricos (rasterio, h5py, LightGBM, pruebas estadísticas) | Claude Opus 5 | Mejor relación capacidad/costo en código con muchos bordes |
| Interfaz, pruebas, documentación, Docker | Claude Sonnet 5 | Rápido y suficiente cuando la tarea está bien especificada |
| Generar casos de evaluación, glosario, limpieza | Claude Haiku 4.5 | Volumen alto; siempre revisar |

Se usan como herramienta de desarrollo (Claude Code, Codex u otro). **Ninguno entra en el producto**: decisión del propietario. Si una prueba falla dos veces con el mismo modelo, subir de modelo. Toda salida de IA se revisa y se cubre con pruebas.

### Para ciencia y ML (en el producto)

| Problema | Modelo que usamos | Alternativas por probar |
|---|---|---|
| Agua abierta | LightGBM por píxel (F1 0,83 bloques / 0,76 fecha retenida) + umbral Kittler-Illingworth como baseline | TerraMind / Clay / Galileo fine-tuned en Colab, U-Net sobre Sen1Floods11 |
| Cambio urbano | Prueba de Conradsen (diagonal) + MAD | Clasificador con etiquetas de edificios OSM; coherencia si llega GSLC/GUNW |
| Pronóstico | Persistencia, climatología (gana por 15 % en mediana HH), Ridge | LightGBM cuantílico y MAPIE cuando haya ≥ 15 fechas |
| Incendio | Focos GOES-19 por celda cruzados con HV, pendiente y cobertura; evaluación de respuesta y anticipación escrita, sin focos suficientes en los recortes actuales | Descargar Araucanía (7 pasadas, mar–abr 2026); VIIRS 375 m; dNBR óptico como etiqueta |
| Glaciar | Pendiente | Cambio estacional de retrodispersión + velocidad por offset tracking (fuera de alcance inmediato) |
| Asistente | Reglas + enrutador TF-IDF + verificador (60/60) | Qwen3-4B vía Ollama local, siempre detrás del verificador |

Detalle y veredictos: [modelos_ia_ml.md](modelos_ia_ml.md).

### Arquitecturas

- **Hoy:** laptop + Docker local + disco D para originales. Suficiente para validar ciencia.
- **Entrega del desafío:** app en Google Cloud Run con los USD 300; índice mundial en BigQuery; procesamiento junto a los datos con Lambda en AWS us-west-2 (gratis). Ver [nube_capas_gratuitas.md](nube_capas_gratuitas.md).
- **Después:** serverless con teselas (titiler) y catálogo STAC. Ver [arquitectura_nube.md](arquitectura_nube.md).

## 6. Medidas que tenemos (para no inventar cifras)

Todas las cifras públicas salen de estos archivos: `docs/detection_benchmark.json`, `docs/forecast_benchmark.json`, `docs/assistant_eval.json`, `docs/fire_benchmark.json`, `catalog/detection_reference.json`, `catalog/prediction_reference.json`, `catalog/thermal_reference.json`, `catalog/hotspot_scan.json`, `catalog/hotspot_scan_chile_verano.json`, `catalog/storage_measurement.json`, `catalog/global/coverage_1deg.json`, `models/*.card.json`. Si cambias un modelo, vuelve a correr el script que genera el JSON y revisa que la app muestre el valor nuevo.
