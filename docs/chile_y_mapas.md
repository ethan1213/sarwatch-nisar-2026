# Mapas y cobertura científica

## Implementado

- Pantanal: capa NISAR reproyectada a WGS84 para visualizar, controles de capa, mapa base OSM, imagen de contexto Esri y consulta por clic dentro del AOI. Los cálculos y consultas conservan la grilla nativa. El mapa muestra la fecha final o la diferencia según el modo seleccionado.
- Región Metropolitana: 52 polígonos comunales, referencia de Santiago y selección de punto.
- Valparaíso continental: 36 polígonos comunales, referencia de Valparaíso y selección de punto. La fuente continental excluye territorios insulares; no es un mapa de toda la región insular.
- Chile: pronóstico del punto y catálogo candidato Earthdata CMR. La consulta engloba Chile central (-72,-34.3,-69.7,-32), no verifica por sí sola cada comuna. Se conserva la primera página de 30 resultados, URL y fecha de consulta. No se afirma un inventario exhaustivo.

## Procedencia

Límites comunales descargados del servicio CIREN / IDE Minagri, capas 8 y 9; salida EPSG:4326, simplificación de 0,001 grados para visualización. No usar como deslinde legal. Tooltip: nombre de comuna. Capa original y campos conservados en catalog/*.geojson.

- https://esri.ciren.cl/server/rest/services/Hosted/LIMITES_ADMINISTRATIVOS_1/FeatureServer
- https://geoportal.cl/geoportal/catalog/42510/servicio-de-web-de-mapas-limites-administrativos
- https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html

Mapa base: © colaboradores OpenStreetMap. Imagen de contexto: Esri/proveedores de imágenes; no se etiqueta como NISAR. Estos servicios externos requieren conexión; los productos científicos locales siguen separados.

## Control de calidad aplicado

Se inspeccionaron los atributos de mask, inputDataExceptionMask y numberOfLooks del HDF5. El procesador comprueba las descripciones antes de aplicar reglas: subswath > 0 y dentro del número declarado; excepción cero; looks finitos positivos; intensidad finita positiva y no fill. Mask 0 identifica píxeles no completamente enfocados; 255 está fuera de adquisición. La interpretación de excepciones proviene del atributo del producto (0: no anomaly). Si cambia la semántica, se detiene el procesamiento.

La máscara técnica no prueba que un cambio sea inundación ni reemplaza evidencia ambiental independiente. No se ha entrenado un predictor de superficie. Para producir series chilenas faltan adquisición autenticada de los HDF5, selección de pares con grilla/geometría compatible y validación local. Los archivos de Pantanal no pueden trasladarse a Santiago.

## Ejecución y límites de entrega

Alcance autorizado: Docker local. No se provisiona nube. Pruebas funcionales recorren los tres destinos y el fallo meteorológico; pruebas cartográficas verifican polígonos y overlay reproyectado. La verificación visual se reporta separada de AppTest. No se declara terminada la validación ambiental que exige referencias independientes.
