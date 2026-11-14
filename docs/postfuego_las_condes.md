# PostFuego — Quebrada Honda (Las Condes): estado real, 14 noviembre 2026

Síntesis de esta sesión. El plan original y el glosario del equipo están en [docs/postfuego/01_problematica.md](postfuego/01_problematica.md) y [docs/postfuego/02_conceptos.md](postfuego/02_conceptos.md); léelos primero si no conoces el caso.

## 0. Aviso importante: dos líneas de trabajo en paralelo

Esta sesión (rama `main`) y otra sesión de Claude Code (rama remota `claude/relaxed-keller-ymtner`, PR [#1](https://github.com/ethan1213/sarwatch-nisar-2026/pull/1)) partieron del mismo commit (`e2fd61b`) y avanzaron **en paralelo sin comunicarse entre sí**. La otra rama construyó un módulo térmico (GOES-19, `sarwatch/ml/thermal.py`, `scripts/fetch_thermal.py`, `scripts/evaluate_fire.py`) y encontró que **FIRMS y LSA SAF están bloqueados desde esa máquina** y que casi no hubo fuego confiable en los recortes de Pantanal/Valparaíso/Metropolitana entre julio y noviembre de 2026; identificó Araucanía (track `003_A_159`) como el único sitio con foco térmico real y pasadas NISAR. Esta rama (la mía) construyó el módulo de incendio/aluvión en sí: dNBR, hidrología D8, umbral dinámico y lectura de interferometría GUNW.

**Las dos ramas tocan los mismos archivos centrales** (`app.py`, `sarwatch/maps.py`, `sarwatch/detections.py`, `CONTEXT.md`, `docs/estado.md`, `docs/guia_equipo.md`, `catalog/detection_reference.json`, `docs/detection_benchmark.json`, `models/pantanal_water_lgbm.card.json`). Fusionarlas a ciegas puede perder trabajo de cualquiera de las dos. **Esto lo debe resolver una persona revisando el PR**, no un merge automático. Mientras tanto, cada rama sigue siendo utilizable por separado.

## 1. Qué construyó esta rama

| Pieza | Archivo | Qué hace | Estado |
|---|---|---|---|
| Severidad de quema (dNBR) | `sarwatch/ml/wildfire.py`, `scripts/fetch_fire_dnbr.py` | NBR/dNBR de Sentinel-2 pre/post incendio, clases USGS | **Datos no usables todavía.** La primera corrida devolvió cobertura real de solo 0,08% del AOI (4.828 de 5.983.116 píxeles). Corregí un error real (SCL se remuestreaba con 'average', una categoría no debe promediarse) pero una segunda corrida con el remuestreo correcto dio el mismo 0,08%: la causa de fondo sigue sin resolver. Candidatos a investigar: la escena cubre solo ~27% del AOI por geometría de la tesela MGRS T19HCC (no explica una caída de 300×); revisar si `odc.stac` está leyendo una banda de baja resolución o un recorte equivocado; probar mosaico de varias teselas en vez de una sola escena. **No ejecutar `evaluate_postfire.py` hasta resolver esto**: el mapa de severidad actual (98,5% sin quemar, 1,5% baja, 0% alta) no es una medición real, es ruido de un recorte casi vacío. |
| Hidrología D8 | `sarwatch/ml/hydrology.py` | Dirección de flujo, acumulación y sub-cuencas desde el DEM, en una grilla reescalada a ~100 m | Implementado y probado (7 pruebas) |
| Umbral dinámico | `sarwatch/ml/debris_flow.py` | Umbral de lluvia en 30 min = base × quema × saturación × concentración × humedad NISAR | Implementado, heurístico y explícitamente no calibrado |
| Lectura de interferometría (GUNW) | `sarwatch/ml/interferometry.py` | Busca coherencia/fase desenrollada dentro de un .h5 GUNW por patrón de nombre, sin asumir una ruta fija | Implementado y probado; **nadie ha abierto un .h5 GUNW real todavía** |
| Evaluación conjunta | `scripts/evaluate_postfire.py` | Corre los tres escenarios (31-ene, 8-oct, esta semana) y escribe `docs/postfire_benchmark.json` / `catalog/postfire_reference.json` | Ejecutándose con datos reales de Metropolitana |
| Visor | `sarwatch/postfire.py` + `sarwatch/maps.py` | Capa de semáforo por escenario en el mapa de la Región Metropolitana | Integrado |
| Asistente | `sarwatch/assistant/tools.py::tool_postfire` | Responde con los umbrales de los tres escenarios | Integrado |
| Focos térmicos (complemento, fuera de NISAR) | `sarwatch/fire_hotspots.py` | Lector de FIRMS (VIIRS), opcional, necesita `FIRMS_MAP_KEY` propia | Implementado y probado; no descargó nada aún |

## 2. Lo que SÍ está verificado en CMR (no es el plan, es lo que confirmé consultando la API)

- **GUNW bracketea el 8 de octubre en tres tracks**, exactamente como dice el plan original:

| Track | Par | Peso |
|---|---|---|
| A75 (075_A_161) | 2026-10-05 → 2026-10-17 | 2,22 GB |
| A147 (147_A_161) | 2026-09-28 → 2026-10-10 | 2,20 GB |
| D169 (169_D_105) | 2026-09-29 → 2026-10-11 | 2,27 GB |

Guardado en `catalog/las_condes_gunw_candidates.json`. El par A75 es el más ajustado al evento. **Nadie los ha descargado todavía**: `python scripts/download_gunw.py` (pide tu Earthdata Login en tu propia terminal).

- **GCOV BETA (sin calibrar) cubre el incendio de dic-2025** en el mismo track que ya usamos (075_A_161): 2025-11-15 (antes), 2025-12-21 (durante/justo después), 2026-01-02 y 2026-01-14 (después). Guardado en `catalog/metropolitana_fire_beta_candidates.json`. Esto permitiría calcular ΔHV real de la cicatriz del incendio (cambio 1 del plan), algo que ni esta rama ni la otra han hecho todavía.

- **No existe NISAR entre el 19 de enero y el 19 de junio de 2026** sobre este track: confirma el hueco que señala el plan. El evento del 31 de enero sigue sin cobertura NISAR propia.

## 3. Lo que esta rama NO hizo (y por qué)

- **No calculó ΔHV de la cicatriz del incendio** (cambio 1 del plan): identifiqué las escenas BETA correctas pero no las descargué ni procesé. Es el siguiente paso más valioso.
- **No descargó ni leyó ningún GUNW real**: `sarwatch/ml/interferometry.py` está probado contra un archivo HDF5 sintético, no contra el producto real. La estructura interna exacta (nombres de grupos/datasets) se confirma solo al abrir el primer archivo.
- **El factor "carga del cauce" del umbral dinámico no usa coherencia todavía**: `debris_flow.py` solo combina quema + saturación + concentración de la cuenca + ΔHH; falta conectar la caída de coherencia una vez descargado el GUNW.
- **Las fechas del incendio en `fetch_fire_dnbr.py` son un ejemplo**, no la fecha/perímetro real confirmado por CONAF.

## 4. Aporte del experto (transcripción de audio, sin verificar por mí)

Un miembro del equipo (posiblemente del Centro Espacial) explicó por audio que el fuego también quema raíces y se propaga por el subsuelo, lo que debilita la cohesión del suelo (coincide con la "ventana de riesgo de 1 a 3 años" del plan) y que el **DEM es clave para entender si el incendio empezó en altura o en el suelo**, porque eso cambia el comportamiento del fuego (turbulencia térmica, propagación horizontal vs. ascendente) y por tanto la **logística de acceso** para apagarlo (ladera empinada = ruta más larga; terreno plano = acceso directo). Sugiere una capa de accesibilidad para brigadas, derivada de pendiente (ya la tenemos en `covariates/slope.tif`) y de la red vial (OSM, pendiente de integrar).

**Qué no afirmar** (regla ya vigente en el proyecto y repetida en el glosario, sección 17): el radar no ve raíces quemadas ni fuego subterráneo. Esa capa de accesibilidad describe terreno y rutas, no el subsuelo.

Idea concreta derivable, no implementada: `sarwatch/ml/hydrology.py` ya calcula pendiente y dirección de flujo; una capa "dificultad de acceso" = f(pendiente, distancia a camino OSM) es una extensión directa cuando haya tiempo.

## 5. Próximo paso recomendado, en orden

1. Descargar los tres GUNW (`python scripts/download_gunw.py`, tu Earthdata Login) y abrir uno con `h5py` para documentar la ruta real de `coherenceMagnitude` (actualiza `sarwatch/ml/interferometry.py` si la ruta no coincide con el patrón genérico).
2. Descargar las 4 escenas BETA de `metropolitana_fire_beta_candidates.json` y calcular ΔHV real pre/post incendio (cierra el cambio 1 del plan con NISAR real, no solo dNBR óptico).
3. Conectar la caída de coherencia al umbral dinámico (factor "carga del cauce").
4. Resolver con el propietario del repositorio cómo fusionar esta rama con el PR #1 (térmico/GOES): qué UI queda, qué catálogo de detección es el vigente.
5. **Depurar la cobertura casi nula del dNBR de Sentinel-2** (ver tabla arriba) antes de confiar en cualquier número de severidad de quema.
5. Confirmar con CONAF/Sernageomin la fecha y el perímetro reales del incendio de Las Condes y re-ejecutar `scripts/fetch_fire_dnbr.py` con esas fechas.

## 6. Honestidad obligatoria en cualquier presentación de esto

Repetido de `docs/postfuego/02_conceptos.md` §17 porque es fácil olvidarlo bajo presión de tiempo: no decir que el radar ve raíces; no atribuir toda la caída de coherencia al depósito (también hay humedad); no usar viviendas dañadas como medida de magnitud del flujo; no presentar dos eventos como modelo calibrado; no comparar tracks distintos; NISAR no puede quedar como capa decorativa.
