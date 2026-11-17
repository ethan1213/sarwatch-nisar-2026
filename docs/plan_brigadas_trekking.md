# Evolución de SARWatch: brigadas y trekking

Fecha: 16 de noviembre de 2026. Alcance inicial: Concepción, Penco y Tomé. Propuesta de desarrollo; no describe funciones ya activadas.

## Estado verificado
Cloud Run sarwatch-00007-j7p sirve 100 % del tráfico. Configuración: 1 CPU, 2 GiB, concurrencia 4, máximo 2 instancias. No se modificó infraestructura ni facturación. El presupuesto de USD 300 sigue siendo una restricción; los límites de instancias no garantizan un techo monetario. Falta consultar consumo y crédito restante antes de programar ingestas recurrentes.

Hay pronóstico horario de 48 horas, ERA5 histórico, detecciones térmicas, terreno agregado y observaciones ópticas/radar. No existe un motor validado de propagación ni un modelo local de deslizamientos. Las celdas térmicas de kilómetros no permiten evaluar un tramo de sendero con precisión métrica.

## Entrega 1: condiciones por lugar y fecha
Backend: servicio de consulta por coordenadas con historial de lluvia 1/3/7/30/90 días y pronóstico 24/48 horas. Cada ventana incluye inicio/fin UTC, unidad, cobertura de datos, celda del proveedor y fecha de actualización. No sumar huecos como cero; no mezclar pronóstico con reanálisis. Cachear consultas y limitar áreas/peticiones para controlar costo.
Frontend: dos tareas, revisar condiciones para brigadas y revisar un recorrido. Primera entrega por punto; importación GPX después. Mostrar lluvia, ráfagas, viento desde/hacia, pendiente, fuente y resolución. Ausencia de datos se muestra como desconocido, nunca como seguro.
Cierre: ventanas temporales reproducibles, tratamiento explícito de faltantes y errores; pruebas de coordenadas, fechas y unidades.

## Entrega 2: crecimiento y secado de vegetación
Construir series Sentinel-2 de verdor (NDVI) y contenido de agua de la vegetación (NDMI), con máscara de nubes/sombras y porcentaje válido por fecha. Contrastar con estacionalidad y cobertura del suelo. Buscar aumento de vegetación seguido de descenso de indicadores de humedad; contrastar lluvia acumulada y déficit meteorológico. Etiquetar como señal a revisar, no como combustible seco confirmado. NDVI/NDMI y radar no sustituyen mediciones de combustible vivo/muerto.
Cierre: series reales por zona, fechas suficientes, baseline estacional y validación independiente; sin extrapolar entre largos periodos sin imágenes.

## Entrega 3: escenarios de propagación para investigación
Preparar combustible local, humedad de combustible, terreno común con orientación, viento adecuado al motor y perímetro inicial con hora. Ejecutar un motor documentado y escenarios de incertidumbre para viento/combustible. No convertir directamente una flecha de viento en trayectoria. Evaluar contra perímetros reservados por evento, baseline de persistencia, solape y distancia al borde; tiempo de llegada solo cuando existan observaciones temporales suficientes.
Cierre: resultados y fallos publicados, revisión con especialistas, límites espaciales/temporales explícitos. Hasta entonces, sin rutas seguras ni avisos operativos automáticos.

## Entrega 4: deslizamientos y trekking
Evaluar integración de NASA LHASA como contexto regional y registrar versión, resolución, fecha y cobertura efectiva en Chile. Combinar con cartografía local de susceptibilidad y registros de eventos, geología, pendiente, humedad antecedente, lluvia intensa/acumulada y áreas quemadas. Distinguir deslizamiento superficial, caída de rocas y flujo de detritos; un modelo no cubre automáticamente los tres.
Cruzar luego trazados GPX con celdas disponibles e incertidumbre de ubicación. Mostrar tramos que requieren revisión y avisos oficiales pertinentes, sin certificar transitabilidad. Investigar fuentes oficiales de SENAPRED, SERNAGEOMIN y DMC antes de definir una integración; no asumir que sus datos tienen API o licencia abierta.
Cierre: validación retrospectiva local por evento y región, sensibilidad y falsas alarmas, caducidad de avisos y ausencia de datos probadas. Notificaciones solo tras consentimiento del usuario y evaluación del sistema.

## Orden de trabajo y presupuesto
Primero condiciones meteorológicas y calidad de datos; después series de vegetación; luego integración regional de deslizamientos y experimento acotado de propagación. Mantener Cloud Run para servir consultas pequeñas y resultados precalculados. No ejecutar entrenamiento ni grandes descargas dentro de una petición web. Medir tamaño/costo y crédito antes de activar trabajos programados; no contratar GPU ni elevar recursos por defecto.

## Referencias de diseño
- NASA LHASA: https://github.com/nasa/LHASA
- NASA LHASA y precipitación: https://pmmpublisher.pps.eosdis.nasa.gov/precip-apps-viewer.html
- Fundamento de propagación y límites: https://research.fs.usda.gov/treesearch/55928
- Open-Meteo histórico: https://open-meteo.com/en/docs/historical-weather-api

Estas referencias orientan la implementación. No equivalen a integración ni validación ya completadas.

## Fuentes chilenas y prioridades adicionales

- CONAF: pronóstico y humedad de combustible fino muerto: https://www.conaf.cl/incendios/situacion-actual-y-pronostico-de-incendios/ . Verificar vigencia, cobertura y condiciones de acceso.
- CONAF: mapas nacionales de riesgo: https://www.conaf.cl/incendios/analisis-nacional-de-riesgo-de-incendios-forestales/ . Revisar escala y fecha.
- SERNAGEOMIN: catastro preliminar de remociones: https://www.sernageomin.cl/visores-mineros/ . No es un inventario validado ni exhaustivo.
- Landsat 8/9 Collection 2: reflectancia a 30 m para complementar series Sentinel-2; aplicar escala y máscara de nubes: https://www.usgs.gov/landsat-missions/landsat-surface-reflectance .
- Consultar lluvia por cualquier punto, con ventanas completas e incompletas identificadas. Open-Meteo forecast API past_days entrega estimaciones modeladas, no estaciones. Validar frente a pluviómetros antes de alertar.
- Antes de activar predicciones, evaluar incertidumbre y capacidad por evento independiente con revisión de especialistas locales.

## Actualización implementada: recorridos y vegetación (16/11/2026)

- Serie puntual Sentinel-2 en Penco: 11 adquisiciones de 2026, NDVI/NDMI, tabla de productos y gráfico sin interpolación. No cumple todavía la serie regional con baseline estacional de la entrega 2.
- Consulta de GPX en navegador: segmentos independientes, distancia horizontal aproximada, hasta 20 puntos de consulta, cruce con polígonos reales del terreno agregado. No se extrapolan valores desde celdas vecinas fuera de cobertura.
- Pronóstico horario 48 h y acumulados anteriores 1/3/7/30/90 días por punto elegido. No se envía el archivo GPX; solo la coordenada consultada. Consulta de puntos, no evaluación continua de cada tramo.
- GPX admite archivo de hasta 2 MB o texto pegado, 20.000 puntos máximo; rechaza XML inválido, entidades externas y coordenadas fuera del área de consulta de Chile.
- Pruebas del recorrido: distancia sin puentes entre segmentos, coordenadas inválidas, cobertura con huecos, muestreo acotado. Fixture sintético identificado como prueba, nunca como sendero recomendado.
- LHASA: documentación oficial consultada en https://github.com/nasa/LHASA y https://registry.opendata.aws/nasa-landslide-project/ . La descarga en maps.nccs.nasa.gov no resolvió DNS desde el equipo el 16/11/2026. No se incorporó una capa ficticia ni se confundió el catálogo con datos descargados.

Pendientes que impiden afirmar «predicción operativa terminada»: combustible local y humedad medidos; terreno y viento adecuados al motor; series regionales de vegetación; inventario local independiente de eventos; calibración y revisión especializada; evaluación temporal/espacial con falsas alarmas; consentimiento y caducidad para notificaciones. La importación GPX no elimina esos requisitos.

## Decisión de implementación para Biobío (17/11/2026)

**Propagación.** Mantener desactivada la salida numérica de propagación de `/api/fire/propagation-readiness`. Los focos FIRMS/GOES indican anomalías térmicas, no el borde ni la hora de avance del fuego. Las delimitaciones Copernicus EMSR859 del 21 al 25 de enero sirven para contraste tardío, pero no reconstruyen el inicio del 17 al 18. Para el primer experimento en Concepción, Penco y Tomé: (1) conseguir ignición/perímetro inicial fechado y perímetros posteriores independientes; (2) preparar un modelo de combustible local y humedad viva/muerta medidos; (3) alinear DEM, pendiente/orientación y viento horario en una grilla común; (4) ejecutar escenarios con incertidumbre y contrastarlos por evento y fecha contra persistencia. Publicar fallos, falsas alarmas y resolución antes de habilitar cualquier trayectoria para brigadas. Las series NDVI/NDMI y NISAR pueden aportar contexto de vegetación y cambio posterior, pero no reemplazan las mediciones de combustible.

**Derrumbes.** El repositorio oficial de NASA identifica LHASA **2.1.1**, con estimación diaria global a 30 segundos de arco (aproximadamente 1 km) y una salida separada para cuencas con potencial de flujo de detritos posterior a incendios: https://github.com/nasa/LHASA/blob/master/README.md . Su archivo público está en https://portal.nccs.nasa.gov/datashare/landslides/ y NASA advierte interrupciones frecuentes. Integrar únicamente recortes fechados de Biobío con versión, hora, tamaño de celda, cobertura y fecha de actualización; si falta un día, mostrar «sin dato». Complementar con lluvia antecedente, pendiente, quema y cartografía geológica local. LHASA no resuelve caída de rocas ni certifica senderos: contrastar con un inventario local validado y eventos reservados antes de clasificar tramos GPX o emitir avisos automáticos.

**Almacenamiento y gasto.** Los nueve GeoTIFF derivados NISAR y su manifiesto ya están en el bucket privado `sarwatch-525550511866-data/derived/concepcion_penco/`. Los tres HDF5 originales locales suman aproximadamente 4,9 GiB. Conservarlos hasta que cada copia a GCS tenga tamaño y checksum verificados; entonces retirar solo esas tres copias locales. Guardar metadatos y recortes regionales, no duplicar series globales en Cloud Run. Consultar consumo y crédito antes de tareas recurrentes; un presupuesto de GCP avisa, pero no garantiza un corte automático de gasto.
