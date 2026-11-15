# SARWatch · adaptación de Figma y flujo para brigadas

## Entrega funcional

Plataforma de análisis territorial para brigadas, publicada en Cloud Run. Se retiró la etiqueta «prototipo» del front a petición del propietario. La identidad del producto es SARWatch; se adapta la propuesta visual compartida en Figma sin copiar sus cifras, mapas ilustrativos, fechas pendientes ni supuestos flancos seguros.

Diseño: https://www.figma.com/make/zwU59kMtbg8bR9XPZJBfmI/NISAR-Surface-Change-App

El video de referencia muestra relieve 3D, fotografía satelital, capas temáticas y selección de terreno. Se incorporan el relieve 3D, la imagen de contexto y la inspección del punto observado, aplicados a incendios. No se trasladan los modelos de cultivos, los árboles ilustrativos ni sus cifras de precisión al análisis del fuego. El video original y las conversaciones privadas no se publican en Git.

## Flujo conectado

1. Elegir Biobío y un punto de FIRMS VIIRS de la consulta disponible. Fecha de detección visible; la consulta guardada no se presenta como un frente en vivo.
2. Consultar Open-Meteo: temperatura, humedad relativa del aire, velocidad y dirección del viento, ráfagas, déficit de presión de vapor, precipitación y probabilidad de lluvia, con 48 horas seleccionables.
3. Comparar sectores geométricos a 2 km del punto, relativos a la dirección del viento: izquierdo, derecho y sotavento. Cada sector ofrece altura y pendiente de la celda del DEM más cercana cuando existe a menos de 3 km. No son flancos reales identificados ni rutas seguras.
4. Abrir el mismo punto en relieve 3D, con marcador y referencias del viento cuando están disponibles. Sin giro automático ni exageración vertical.
5. Consultar la secuencia observada de Copernicus EMSR859, el cambio de señal NISAR o el índice de vigilancia evaluado.
6. Exportar la evidencia del lugar o la revisión del punto en JSON. Viña exporta sus propios datos; no reutiliza el resumen de Biobío.

## Capas y fechas reales

| Vista | Fuente | Alcance |
|---|---|---|
| Focos recientes | NASA FIRMS VIIRS NOAA-20, NOAA-21 y S-NPP | Consulta reciente guardada; puntos, no perímetro ni incendio único |
| Histórico de calor | GOES-19 / NOAA | Horas de enero 2026; separado de FIRMS |
| Clima | Open-Meteo, pronóstico horario | Viento a 10 m de un modelo; no medición local dentro de una quebrada |
| Meteorología pasada | ERA5 vía Open-Meteo | Reanálisis, no pronóstico retrospectivamente disponible |
| Altura y pendiente por celda | Copernicus DEM | Medias en celdas térmicas; no análisis de accesos de precisión métrica |
| Relieve 3D | Mapzen Terrain Tiles en AWS | Dataset distinto del usado en las estadísticas; sin exageración vertical |
| Imagen satelital de contexto | Esri World Imagery | Fecha variable, no fotografía histórica atribuida al incendio |
| Biobío NISAR | GCOV PROVISIONAL P05023, misma serie | 26 feb, 14 jun y 12 oct 2026, posteriores al incendio de enero |
| Extensión observada Biobío | Copernicus EMSR859 AOI04 | 21, 22, 23, 24 y 25 ene 2026; fechas y sensores por producto |
| Viña: incendio 2024 | Sentinel-2 L2A, Planetary Computer | Imágenes reales del 18 ene y 12 feb 2024, máscaras SCL y offset de reflectancia aplicado |
| Viña: radar 2026 | NISAR HH/HV | 5 y 17 oct 2026, separado del incendio de 2024 |

Las capas derivadas de Concepción/Penco también se publicaron como revisión inmutable en Cloud Storage. La web lee ese bucket en modo de solo lectura. Los HDF5 originales y Earthdata Login no forman parte de la imagen ni de Git.

## Resultado de investigar perímetros

La API pública de Copernicus EMSR859 ofrece cinco productos para AOI04 Concepción. Se descargaron las geometrías originales, se calcularon SHA256 y se prepararon versiones de visualización simplificadas a 20 m. Los originales están en work/emsr859, fuera de Git; el manifiesto publicado conserva sus enlaces, sensores, versiones y hashes.

| Adquisición UTC | Sensor | Producto |
|---|---|---|
| 21 ene 2026 15:25 | PlanetScope | DEL v2 |
| 22 ene 2026 14:37 | Sentinel-2 | DEL MONIT01 v1 |
| 23 ene 2026 23:21 | Legion | DEL MONIT02 v1 |
| 24 ene 2026 14:33 | Pleiades | DEL MONIT03 v1 |
| 25 ene 2026 14:46 | SPOT-6-7 | GRA v2 |

No cubren el avance inicial del 17–18 de enero. Una diferencia entre productos también puede deberse a sensor, visibilidad y revisión cartográfica. Las geometrías simplificadas se usan para mostrar, no para calcular métricas o entrenar.

API documentada por el propio visor: https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR859

## Qué modelo funciona y qué falta para propagación

El modelo radar_terreno evalúa prioridad de detecciones térmicas a 12 días. En fechas retenidas: AUC 0,632, con 44 casos positivos; referencia de persistencia 0,494. Fuente: catalog/fire_story/story.json y catalog/fire_propagation_readiness.json. Eso no es precisión de trayectoria ni una probabilidad calibrada de incendio.

El pronóstico meteorológico de 48 horas funciona como fuente independiente. Se muestran también referencias laterales respecto al viento. No se genera una velocidad de fuego ni un flanco seguro a partir de esos datos.

Para un experimento de propagación se dispone ahora de un estado inicial observado el 21 de enero y de delimitaciones posteriores para contrastarlo. Siguen faltando un modelo local de combustible, su humedad, una grilla de terreno preparada para el motor y la adecuación del viento al combustible/terreno. La humedad del aire no sustituye la humedad de combustible. Tampoco se convierte directamente el radar en biomasa o combustible.

Secuencia de implementación científica: preparar esos insumos y sus unidades; ejecutar un motor físico basado en Rothermel o FARSITE en un caso acotado; comparar con persistencia y las delimitaciones retenidas; evaluar solape, distancia al borde y error de llegada; repetir con otros eventos separados del entrenamiento. Si solo se dispone de perímetro final, se evalúa extensión final, no trayectoria horaria. Completar el contrato de datos no activa por sí solo una predicción operativa.

Referencia física: https://research.fs.usda.gov/treesearch/55928
Entradas y simulación FARSITE: https://owfflammaphelp62.firenet.gov/millerTutorials/miller-Input_a_FARSITE_Simulation.htm

## Archivos y reproducción

- scripts/audit_fire_propagation.py: inventario de insumos y evidencia; sin salidas numéricas de propagación inventadas.
- sarwatch/ml/sector_context.py: direcciones meteorológicas, sectores geodésicos y consulta del relieve; bloquea interpretación de dirección con viento débil.
- scripts/fetch_fire_dnbr.py y scripts/build_vina_2024.py: comparación Sentinel-2 de Viña.
- scripts/prepare_official_perimeters.py: publicación de geometrías para visualización con hashes de los originales.
- catalog/vina_2024 y catalog/official_fire_perimeters: paquetes públicos que sirven las vistas.
- GET /api/fire/forecast, /forecast-sectors, /sector-context, /vina-2024 y /official-perimeters.

El render 3D usa datos públicos desde el navegador. No se contrataron servicios adicionales, GPU, LLM ni planes pagados. Se mantienen mínimo 0 y máximo 2 instancias Cloud Run. Las alarmas de presupuesto no son un corte automático de gasto; no se modificó la modalidad de prueba de GCP.

## Fuentes y atribuciones

- © European Union, 2026 · Copernicus EMSR859: https://mapping.emergency.copernicus.eu/activations/EMSR859/
- Contexto del producto al 25 de enero: https://eu-space.europa.eu/components/earth-observation-copernicus/image-of-the-day/wildfires-biobio-and-nuble-regions-chile
- FIRMS: https://firms.modaps.eosdis.nasa.gov/content/active_fire/
- Open-Meteo: https://open-meteo.com/en/docs
- Sentinel-2: https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a
- Contexto del incendio 2–3 feb 2024: https://cigiden.cl/producto/informe-de-danos-evento-incendios-02-y-03-de-febrero-de-2024-vina-del-mar-region-de-valparaiso/
- Terrain Tiles: https://registry.opendata.aws/terrain-tiles/
- Atribución del terreno: Mapzen, USGS SRTM/GMTED2010 y NOAA ETOPO1; https://github.com/tilezen/joerd/blob/master/docs/attribution.md
- Traza Urbana, Gerardo Ureta: referencia de interfaz citada en el diseño del equipo, sin importar sus capas: https://trazaurbana.cl/
