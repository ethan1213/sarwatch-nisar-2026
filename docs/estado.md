# Estado de entrega — 13 noviembre 2026

## Actualización: comprensión y evaluación predictiva

Se añadió lectura guiada con resumen calculado, perfiles de audiencia, chat local explícitamente basado en reglas/fuentes, estadísticas robustas de la máscara común y calculadora de escala. No se instaló un LLM ni se habilitó API de lenguaje externa. El benchmark retrospectivo de persistencia HH de Pantanal tiene cuatro evaluaciones a ~12 días y MAE 0,45154 dB; no es un predictor validado de inundación. Detalle, revisión de escritorio por perfiles, escenarios de almacenamiento y plan de validación: experiencia_asistente_y_prediccion.md. No se realizaron entrevistas con usuarios reales.

Verificación de esta actualización: 14 pruebas unitarias; AppTest de los tres AOI, cinco perfiles y pregunta de predicción; recorrido dentro del contenedor Linux. Servicio healthy. Se pudo inspeccionar visualmente la versión actual en el navegador y comprobar una respuesta del chat que se abstiene de predecir inundación. La captura de esa prueba queda en work/asistente-verificado.jpg (fuera de Git). Esta evidencia visual no sustituye pruebas de usabilidad con personas.

## Actualización: NISAR real para Chile

Descargados los HDF5 del 5 y 17 octubre de 2026. Ambos tamaños y MD5 coinciden con CMR; SHA-256 y grillas registrados en catalog/chile_verified.json. Generados COG HH/HV para dos AOI urbanos: Santiago y Valparaíso/Viña del Mar, usando las mismas máscaras técnicas que Pantanal. Cobertura válida por fecha superior a 99,9 % en ambos recortes. Informes: metropolitana_quality.json y valparaiso_quality.json.

El visor regional incorpora ambas fechas, diferencia en dB, consulta de punto con valores y CSV, y procedencia. Los límites comunales siguen siendo referencia de toda la región continental; la capa SAR cubre solo el recorte indicado. Esto reemplaza el estado anterior de «solo candidatos» para esos dos AOI, no para todas las comunas. Sigue pendiente validación ambiental independiente; no se publican inundaciones confirmadas ni predicciones SAR.

Nueve pruebas unitarias y AppTest con cambio HH/HV y diferencias en ambos recortes pasan en Windows. Imagen Docker reconstruida y AppTest regional pasa también en Linux con los derivados reales montados. El aviso de PSReadline observado en la terminal no afectó la descarga ni la integridad de archivos.

## Actualización: mapas Chile y QA

Alcance actual: solo Docker local por elección del propietario. Implementados selector de región, mapa geográfico NISAR con consulta por clic en Pantanal y límites comunales continentales CIREN de Metropolitana y Valparaíso, con encuadre regional/ciudad, pronóstico y candidatos CMR. Descarga de fuentes reproducible mediante scripts/refresh_chile.py. Siete pruebas unitarias y recorrido AppTest de los tres destinos pasan en Windows.

Las siete escenas de Pantanal se reprocesaron con máscara de subswath, excepciones y looks según sus atributos; se conserva la cobertura escasa de julio 5. El resumen actualizado es quality_summary.json. Esto reemplaza el filtrado anterior de solo finitos positivos. La validación ambiental independiente sigue pendiente y no se presentan inundaciones confirmadas.

Para Chile hay cartografía y catálogo candidato, todavía no HDF5 descargados/procesados ni cambios SAR validados. La fuente CIREN usada excluye territorios insulares. El control del navegador volvió a fallar por timeout; no se afirma verificación visual. Imagen Docker reconstruida y prueba funcional AppTest ejecutada en Linux: carga, diferencia, polarización, fallo meteorológico y navegación de las tres zonas sin excepciones. Servicio local healthy y HTTP 200 en localhost:8080. Siete pruebas unitarias pasan en Windows.

## Comprobado

- Recuperado el chat anterior y catálogo de siete escenas Pantanal 2026.
- Creado el repositorio remoto privado `ethan1213/sarwatch-nisar-2026`.
- Docker Desktop iniciado; Compose validado.
- Cuatro pruebas unitarias pasan: unidades dB, datos inválidos, máscara temporal común y contrato meteorológico.
- Consultas reales Open-Meteo: pronóstico de siete días e histórico ERA5 de cinco días responden para el punto Pantanal. No se añadieron observaciones ficticias.
- Código inicial subido y SHA remoto comprobado.
- Preparados 14 COG (HH/HV de siete escenas), aproximadamente 406 MB fuera de Git. Grilla común comprobada: EPSG:32721, 2769 × 2661, 20 m.
- Punto de referencia de la escena del 17 de julio coincide entre HDF5 convertido a dB y COG (-7,42203045 dB).
- Prueba de interfaz mediante Streamlit AppTest en Windows: carga, diferencia, cambio HH/HV y caída simulada de meteorología pasan sin excepción; SAR permanece disponible.
- Cobertura inicial de finitos positivos: 77 píxeles (0,001045 %) el 5 de julio; 100 % en las otras seis fechas. Esto no reemplaza QA. Resumen reproducido en quality_summary.json. El visor elige por defecto el 17 de julio y mantiene visible la fecha escasa.
- Imagen Docker Linux construida. Dependencia nativa libexpat1 incluida. AppTest dentro del contenedor pasa carga, diferencia, polarización y caída meteorológica con los derivados reales montados.
- Contenedor ejecutándose como UID 10001, estado healthy y endpoint HTTP 200. Acceso local: http://localhost:8080. Montaje de datos de solo lectura; no se subieron COG/HDF5 al repositorio.

## Pendientes y límites

No confundir las verificaciones técnicas con validación hidrológica. Faltan interpretación completa de máscaras QA, evidencia ambiental independiente y mapa base/clic. La comprobación visual en Chrome quedó interrumpida por desconexión del control del navegador; AppTest sí completó el flujo en Windows y Linux. El despliegue en nube no está ejecutado y los colaboradores no están invitados sin sus cuentas verificadas.
