# Plan de cierre del MVP de incendios — para cualquier sesión (Opus, Sonnet u otra)

Entrega: **15 de noviembre de 2026, 11:00 (hora de Chile)**. Se presenta en vivo (2 minutos) y se entrega un video.
Rama de trabajo: `claude/happy-thompson-q4tmf9`. Lee este archivo completo antes de tocar nada; después `CONTEXT.md`.

Si eres un asistente de IA: toma **un solo paquete** de la sección 4, toca solo los archivos que ese paquete te asigna y termina con sus comprobaciones. No rehagas lo que la sección 1 marca como hecho.

## 1. Qué está hecho y comprobado (no repetir)

| Pieza | Dónde | Cómo comprobarlo |
|---|---|---|
| 9 escenas NISAR GCOV del cuadro `003_A_159` verificadas con MD5 oficial | `catalog/biobio_fuego_verified.json`, `catalog/concepcion_penco_verified.json` | Los JSON traen MD5 y SHA-256 por escena |
| Térmico GOES-19 horario, 1 ene–21 may 2026, y evaluación respuesta/anticipación | `docs/fire_benchmark_biobio.json` | `python -m unittest tests.test_fire_story -v` |
| Cicatriz de enero: severidad dNBR y radar quemado/no quemado | `docs/burn_scar_benchmark.json` | Igual |
| Paquete de la historia (cifras, celdas, capas PNG) | `catalog/fire_story/story.json` + 4 PNG | Igual |
| API de la historia y pronóstico de viento en vivo | `api/fire.py`, `weather.py` | Sección 3 |
| Despliegue desde Cloud Shell (escrito, **sin probar contra GCP**) | `scripts/deploy_cloudshell.sh`, `Dockerfile.update` | Paquete D |
| Detalle de método, cifras y errores corregidos | `docs/calor_y_focos.md` (sección del 15 nov) | — |

Los rásteres derivados (`data/`) **no están en Git ni en el bucket**: viven en la sesión que los generó. Por eso el visor nuevo lee solo `catalog/fire_story/`. Si un paquete necesita regenerar algo de `data/`, se pide a esa sesión; no se inventa ni se sustituye.

## 2. Reglas que valen para todos los paquetes

1. Ninguna cifra en pantalla, guion o texto sin su JSON de origen (tabla de la sección 6). Si no está en la tabla, no se dice.
2. No escribir «predicción de incendios», «riesgo», «zona segura», «por dónde entrar» ni «flanco seguro». El índice se llama **prioridad de vigilancia (exploratoria)** y siempre va con su métrica.
3. No decir que NISAR ve el fuego, la temperatura, el humo o las raíces. NISAR aporta estructura de la vegetación y la cicatriz posterior.
4. No hay imagen NISAR previa al incendio de enero en esta geometría (la serie empieza el 26 de febrero). Nunca rotular una comparación como «antes y después del incendio». Lo correcto: «bosque quemado frente a bosque sin quemar, después del incendio» y «evolución de febrero a octubre».
5. No mezclar BETA con PROVISIONAL ni geometrías distintas.
6. Viento y humedad: ERA5 es reanálisis (pasado) y Open-Meteo es pronóstico (modelo). Ninguno es medición en terreno; se rotula así.
7. Sin API de Claude ni otro LLM en el producto. Sin credenciales en el repo ni en el chat.
8. Commits sin líneas de coautoría de IA. Antes de cada commit: `python -m unittest discover -s tests` (114 pruebas, todas deben pasar).
9. Cifras de víctimas, viviendas y hectáreas del incendio, y el nombre del servicio forestal: solo con cita de la fuente oficial (SENAPRED, ley publicada). Hoy **no están verificadas** en el repo.

## 3. Contrato de la API (ya funciona; no cambiarlo sin avisar)

Levantar en local: `pip install -r requirements.txt -r requirements-maps.txt -r requirements-api.txt` y `python -m uvicorn api.main:app --port 8010`. Vite ya redirige `/api` a ese puerto.

| Ruta | Devuelve |
|---|---|
| `GET /api/fire/story` | Resumen liviano: `place`, `sources`, y por acto `before`, `during`, `after` sin geometrías |
| `GET /api/fire/story?part=before` | `cells` (GeoJSON, 2.547 celdas de unos 2 × 3 km), `passes`, `held_out_dates`, `latest_date`, `benchmark`, `limits` |
| `GET /api/fire/story?part=during` | `cells` (GeoJSON, 168 celdas), `frames`, `by_day`, `weather`, `limits` |
| `GET /api/fire/story?part=after` | `radar` (3 capas), `severity`, `area_km2`, `dates`, `limits` |
| `GET /api/fire/asset/{png}` | PNG de una capa listada en `after` |
| `GET /api/fire/forecast?lat=&lon=` | Pronóstico horario 48 h: `hourly.wind_speed_10m`, `wind_direction_10m`, `wind_gusts_10m`, `relative_humidity_2m`, `temperature_2m`, `vapour_pressure_deficit`, `precipitation_probability`, con `units` y `retrieved_utc` |
| `GET /api/chile/biobio/overview` | Focos VIIRS de los últimos 7 días (`firms`, GeoJSON de puntos) |

Campos que el frontend necesita:

- **before**: cada celda tiene `r20260427`, `r20260509`, `r20261012` (posición en el orden de esa pasada, 0 a 1; 1 = mayor prioridad) y `h20260427`, `h20260509` (1 si GOES vio calor confiable en los 12 días siguientes). Además `elev_m`, `slope_deg`, `trees`, `crops`, `grass`, `urban`. `passes[fecha]` trae `hot_next`, `hot_in_top_decile`, `top_decile_cells`. La pasada `2026-10-12` no tiene `h…`: no se puede comprobar.
- **during**: `frames[]` = `{t, cells[], frp_mw[]}`; `cells[]` son índices de `cells.features` (propiedad `i`). `weather.times[]` es horario y cada `weather.points[]` trae `lat`, `lon` y las series `wind_kmh`, `wind_from_deg` (dirección **desde** donde sopla), `gust_kmh`, `rh_pct`, `t_c`, `vpd_kpa` alineadas con `times`. Todo en UTC; Chile en enero es UTC−3.
- **after**: `radar[]` = `{date, png, bounds{west,south,east,north}, valid_fraction}`; `severity` = `{png, bounds, classes}`; `dates[]` trae `median_by_class` y `separation_high_vs_unburned` por fecha. Escala del radar: −24 a −6 dB (oscuro a claro).

## 4. Paquetes de trabajo

### Paquete A — Vista «Incendios» en React · **Opus**

Objetivo: una pantalla que cuente la historia en tres actos y sea lo primero que se ve al abrir la app.

Archivos propios (crear): `web/src/views/FireView.jsx`, `web/src/components/Fire*.jsx`, `web/src/fire.css`. Archivos compartidos que puede editar: `web/src/App.jsx` (añadir la región `incendios` como primera y por defecto) y `web/src/api.js` (añadir `fetchFire`). No tocar el resto de las vistas.

Pasos:

1. `cd web && npm ci`. Leer `web/src/components/SarMap.jsx` y `ThermalMap.jsx`: mismo patrón de MapLibre (`CONTEXT_STYLE`, fuentes `image` y `geojson`, `map.moveLayer('place-names')`).
2. Estructura: encabezado corto, tres pestañas grandes (**Antes · Durante · Después**), mapa ancho y un panel lateral con una cifra principal por acto. Fondo oscuro, un acento cálido (ámbar a rojo) para calor y uno frío para radar. Fuentes del proyecto en `static/fonts` (Bricolage Grotesque para títulos, Atkinson Hyperlegible para texto).
3. **Durante** (construir primero, es el más vistoso): control deslizante de tiempo con botón de reproducir sobre `frames`. Celdas activas en la hora en rojo intenso; celdas que ya tuvieron calor, en ámbar tenue. Flechas de viento en los 24 puntos de `weather.points`, apuntando **hacia donde va** el viento (`wind_from_deg + 180`), largo proporcional a `wind_kmh`. Panel: hora local, detecciones de esa hora, y del punto meteorológico más cercano a la celda elegida: viento, ráfaga, humedad, temperatura y VPD, con tres luces «30-30-30» (temperatura > 30 °C, humedad < 30 %, viento > 30 km/h) y pendiente y cobertura de la celda. Rótulo fijo: «Viento de reanálisis ERA5: orienta, no indica por dónde entrar».
4. **Después**: mapa con la capa de radar de la fecha elegida (3 fechas) y un comparador deslizante entre dos fechas (dos mapas sincronizados o `clip` sobre el contenedor). Botón para superponer `severity`. Panel: km² por clase (`area_km2.land_by_class`) y, para la fecha elegida, AUC de HV y de HH − HV (`separation_high_vs_unburned`). Texto: «Radar posterior al incendio; no hay pasada previa».
5. **Antes**: celdas coloreadas por `r<fecha>`; selector de pasada. En las dos fechas retenidas, contorno sobre las celdas con `h<fecha> = 1` («lo que ocurrió después»). Panel con las métricas de `benchmark` (`radar_terreno` frente a `persistencia`, bloques y fechas) y la frase del resultado real: en el 10 % de celdas con mayor prioridad cayeron `hot_in_top_decile` de `hot_next`. Rótulo: «Índice exploratorio».
6. En «Durante», modo «Hoy»: puntos VIIRS de `/api/chile/biobio/overview`; al elegir uno, `/api/fire/forecast` y la misma ficha de viento y humedad, rotulada «pronóstico».
7. Un solo aviso persistente («Prototipo: organiza evidencia, no es una alerta») y el detalle de límites (`limits`) en un `<details>`.

Hecho cuando: `npm run build` y `npm run lint` terminan sin avisos; con la API levantada, las tres pestañas cargan sin errores de consola; a 390 px de ancho no hay desborde horizontal; capturas de las tres pestañas adjuntas en el PR o en `docs/`.

No hacer: recalcular cifras en el navegador más allá de buscar el punto meteorológico más cercano y comparar contra 30; terreno 3D antes de terminar los tres actos; tocar `PantanalView`, `StudyView` o `ChileView`.

### Paquete B — Las Condes regenerado · **hecho** (15 nov, sesión con los datos)

El cálculo de severidad ignoraba el offset de 1000 de Sentinel-2 (ver `docs/calor_y_focos.md`). Se regeneraron, con las mismas escenas y ventanas, `catalog/postfire_reference.json`, `docs/postfire_benchmark.json`, `catalog/fire_impacts_reference.json` y `docs/fire_impacts_estimate.json`. Los cuatro rásteres pequeños que el visor superpone quedaron en `deploy_data/metropolitana/postfire/` para que la imagen publicada no mezcle cifras nuevas con mapas antiguos.

| Qué cambió | Antes | Ahora |
|---|---|---|
| Señal dNBR moderada o mayor en el recorte de Santiago | 1,5 % | 3,6 % |
| Superficie con señal de quema (clase baja o mayor) | 26.442 ha | 45.607 ha |
| CO₂ bruto del escenario (laboratorio experimental) | 86.876 t | 178.393 t |
| Umbral mediano de lluvia, 31 ene y 8 oct | 19,6 y 6,4 mm/30 min | sin cambio |

La clase «baja» del recorte completo incluye secado estival de noviembre a febrero: esas hectáreas y ese CO₂ no son un inventario del incendio (límite ya declarado en el visor).

Quien despliegue con `scripts/deploy_gcp.ps1` debe repetir en su copia local: `python scripts/fetch_fire_dnbr.py --aoi metropolitana && python scripts/evaluate_postfire.py && python scripts/estimate_fire_impacts.py`, y reconstruir con `-RebuildSnapshot`. Debe obtener las mismas cifras de la tabla.

### Paquete C — Guion, video y textos de entrega · **Sonnet**

Archivos propios (crear): `docs/entrega/guion_2min.md`, `docs/entrega/resumen_en.md`, `docs/entrega/uso_de_ia.md`. No tocar código.

1. Guion de 2:00 en español con marcas de tiempo, quién habla y qué pantalla se ve, siguiendo la sección 5. Cada cifra con su fila de la sección 6 entre paréntesis.
2. Resumen del proyecto en inglés (máximo 300 palabras): qué hace, cómo usa NISAR, datos complementarios, límites.
3. Declaración de uso de IA: se usaron asistentes de código (Claude Code y otros) para programar, revisar y documentar; ningún modelo de lenguaje corre dentro del producto; las cifras salen de scripts reproducibles.
4. Lista de fuentes con enlace: NISAR/ASF, GOES-19 NOAA, FIRMS, Sentinel-2/Planetary Computer, Copernicus DEM, WorldCover, Open-Meteo/ERA5.

Hecho cuando: el guion leído en voz alta dura entre 1:50 y 2:00 (unas 270 palabras), no contiene ninguna palabra vetada por la sección 2 y cada cifra coincide con su JSON.

### Paquete D — Publicación en GCP · **Sonnet + una persona con sesión de Google**

Camino 1 (preferido, completo): en el computador de Ethan, con los derivados locales, `git pull`, los tres comandos del paquete B y `scripts/deploy_gcp.ps1 -RebuildSnapshot`.

Camino 2 (desde el navegador, sin instalar nada): abrir https://console.cloud.google.com, activar **Cloud Shell**, clonar el repo (es privado: usar un token personal de GitHub o subir el `.tar.gz` del repo con el menú «Subir») y ejecutar:

```bash
git checkout claude/happy-thompson-q4tmf9
```

```bash
bash scripts/deploy_cloudshell.sh
```

El script reutiliza la imagen que el servicio ya tiene (con los derivados dentro) y reemplaza código, catálogo, web y los rásteres de `deploy_data/`. Si no existe servicio previo, publica la imagen sin instantánea: funcionan Incendios, Mundo y el resumen de Chile; Pantanal, Santiago y Valparaíso quedan sin capas hasta usar el camino 1. **Este script no se ha ejecutado contra GCP**: si un comando falla, copiar el error completo y corregir antes de reintentar; no cambiar la facturación ni los límites.

Hecho cuando: `python scripts/check_api.py <URL>` pasa (camino 1) o, en el camino 2 sin instantánea, `/api/health`, `/api/fire/story` y la portada responden 200 desde otra red. Durante la evaluación: `MIN_INSTANCES=1 bash scripts/deploy_cloudshell.sh`; después volver a 0.

### Paquete E — README, licencia y control final · **Sonnet**

Archivos propios: `README.md`, `LICENSE` (solo si el propietario ya eligió: Apache-2.0 o MIT), `CLAUDE.md` (sección de estado), `CONTEXT.md` (resultados vigentes).

1. Reescribir el README: hoy mezcla estados antiguos (siete fechas, Streamlit). Dejar: qué es, enlace a la app, cómo correr API y web, fuentes, límites, enlace a este plan y a `docs/calor_y_focos.md`.
2. Control final: 114 pruebas, `npm run build`, `npm run lint`, y que ninguna palabra vetada aparezca en `web/src` (`grep -rniE "predicci[oó]n de incendios|zona segura|flanco seguro" web/src` debe salir vacío).
3. Confirmar con el propietario la visibilidad del repo: el desafío pide código abierto.

## 5. Arco de la presentación (2:00)

| Tiempo | Pantalla | Idea |
|---|---|---|
| 0:00–0:15 | Durante, reproducción del 17 al 19 de enero | El relato de quien estuvo en Tomé |
| 0:15–0:45 | Durante, hora de mayor actividad, ficha de viento | El día con más calor detectado coincidió con calor, aire seco y viento fuerte |
| 0:45–1:15 | Después, comparador febrero–octubre con severidad | El radar distingue el bosque quemado a través de nubes y humo, meses después |
| 1:15–1:40 | Antes, fecha retenida con «lo que ocurrió» | Probamos anticipar; el resultado honesto y qué falta |
| 1:40–2:00 | Vista Mundo | Misma app en Pantanal, Santiago y Valparaíso; código abierto |

## 6. Cifras que se pueden decir y su origen

| Cifra | Valor | Archivo y clave |
|---|---|---|
| Detecciones GOES confiables, ventana Biobío, 1 ene–21 may | 2.492 | `docs/fire_benchmark_biobio.json` → `hotspots.confident_detections` |
| Detecciones confiables el 18 de enero (ventana Biobío) | 965 | `catalog/fire_story/story.json` → `during.by_day` |
| Celdas con calor en el evento de enero | 168 | `story.json` → `during.cells_hot` |
| Señal de quema moderada o mayor sobre tierra, Concepción/Penco | 185,7 km² (alta: 80,4) | `docs/burn_scar_benchmark.json` → `area_km2.land_by_class` |
| Radar HV separa bosque de severidad alta del no quemado | AUC 0,69 (26 feb), 0,51 (14 jun), 0,71 (12 oct) | `burn_scar_benchmark.json` → `dates[].separation_high_vs_unburned.hv_db.auc` |
| Igual con HH − HV | 0,59, 0,64, 0,67 | misma ruta, `hh_menos_hv_db` |
| Prioridad de vigilancia, fechas retenidas | AUC 0,63 frente a 0,49 de la persistencia, 44 celdas con calor | `fire_benchmark_biobio.json` → `anticipation.models.*.held_out_dates` |
| Igual, bloques espaciales retenidos | 0,89 frente a 0,61 | misma ruta, `spatial_blocks` |
| Aciertos en el 10 % de mayor prioridad | 1 de 13 (27 abr) y 3 de 31 (9 may): no mejor que el azar | `story.json` → `before.passes` |
| Índice mundial NISAR | 158.639 granulos (el texto de `docs/` dice 163.672: usar el del JSON) | `catalog/global/coverage_1deg.json` → `granules_indexed` |

Condiciones del 18 de enero (temperatura, humedad, viento, ráfaga): leerlas en pantalla desde `during.weather` para la hora mostrada; no citarlas de memoria.

## 7. Respuesta a la conversación compartida por Candela

| Lo que plantea | Qué dicen los datos del repo | Qué hacer |
|---|---|---|
| Caso Penco–Tomé con NISAR «antes y después» | No existe: la serie comparable empieza el 26 de febrero; las escenas BETA son de otra órbita y no cubren la ventana urbana (`catalog/chile_nisar_audit.json`) | Mostrar quemado frente a no quemado y la evolución feb–oct |
| El incendio empezó el 17 de enero | GOES concentra el calor entre el 17 y el 22, con máximo el 18: coincide | Decir «según GOES»; la fecha oficial se cita aparte |
| Índice combustible × pendiente × viento que indique por dónde atacar | No hay validación y `docs/fuentes_biobio_y_experiencia.md` ya lo descarta | Ficha con viento, humedad, pendiente y cobertura, sin recomendación táctica |
| Flujo del jefe de brigada en tres pantallas | Encaja con Antes · Durante · Después | Es el paquete A |
| CO₂ = área × biomasa × fracción × 0,47 × 3,67 | El repo usa el método IPCC 2006 por defecto y lo marca como no validado; la biomasa por banda L no está calibrada aquí | Como mucho una cifra en el laboratorio existente; no en el pitch |
| Viña del Mar 2024 | NISAR se lanzó en 2025: no hay escenas de ese incendio. El repo tiene Valparaíso con dos fechas de octubre de 2026 | Viña solo como «estado actual»; nunca «NISAR 2024» |
| 40.000 ha, 2.098 viviendas, 21 fallecidos; Ley 21.744 y SERNAFOR | Sin verificar en el repo | Citar la fuente oficial o no usar |
| El video de Tomé | Material propio del equipo | Abre el pitch y el video |

## 8. Orden y cortes

1. Ahora: A (Opus) y C (Sonnet) en paralelo; B ya está cerrado.
2. Cuando A tenga «Durante» y «Después»: D publica; E corre el control final.
3. Tres horas antes de la entrega se congela el código y se graba el video.

Si falta tiempo se recorta en este orden: modo «Hoy», acto «Antes» (queda como tarjeta con las cifras), animación de flechas (flechas fijas). No se recorta: «Durante» con reproducción, «Después» con comparador, URL pública o video de respaldo grabado en local.
