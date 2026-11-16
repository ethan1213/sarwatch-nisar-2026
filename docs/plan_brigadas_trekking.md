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
