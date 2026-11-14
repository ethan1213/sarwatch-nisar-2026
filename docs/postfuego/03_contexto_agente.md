# PostFuego — Contexto para agente

Archivo de contexto para un agente de IA (por ejemplo, Claude Code como CLAUDE.md). Léelo completo antes de escribir código. Documentos relacionados: [01_problematica.md](01_problematica.md) (el porqué) y [02_conceptos.md](02_conceptos.md) (glosario técnico). Estado real de lo implementado: [../postfuego_las_condes.md](../postfuego_las_condes.md).

## Objetivo

Construir una aplicación web interactiva que use datos de radar NISAR (banda L) para seguir y visualizar el cambio superficial en una ladera quemada, desde el incendio hasta el aluvión.

- Desafío: NASA Space Apps Challenge — "build an interactive application that uses radar remote sensing data from NISAR to track and visualize one or more types of surface change at locations around the world".
- Caso principal: quebrada Honda, Las Condes / Lo Barnechea, Santiago, Chile.
  - Incendio: diciembre de 2025.
  - Aluvión menor: 31 de enero de 2026.
  - Aluvión mayor: 8 de octubre de 2026.
- Tiempo disponible: ~20 horas.

## Jerarquía del producto (no alterar)

1. Núcleo: visor NISAR con línea de tiempo de tres cambios superficiales.
2. Valor agregado: panel de umbral dinámico de lluvia (se recorta primero si falta tiempo).
3. Extensión: segundo sitio para cumplir "locations around the world".

NISAR nunca queda como capa decorativa ni opcional.

## Los tres cambios a mostrar

| # | Cambio | Fechas | Producto | Señal | Prioridad |
|---|---|---|---|---|---|
| 1 | Cicatriz del incendio | Pre vs. post incendio (BETA, dic–ene) | GCOV | ΔHV en dB (debe caer) | Máxima: asegurar primero |
| 2 | Humedecimiento del suelo | Antes vs. después del 6–7 oct | GCOV | ΔHH en dB (debe subir sobre zona quemada) | Alta |
| 3 | Huella del aluvión | Par que cubre el 8 oct | GUNW | Caída de coherencia en el cauce | Alta |

Hito de corte (17:00): si no hay ΔHH legible, seguir con cambios 1 y 3. No reemplazar NISAR por lluvia y quema.

## Datos

| Dato | Estado | Notas |
|---|---|---|
| NISAR GCOV/GUNW antes y después del 8-oct | Verificado en ASF | Tracks A147 (prioritario), A75, D169 |
| NISAR antes y después del incendio | Verificado | Productos BETA, sin calibración final |
| NISAR 19-ene a 19-jun-2026 | No existe | El evento del 31-ene se trata solo con óptico y lluvia |
| Lluvia 30 min DGA (Parque El Arrayán, Río Molina) | Publicada en análisis CR2 y prensa | Descargar serie de enero y octubre |
| GPM IMERG | Libre (NASA) | Precipitación cada 30 min, ~10 km |
| HLS / Sentinel-2 (dNBR) | Libre | Nubes en invierno |
| Copernicus DEM 30 m | Libre | Pendiente, subcuencas, dirección de flujo |
| OpenStreetMap | Libre | Viviendas, calles, ductos aguas abajo |
| Recorrido del aluvión | asdr.cl, hirely.cl | Solo validación; citar siempre |

Acceso NISAR: cuenta NASA Earthdata + ASF DAAC. Usar asf_search (Python) para listar productos por track, fecha y área.

## Notas técnicas

### Lectura de HDF5

- Usar h5py para explorar la estructura antes de asumir rutas internas. Empezar con `f.visit(print)`.
- Rutas esperadas (verificar en el archivo real):
  - GCOV: `/science/LSAR/GCOV/grids/frequencyA/HHHH`, `.../HVHV`
  - GUNW: grupo de interferograma desenrollado, con capa de magnitud de coherencia
- Alternativa: `gdalinfo` sobre el subdataset HDF5 específico.
- Leer los metadatos de proyección (EPSG, espaciado de grilla) del propio archivo.

### Procesamiento

- Convertir potencia lineal a dB: `10 * log10(valor)`. Enmascarar ceros y no-datos antes del logaritmo.
- Solo comparar fechas del mismo track.
- Reducir speckle: promediar ventanas o comparar estadísticas por zona (cuenca quemada vs. ladera intacta de control), no píxeles sueltos.
- Recortar al área de interés antes de procesar para ahorrar memoria.
- Revisar escorzo y sombra en laderas empinadas. Si un track deja la quebrada en sombra, usar el opuesto (ascendente/descendente).

### Umbral dinámico (versión mínima, 2–3 h)

- API (lluvia antecedente): `API_t = k * API_{t-1} + P_t`, con k entre 0,85 y 0,95 diario. Documentar el valor elegido.
- M1 USGS con intensidad de 30 min, pendiente, severidad (dNBR) y erodabilidad. Calcularlo para ambos eventos; no suponer el resultado.
- Factor de saturación: reducir el umbral M1 en función del API. Presentarlo como hipótesis calibrable.
- Salida: semáforo por quebrada y el texto "con el suelo como está, bastan X mm en 30 min".

### Aplicación web

- Mapa interactivo (Leaflet o MapLibre) con:
  - Capas NISAR: ΔHV, ΔHH y coherencia, con leyenda en dB o 0–1.
  - Línea de tiempo dic-2025 → oct-2026 con los tres cambios.
  - Control de comparación antes/después.
  - Capa de exposición (OSM): viviendas y calles aguas abajo.
  - Panel de umbral dinámico.
- Exportar rásters como GeoTIFF o PNG georreferenciado (COG si es posible) para la web.
- Textos explicativos para público no experto: el objetivo es acercar el radar.
- Debe aceptar otra área de interés (pipeline parametrizado por bbox y fechas).

## Orden de trabajo

1. Credenciales Earthdata y abrir un GCOV de A147 (h5py).
2. Con asf_search, identificar qué par termina antes del 6-oct y cuál cubre el 8-oct.
3. ΔHV pre vs. post incendio sobre la quebrada (cambio 1).
4. Esqueleto del mapa web con línea de tiempo.
5. ΔHH (cambio 2) y coherencia (cambio 3).
6. Subcuencas y pendiente desde el DEM; dNBR.
7. Serie de lluvia 30 min (DGA e IMERG); gráfico intensidad vs. lluvia previa para ambos eventos.
8. Panel de umbral dinámico.
9. Segundo sitio (solo cicatriz HV), dentro del período NISAR (posterior a julio de 2025).

## Reglas de honestidad científica (obligatorias en código, textos y gráficos)

- No afirmar que el radar ve raíces o fuego subterráneo.
- No atribuir toda la caída de coherencia del 8-oct al depósito: el par mezcla humedad y depósito.
- No usar daño (viviendas) como medida de magnitud del flujo.
- Dos eventos no calibran un modelo: rotular como "prueba de concepto calibrable".
- Etiquetar los productos BETA como no calibrados.
- Citar fuentes en la app: asdr.cl, hirely.cl, DGA, CR2, Sernageomin, Senapred.

## Definición de "terminado"

- [ ] Al menos un cambio NISAR (cicatriz HV) visible en el mapa con leyenda.
- [ ] Línea de tiempo funcional.
- [ ] Comparación antes/después.
- [ ] Capa de exposición.
- [ ] Textos para público no experto.
- [ ] Fuentes citadas en la interfaz.
- [ ] Pipeline reutilizable en otra área.
- [ ] (Deseable) Panel de umbral dinámico.
- [ ] (Deseable) Segundo sitio.
