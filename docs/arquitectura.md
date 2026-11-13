# Diseño de la aplicación

Actualización 13 noviembre 2026: este documento conserva el diseño inicial. Existe ahora un prototipo Streamlit con vistas raster UTM, diferencias, serie por coordenadas y meteorología opcional. Mapa base, clic y validación ambiental siguen pendientes. El plan vigente y las comprobaciones están en `plan_implementacion.md` y `estado.md`.

Decisión propuesta, 11 de octubre de 2026: comenzar con una aplicación web de exploración y comparación de cambios de retrodispersión, antes de introducir una clasificación de inundación.

## Usuarios y recorrido
Una persona abre un enlace, selecciona Pantanal y una fecha, y ve HH o HV sobre el mapa. Puede elegir otra fecha para comparar, activar la diferencia en dB y consultar la serie de un punto. Siempre se muestran adquisición, unidades, producto y área válida. Las fechas ausentes se mantienen como huecos.

## Primera versión
- Mapa geográfico con selector de siete fechas y polarización.
- Comparación antes/después con escala de color consistente.
- Diferencia temporal sobre píxeles válidos en ambas fechas.
- Serie temporal al seleccionar un punto; información ausente se muestra como ausente.
- Panel de procedencia: identificador NASA, fecha UTC, versión y verificación.
- Exportación de un recorte y su descripción, una vez disponible el procesamiento.
- Texto visible: cambio de retrodispersión. La categoría inundación probable requiere método y validación adicionales.

## Procesamiento
Python, h5py, NumPy, rasterio y pyproj. Un proceso local lee ventanas del HDF5, identifica sus coordenadas y recorta el AOI. Se comprueban grillas completas, no solo tamaño o EPSG. Si no coinciden, se define una grilla común y un método documentado de remuestreo; las máscaras se remuestrean como categorías.

Se conservan originales. La transformación a dB usa únicamente intensidades positivas y válidas. Se generan GeoTIFF/COG con CRS, nodata, unidades, overviews y metadatos de procedencia. El análisis temporal calcula diferencias en dB entre fechas, con una máscara común; no rellena huecos mediante datos inventados.

Antes de usar máscara, inputDataExceptionMask o numberOfLooks se revisan sus atributos y la especificación de la versión 1.5.0 observada. No se inventará un significado para códigos de máscara ni un umbral universal.

## Web recomendada
Primera implementación: Streamlit con visualización cartográfica y Plotly, leyendo productos pequeños ya procesados. Un servidor con Python puede alojarla para acceso mediante HTTPS. El análisis SAR pesado queda en un proceso separado.

Evolución si la navegación raster lo exige: frontend React/TypeScript y MapLibre, servicio FastAPI + TiTiler, almacenamiento de COG accesible por solicitudes de rango. Esta evolución se justifica por necesidades de escala e interacción, no es requisito del primer experimento.

## Contrato de datos
Catálogo por región y escena: ID, fecha UTC, sensor, producto, frecuencia, polarizaciones, CRS, espaciado, versión, bounds, URL de capas, nodata, calidad y procedencia. La publicación recibe URLs de productos derivados; no rutas absolutas de esta computadora.

Para una consulta de punto: coordenadas WGS84 y valores por fecha/polarización, con estado válido/ausente y unidad. Para una diferencia: IDs de ambas escenas, máscara de validez, diferencia en dB y parámetros.

## Límites científicos actuales
Tenemos siete fechas entre julio y septiembre, no cobertura de todo el año. La extensión del proyecto es una región inicial; el catálogo podrá incorporar otras regiones verificadas. No existe todavía verdad de terreno o validación hidrológica independiente. El tamaño común de las matrices no prueba la cobertura útil común. La comparación entre banda L y otros sensores deberá controlar fechas, geometría y unidades.
