# Estado de entrega — 13 noviembre 2026

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
