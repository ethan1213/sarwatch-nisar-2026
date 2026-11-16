# Fuentes candidatas para Biobío — 16 noviembre 2026

Investigación de fuentes, no integración implementada. Comprobar adquisición, cobertura y licencias para cada periodo y zona antes de usar los datos.

| Fuente | Aporte | Resolución / frecuencia del producto | Precaución |
|---|---|---|---|
| NASA GPM IMERG Early V07 | Lluvia casi en tiempo real | 0,1°, cada 30 minutos | Estimación regional; Early no tiene calibración final. Integrar tasas considerando duración y datos faltantes. https://gis.earthdata.nasa.gov/portal/home/item.html?id=598df0e6fd674ab7855f448f7f6f0e39 |
| NASA SMAP L4 SPL4SMGP V8 | Humedad superficial y zona radicular | Grilla 9 km, cada 3 horas | Producto de asimilación en modelo; no humedad de combustible ni precisión de sendero. https://nsidc.org/data/smap/data |
| Copernicus Sentinel-2 L2A | Verdor y contenido de agua de vegetación mediante NDVI/NDMI | Bandas 10 y 20 m; revisita nominal 5 días al ecuador | Nubes y sombras; NDMI no mide directamente humedad de combustible. https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2 |
| NASA MODIS MOD13Q1 | Contexto histórico de vegetación | Compuestos de 16 días a 250 m | Mezcla superficies y fechas, sin detalle de sendero. https://lpdaac.usgs.gov/products/mod13q1v061/ |
| NASA/NOAA VIIRS FIRMS | Detecciones térmicas | Variable por sensor y geometría | Detección no es frente de fuego ni ausencia de detección garantiza ausencia de fuego. https://firms.modaps.eosdis.nasa.gov/ |
| NASA/ISRO NISAR | Cambios estructurales radar | Según producto y geometría | No mide fuego ni humedad de combustible directamente. https://nisar-docs.asf.alaska.edu/ |
| NASA LHASA | Contexto regional de deslizamientos | Modelo regional basado en múltiples factores | Verificar disponibilidad efectiva, versión, fechas, cobertura y evaluación local. No determina seguridad de sendero. https://github.com/nasa/LHASA |

Orden propuesto: 1) verificar disponibilidad GPM y SMAP en Concepción/Penco/Tomé para fechas conocidas y costos; 2) construir serie Sentinel-2 con máscara de nubes; 3) contrastar con estaciones y eventos independientes; 4) evaluar LHASA y cartografía local. Ninguna fuente autoriza por sí sola avisos operativos ni trayectorias de fuego.

La ficha de lluvia actual usa el endpoint histórico del pronóstico de Open-Meteo, no IMERG; los periodos terminan en el último día UTC completo, con control de faltantes. Evitar confundir salida de modelo con pluviómetro.
