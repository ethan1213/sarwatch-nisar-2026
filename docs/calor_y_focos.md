# Calor y focos: térmico GOES + radar NISAR + terreno

Estado al 14 nov 2026. Cifras de `docs/fire_benchmark.json`, `catalog/thermal_reference.json`, `catalog/hotspot_scan.json` y `catalog/hotspot_scan_chile_verano.json`.

## Qué mide cada sensor (y qué no)

| Fuente | Qué aporta | Resolución | Qué no hace |
|---|---|---|---|
| GOES-19 ABI, banda 7 (3,9 µm, infrarrojo medio) y banda 14 (11,2 µm, infrarrojo térmico) | Temperatura de brillo; la diferencia entre ambas delata superficies muy calientes | 2 km en el nadir (2,2 km en Pantanal, 2,1 × 2,6 km en Chile central), cada 10 min | No ve bajo nubes; de día el canal de 3,9 µm incluye sol reflejado |
| GOES-19 `ABI-L2-FDCF` | Foco de calor por píxel, con clase de confianza, potencia radiativa y temperatura | Igual | Un foco es una anomalía dentro del píxel: no da posición fina ni confirma incendio |
| GOES-19 `ABI-L2-LST2KMF` | Temperatura de superficie horaria, solo con cielo despejado | 2 km | No existe bajo nube |
| NISAR GCOV HH/HV (banda L) | Estructura y humedad de la vegetación antes del fuego; cambio de la señal después | 20 m, cada 12 días | **No mide temperatura y no detecta fuego activo** |
| DEM Copernicus, WorldCover | Elevación, pendiente y cobertura dentro de cada celda térmica | 30 m y 10 m | Son estáticos |

"SAF": los productos de fuego de EUMETSAT LSA SAF salen de Meteosat, que no observa Chile y ve el Pantanal en el borde del disco. Su equivalente para América es GOES-19, que es lo que usamos.

## Qué hay construido

1. `scripts/fetch_thermal.py --aoi <sitio> --start … --end …` lee solo la ventana del AOI con peticiones HTTP por rango (sin credenciales) y escribe `data/<sitio>/thermal/{cube.npz,hotspots.json,manifest.json}`.
2. `scripts/evaluate_fire.py --aoi <sitio>` asigna cada píxel NISAR a su celda GOES (`zones.tif`), agrega HH/HV, elevación, pendiente y cobertura por celda (`zones.json`) y evalúa dos preguntas en bloques espaciales y fechas retenidos:
   - **Respuesta:** ¿cambia HV de otro modo en las celdas donde GOES vio calor entre dos pasadas?
   - **Anticipación:** ¿se puede adelantar qué celdas tendrán un foco en los 12 días siguientes a una pasada, y agregan algo el radar y el terreno frente a repetir dónde hubo calor?
3. `scripts/scan_hotspots.py --bbox W S E N --start … --end …` cuenta focos confiables por celda de 0,25° y los cruza con el índice mundial NISAR: sirve para elegir sitio antes de descargar nada.
4. Vista «Calor y focos» en la app (`sarwatch/views/thermal.py`): mapa de celdas térmicas con nueve capas (focos, temperatura de superficie, 3,9 µm, 11,2 µm, su diferencia, HV, cambio de HV, pendiente, elevación), período ajustable o entre pasadas NISAR, serie de temperaturas y de radar de la celda elegida, y tabla de las celdas más activas.

La unidad de análisis es la celda térmica, no el píxel de 20 m: el calor solo se conoce a esa escala.

## Qué encontramos

| Recorte | Período térmico | Pasos horarios | Detecciones de foco | De ellas confiables | Celdas con algún foco | Nube |
|---|---|---|---|---|---|---|
| Pantanal | 1 jul – 13 nov 2026 | 3212 | 41 | 7 | 26 | 22 % |
| Región Metropolitana | 1 jul – 13 nov 2026 | 3212 | 10 | 0 | 1 | 59 % |
| Región de Valparaíso | 1 jul – 13 nov 2026 | 3212 | 0 | 0 | 0 | 65 % |

Con una sola celda con foco confiable y radar entre dos pasadas, **ninguna de las dos preguntas se puede evaluar en los recortes actuales**. El script lo registra y la app no muestra ninguna predicción. Los diez focos de la Región Metropolitana son de probabilidad baja y caen siempre en la misma celda: es más probable una fuente fija o una falsa alarma que vegetación ardiendo (hipótesis, sin verificar).

Dónde sí hubo calor:

- **Araucanía** (−73,0 −38,75 −72,0 −38,0), enero–junio 2026: 718 detecciones confiables en 12 celdas de 0,25°, 405 en marzo y 131 en abril. Hay 7 pasadas NISAR de la misma geometría entre el 26 feb y el 9 may (11,7 GB), ya listadas en `catalog/araucania_candidates.json`.
- **Biobío–Ñuble** (−72,5 −37,5 −71,75 −36,5): 648 detecciones confiables, 197 en marzo y 269 en abril.
- **Dentro de la escena de Pantanal ya descargada**, fuera del recorte de 0,5°: 5 celdas de 0,25° con al menos 20 detecciones confiables entre julio y noviembre (183 en total); la mayor, con 82, toca el borde este del recorte actual (−57,0 −17,25). Cambiar el recorte no exige descargar nada.

Que marzo y abril concentren los focos del sur sugiere quemas agrícolas tras la cosecha más que incendios forestales (hipótesis).

## Qué sigue

```powershell
python scripts/download_scenes.py --candidates catalog/araucania_candidates.json --target data_raw/araucania   # requiere Earthdata Login
python scripts/request_aoi.py prepare --name araucania
python scripts/fetch_covariates.py --aoi araucania
python scripts/fetch_thermal.py --aoi araucania --start 2026-02-14 --end 2026-05-21
python scripts/evaluate_fire.py --aoi pantanal valparaiso metropolitana araucania
```

Luego: focos VIIRS de 375 m (FIRMS, con clave del operador) como segunda fuente; viento y humedad del aire (ERA5); área quemada óptica (dNBR Sentinel-2) como etiqueta independiente; FDC cada 10 minutos en vez de cada hora. Una capa de predicción entra al visor solo si supera a la persistencia en bloques y fechas retenidos y tiene tarjeta de modelo.

## Límites

- Una observación por hora subestima los focos breves.
- La nube oculta el calor: 22 % de las observaciones en Pantanal y más de la mitad en Chile central en invierno y primavera.
- El barrido de sitios muestrea seis horas de la tarde: es un piso de la actividad, no un inventario.
- No se afirma incendio, área quemada ni riesgo. Un foco orienta dónde mirar con otras fuentes.

## Actualización 15 nov 2026: Biobío con datos reales

Cifras de `docs/fire_benchmark_biobio.json`, `catalog/thermal_reference_biobio.json`, `docs/burn_scar_benchmark.json`, `catalog/biobio_fuego_verified.json` y `catalog/concepcion_penco_verified.json`.

**El plan de Araucanía de más arriba no sirve tal como estaba.** El cuadro `003_A_159` termina cerca de los 38,25° S: el recorte `araucania` (−73,0 −38,75 −72,0 −38,0) queda cubierto en un 16 %. El mismo cuadro sí cubre completo Biobío y Ñuble, así que el recorte de trabajo es `biobio_fuego` (−73,3 −37,5 −71,75 −36,5), que reúne los focos de enero en la costa y los de marzo–abril en el valle.

Descargado y verificado con el MD5 oficial de CMR: nueve escenas GCOV PROVISIONAL de esa geometría (26 feb, 10 y 22 mar, 3, 15 y 27 abr, 9 may, 14 jun y 12 oct de 2026; 15,95 GB). El 26 de febrero y el 15 de abril tienen dos franjas sin dato válido (69 % de cobertura en `biobio_fuego`, 78 % en `concepcion_penco`); el resto, 100 %.

| Qué | Resultado |
|---|---|
| Térmico GOES-19, 1 ene – 21 may, horario | 3.219 detecciones en `biobio_fuego`, 2.492 confiables, 101 días con focos, 479 celdas con foco confiable y radar; 0 fallos de lectura |
| Fecha del evento de enero (sale de GOES, no de una fuente oficial) | Detecciones confiables en Concepción/Penco concentradas entre el 17 y el 22 de enero; 707 el día 18 |
| Severidad dNBR Sentinel-2 en Concepción/Penco (10 dic–16 ene frente a 23 ene–27 feb) | Sobre tierra: 185,7 km² de señal moderada o mayor, 80,4 km² alta. No es un perímetro oficial |
| Radar en bosque quemado frente a bosque sin quemar (corte transversal, sin pasada previa) | HV separa severidad alta de sin quema con AUC 0,69 (26 feb), 0,51 (14 jun) y 0,71 (12 oct); HH − HV, 0,59, 0,64 y 0,67. Los cinco pliegues espaciales coinciden |
| Respuesta del radar al calor entre pasadas (celdas de 2 km) | En el par con más calor (22 mar → 3 abr, 179 celdas) AUC 0,70; en los demás pares, entre 0,30 y 0,52. Conjunto centrado por par: 0,62 |
| Anticipación a 12 días, bloques espaciales retenidos | Radar y terreno AUC 0,89; todo 0,90; persistencia 0,61 |
| Anticipación a 12 días, fechas retenidas (27 abr y 9 may, 44 celdas con calor) | Radar y terreno AUC 0,63; todo 0,61; persistencia 0,49; precisión media 0,016–0,020 con prevalencia 0,009 |

Lectura. El radar y el terreno ordenan mejor que repetir dónde hubo calor, pero en fechas nuevas la ventaja es pequeña y descansa en 44 casos: no alcanza para llamar a la capa predicción de incendios. El resultado alto en bloques espaciales refleja sobre todo geografía estable (dónde hay cultivo y dónde bosque). La mayoría de los focos de marzo y abril caen en fechas de quema agrícola (hipótesis sin verificar); falta separar por cobertura.

Tres correcciones de método hechas en esta corrida:

- `scripts/fetch_fire_dnbr.py` calculaba NBR sobre números digitales sin restar el offset de 1000 que Sentinel-2 L2A lleva desde la versión de procesamiento 04.00. Eso comprime el dNBR y baja la severidad: en Concepción/Penco la señal moderada o mayor pasaba de 0,5 % a 7,8 % de los píxeles válidos con las mismas escenas. **Los resultados de Las Condes (`postfire_*`, `fire_impacts_*`) se generaron con la versión anterior y hay que regenerarlos.**
- El mismo script elegía las seis escenas menos nubosas, que podían ser franjas angostas: la ventana posterior cubría el 60 % del recorte y dejaba fuera el 91 % de la tierra dentro de las celdas con calor. Con `--max-items 16` cubre el 99 %.
- `scripts/evaluate_fire.py` juntaba los cambios de todos los pares sin centrar: un cambio estacional entre dos pasadas contaba como separación. El conjunto anterior (AUC 0,79) estaba inflado; centrado por par da 0,62.

También quedó descargado el tiempo horario ERA5 (viento, ráfagas, humedad relativa, temperatura, déficit de presión de vapor y lluvia) para `biobio_fuego` con `scripts/fetch_fire_weather.py`; aún no entra como variable del modelo.

Reproducir:

```bash
python scripts/request_aoi.py prepare --name biobio_fuego          # originales en data_raw/biobio_fuego
python scripts/fetch_covariates.py --aoi biobio_fuego
python scripts/fetch_thermal.py --aoi biobio_fuego concepcion_penco --start 2026-01-01 --end 2026-05-21
python scripts/fetch_fire_weather.py --aoi biobio_fuego --start 2026-01-01 --end 2026-05-21
python scripts/evaluate_fire.py --aoi biobio_fuego --benchmark docs/fire_benchmark_biobio.json --reference catalog/thermal_reference_biobio.json
python scripts/fetch_fire_dnbr.py --aoi concepcion_penco --pre-start 2025-12-10 --pre-end 2026-01-16 --post-start 2026-01-23 --post-end 2026-02-27 --max-items 16
python scripts/evaluate_burn_scar.py --aoi concepcion_penco
```
