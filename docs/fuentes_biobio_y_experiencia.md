# Biobío: evidencia útil y una interfaz que no dependa de leer un manual

## Decisiones de interfaz implementadas

El recorrido empieza por lugar, fechas y tarea. La comparación muestra dos mapas grandes con el
mismo encuadre y escala; la opción «Resaltar las diferencias» separa la comparación visual del
análisis de señal. El mapa base sirve para ubicarse y no se presenta como imagen NISAR.
HH/HV, métricas, versiones, hipótesis y tablas se consultan en detalle técnico. El asistente ofrece
preguntas iniciales. Los datos aún no verificados muestran un estado pendiente; no un mapa inventado.

Revisión técnica realizada: comparación de Valparaíso, consulta de punto y CSV, respuesta del
asistente sin confirmar incendio, FIRMS con puntos reales en Concepción/Penco, y viewport móvil
390×844 sin desborde horizontal. Los mapas móviles tienen ancho y altura útiles. Esto comprueba
funcionamiento y disposición, **no demuestra comprensión por personas reales**. El protocolo de
pruebas con personas continúa en `pruebas_usuarios.md`.

## Qué demuestra el catálogo de Chile

Fuente reproducible: `scripts/audit_chile_nisar.py` → `catalog/chile_nisar_audit.json`. Consulta
paginada de colecciones GCOV BETA, PROVISIONAL y VALIDATED desde el lanzamiento hasta el 14-11-2026.

En la ventana urbana de Concepción/Penco no aparecen granulos BETA. Hay 19 fechas de una geometría
PROVISIONAL P05023 desde el 26-02 hasta el 12-10-2026, además de otra geometría provisional.
Los dos productos VALIDATED P05036 del recorte pertenecen a geometrías diferentes: no forman una
pareja comparable. La ventana regional de Biobío sí tiene BETA y más geometrías, lo que no implica
que cubran Penco o permitan reconstruir el incendio de enero. Una intersección de huellas no prueba
cobertura útil; se comprueba después en los datos.

No se mezcla BETA con PROVISIONAL para rellenar una serie. Se distingue versión de colección,
CRID y revisión del archivo. La liberación validada actual y sus límites se verificaron en
[ASF](https://nisar-docs.asf.alaska.edu/availability-overview/).

## Fuentes complementarias elegidas

| Fuente | Qué aporta a la pregunta | Estado en este trabajo | Límite que no debe perderse |
|---|---|---|---|
| NISAR GCOV | Comparar respuesta radar del terreno en fechas reales | Pantanal y Chile central procesados; tres originales de Concepción/Penco en adquisición | No mide temperatura, carbono ni severidad de incendio directamente |
| FIRMS VIIRS NOAA-20/NOAA-21/S-NPP | Dónde y cuándo un sensor observó una anomalía térmica | Descarga pública reciente y mapa implementados; 15 detecciones urbanas y 269 en ventana regional | Un punto no equivale a incendio, perímetro ni coordenada exacta del frente |
| GOES-19 ABI | Evolución térmica y contexto infrarrojo | Día 13-11-2026 recuperado para los tres sitios anteriores, con cruce por celda SAR/DEM | Celdas kilométricas, nubes y distinta hora de observación |
| Sentinel-2 L2A | Contraste óptico, vegetación y dNBR | Pipeline existente; extensión a Biobío posterior a grilla NISAR verificada | Nubes, estacionalidad y cambios de uso también alteran dNBR |
| Landsat 8/9 Collection 2 Level-2 | Segunda referencia óptica y temperatura superficial | Fuente y método revisados; no se afirma una capa nueva ya descargada | Temperatura de superficie no es temperatura del aire ni ignición prevista |
| GPM IMERG V07 | Lluvia acumulada y evolución de episodios | Fuente revisada; integración pendiente | Rejilla 0,1° y pasos de media hora no sustituyen pico pluviométrico local de 15 minutos |
| SMAP L4 | Contexto regional de humedad superficial y de raíces | Fuente revisada; integración pendiente | Producto modelado/asimilado en rejilla de 9 km; no lectura local de cada píxel SAR |
| Copernicus DEM / WorldCover | Altura, pendiente y tipo de cobertura | Covariables existentes; extensión a Biobío posterior a preparación | Un DEM estático no proporciona profundidad de depósito ni accesos seguros |

FIRMS reciente no valida retrospectivamente un incendio de enero: hacen falta sus archivos históricos
del período correcto. Se conserva fecha, hora UTC, sensor, confianza, versión y potencia radiativa.
Se eliminan duplicados de la misma observación, sin agrupar pasadas diferentes como si fueran
incidentes únicos. La potencia radiativa en MW no se convierte directamente a toneladas de CO₂.

Fuentes primarias: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/content/active_fire/),
[FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/area/),
[Copernicus Sentinel-2](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2),
[USGS Landsat Level-2](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products),
[NASA IMERG](https://gpm.nasa.gov/data/imerg), [NSIDC SMAP](https://nsidc.org/data/smap/data).

## Relación con la propuesta del equipo

Se conserva la idea de Igor de cruzar calor, radar y terreno. La conversación de Candela añade el
caso vivido en Tomé y el interés por orientar una revisión territorial. Se corrigen las inferencias
que aún no tienen respaldo: descenso de radar no demuestra quema, radar no mide biomasa sin un
modelo calibrado, y altura + viento no certifican un flanco seguro para una brigada. El prototipo
organiza evidencia para revisar; no imparte órdenes tácticas ni pronósticos operativos.

## Distribución de servicios

GCP sirve API y derivados; Cloud Storage guarda datos y Artifact Registry las imágenes de software.
Vercel puede servir únicamente React. Supabase se reserva para catálogo, procedencia y estado
compartido, con lectura pública controlada; los HDF5 no pertenecen a una base de datos de aplicación.
Vercel/Supabase requieren conectar las cuentas; no se declaran desplegados. No se contratan planes
de pago ni se actualiza la cuenta GCP: el límite total autorizado sigue siendo US$300 de crédito.
