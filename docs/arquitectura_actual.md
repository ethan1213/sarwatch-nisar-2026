# Arquitectura implementada

La aplicación conserva Streamlit como adaptador de presentación. La estructura separa las responsabilidades sin introducir servicios de red que todavía no necesita el volumen actual.

| Componente | Responsabilidad |
|---|---|
| app.py | Flujo de exploración y estado de controles |
| sarwatch/repository.py | Validación de manifiesto, límites de rutas y lectura por ventana para series de puntos |
| sarwatch/charts.py | Representación raster con escalas y coordenadas explícitas |
| sarwatch/theme.py | Tratamiento visual compartido |
| science.py | Operaciones numéricas y máscara común |
| weather.py | Adaptador externo opcional, separado del procesamiento SAR |
| scripts/prepare.py | Preparación fuera del servidor web (COG HH/HV y capa de looks) |
| sarwatch/ml/ | Fundamentos científicos de ML: features, splits por bloques, métricas, umbrales de agua, prueba de cambio, LightGBM, pronóstico, inferencia ONNX por ventanas |
| sarwatch/assistant/ | Asistente local: enrutador de intención, herramientas con cifras, recuperador BM25, generadores (reglas y Ollama opcional) y verificador |
| sarwatch/detections.py | Lectura de máscaras evaluadas y leyendas para el visor (sin dependencias de ML) |
| sarwatch/views/components.py | Tablero de evidencia observado / estimado / hipótesis / dato ausente |
| scripts/fetch_labels.py, fetch_covariates.py | Etiquetas Sentinel-2 y covariables (DEM, JRC, WorldCover) en la grilla NISAR |
| scripts/evaluate_detection.py, forecast_benchmark.py, evaluate_assistant.py | Evaluaciones que alimentan `catalog/*_reference.json` y `docs/*_benchmark.json` |
| scripts/select_new_scenes.py, download_scenes.py, request_aoi.py | Adquisición por geometría repetida y AOI bajo demanda con mediciones |

Los datos y las máscaras evaluadas se montan como solo lectura. El visor solo muestra capas que tienen una evaluación registrada en `catalog/detection_reference.json`; el asistente solo pronuncia cifras que existen en las herramientas. El procesamiento no se ejecuta al navegar. La interfaz almacena en caché las capas utilizadas para comparación; las series consultan ventanas de un píxel. Las rutas de productos deben permanecer dentro del directorio publicado. La consulta meteorológica falla independientemente de las observaciones SAR.

## Verificación

Pruebas unitarias: unidades, nodata, diferencias, contrato meteorológico y límites de acceso a productos. Prueba funcional AppTest con datos reales: carga, diferencia, polarización y continuidad ante caída meteorológica. La misma prueba se ejecuta en Linux dentro del contenedor.

## Trabajo todavía necesario

Esta separación mejora la base del prototipo; no equivale a una plataforma de producción terminada. Faltan mapa geográfico con interacción directa, evaluación completa de QA, validación ambiental, prueba visual responsive, observabilidad de despliegue y acceso externo. Esas etapas deben conservar la procedencia y comprobarse individualmente.
