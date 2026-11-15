# SARWatch · NISAR 2026

La entrada guiada explica lugar, fechas y significado antes de los detalles SAR. Incluye perfiles de público general/ciencia/desarrollo/comunicaciones/gestión, asistente local basado en reglas y fuentes, calculadora de almacenamiento y referencia predictiva retrospectiva. No hay un LLM instalado ni predicción validada de inundación. La evaluación detallada y el plan están en [experiencia, asistente y predicción](docs/experiencia_asistente_y_prediccion.md).

Explorador de cambios de retrodispersión para **Dancing with the SARs**. Equipo Software Detective, Santiago, Chile. Proyecto independiente, sin respaldo implícito de NASA o ISRO.

Pantanal: siete adquisiciones GCOV PROVISIONAL de 2026, HH/HV, frecuencia A. Originales fuera de Git. No hay clasificación de inundaciones validada.

## Ejecutar

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -r requirements-maps.txt
.\.venv\Scripts\python scripts/prepare.py --raw "RUTA_A_LOS_HDF5" --output data
.\.venv\Scripts\python -m streamlit run app.py
```

Con Docker Desktop iniciado y derivados preparados: `docker compose up --build -d`. Abrir http://localhost:8080. Detener con `docker compose down`. Sin derivados, se muestra el catálogo y cómo prepararlos.

Incluye procesamiento por ventana, COG, rechazo de grillas incompatibles, comparación temporal, diferencias, serie de punto y CSV. Meteorología opcional con histórico ERA5 y pronóstico separados; sus errores no bloquean SAR.

## Modelos y asistente (14 noviembre 2026)

Detección de agua abierta en Pantanal evaluada contra Sentinel-2 en bloques y fecha retenidos (LightGBM F1 0,83 / 0,80; umbral Kittler-Illingworth 0,65; Otsu 0,10), prueba de cambio de Conradsen para Santiago y Valparaíso, benchmark de pronóstico en origen rodante donde la persistencia sigue ganando (no se publica pronóstico) y asistente local con enrutador de intenciones, herramientas con cifras verificables y verificador de salida (60/60 casos). Sin API de Claude ni otro LLM externo en el producto. Inventario de modelos: [docs/modelos_ia_ml.md](docs/modelos_ia_ml.md).

```powershell
.\.venv\Scripts\python -m pip install -r requirements-ml.txt
.\.venv\Scripts\python scripts/fetch_labels.py --aoi .        # etiquetas Sentinel-2 (sin credenciales)
.\.venv\Scripts\python scripts/fetch_covariates.py --aoi .    # DEM, JRC, WorldCover
.\.venv\Scripts\python scripts/evaluate_detection.py          # máscaras, tarjetas y docs/detection_benchmark.json
.\.venv\Scripts\python scripts/forecast_benchmark.py          # docs/forecast_benchmark.json
.\.venv\Scripts\python scripts/evaluate_assistant.py          # docs/assistant_eval.json
```

## Datos originales y escala mundial

Los HDF5 originales viven en el disco externo `D:/NISAR/raw` (variable `SARWATCH_RAW`); nunca entran en Git ni en la imagen Docker. El archivo GCOV completo supera los 290 TB en 163 mil granulos, por lo que la app no lo copia: `scripts/build_global_catalog.py` construye un índice mundial desde CMR y la vista «Mundo · cobertura NISAR» muestra dónde hay datos y cuántas fechas; los sitios se procesan bajo demanda con `scripts/request_aoi.py`. Opciones de nube en [docs/arquitectura_nube.md](docs/arquitectura_nube.md).

## Documentación y estado

- [Plan detallado](docs/plan_implementacion.md)
- [Arquitectura](docs/arquitectura.md)
- [Investigación oficial](docs/investigacion.md)
- [Docker y nube](docs/publicacion_y_github.md)
- [Meteorología](docs/meteorologia.md)
- [Comprobaciones y pendientes](docs/estado.md)
- [Modelos de IA/ML: inventario y veredicto](docs/modelos_ia_ml.md)
- [Estrategia comercial](docs/estrategia_comercial.md)
- [Guion de pruebas con personas](docs/pruebas_usuarios.md)

Pruebas: `python -m unittest discover -s tests -v`.

Prototipo exploratorio: filtrado de finitos positivos y fill values declarados. Se aplican las máscaras de calidad descritas por el producto; falta validación ambiental independiente. Incluye mapa geográfico y consulta con clic. Los gráficos conservan UTM. Siete fechas y un AOI no equivalen a cobertura anual o mundial. Código privado por instrucción del propietario; resolver apertura/licencia y acceso del jurado antes de enviar al desafío.

## Chile central

Selector de Pantanal, Región Metropolitana y Valparaíso continental. Chile incluye límites comunales CIREN, mapa base y satelital de contexto, consulta de puntos, pronóstico y candidatos NISAR CMR. No se presentan candidatos como series SAR procesadas. Ver docs/chile_y_mapas.md.

Los entornos urbanos de Santiago y Valparaíso/Viña del Mar incluyen capas NISAR reales del 5 y 17 octubre 2026, verificadas mediante checksum oficial, con HH/HV, diferencia y valores por punto. Son recortes urbanos; no equivalen a cobertura completa de las regiones. Los originales permanecen en data_raw/chile y derivados en data/metropolitana y data/valparaiso, fuera de Git.
# Publicación React + FastAPI en GCP

La interfaz React incluye Pantanal, Región Metropolitana, Valparaíso, Mundo, calor/infrarrojo,
PostFuego y laboratorio experimental CO₂/DEM. El proceso web publicado usa FastAPI, sin Streamlit.
Estado, validaciones y límites: [docs/cierre_gcp.md](docs/cierre_gcp.md).

```powershell
# Aplicación completa en local, usando los derivados verificados existentes:
cd web
npm ci
npm run build
cd ..
docker build -t sarwatch-nisar:local .
docker build -f Dockerfile.deploy -t sarwatch-nisar:demo .
docker build -f Dockerfile.cloud -t sarwatch-nisar:cloud .
docker run --rm -p 127.0.0.1:8090:8080 sarwatch-nisar:cloud
# En otra terminal:
.\.venv\Scripts\python scripts/check_api.py http://127.0.0.1:8090
# Redespliegue: scripts/deploy_gcp.ps1 -GcloudPath <ruta-a-gcloud.cmd>
```

El límite autorizado es US$300 de crédito total. Mantener cuenta en prueba gratuita;
no actualizarla a pago. Alertas de presupuesto no equivalen a un corte automático.
