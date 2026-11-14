# PostFuego — Conceptos a manejar

Glosario de trabajo para el equipo. Cada concepto incluye qué es, por qué importa para PostFuego y, cuando aplica, qué no se debe afirmar.

## 1. Teledetección

Observar la Tierra sin contacto, desde satélites o aviones.

- Sensores pasivos (ópticos): Sentinel-2, Landsat. Miden la luz solar reflejada. Necesitan sol y cielo despejado.
- Sensores activos (radar): emiten su propia señal y miden el eco. Funcionan de día, de noche, con nubes y con humo.

Para PostFuego: el radar puede observar la quebrada en pleno temporal, cuando el óptico solo ve nubes.

## 2. SAR — Radar de apertura sintética

Un radar que, al moverse el satélite, combina los ecos recibidos de un mismo punto para simular una antena gigante y lograr alta resolución. Clave: mira de lado, no hacia abajo (ver concepto 12).

## 3. NISAR

Misión conjunta NASA–ISRO, lanzada en julio de 2025.

- Banda L (NASA): cobertura global. Es la que usaremos para Chile.
- Banda S (ISRO): adquisiciones concentradas en India y zonas seleccionadas (verificar cobertura antes de considerarla).
- Revisita: cada 12 días sobre el mismo punto.
- Distribución: ASF DAAC, con cuenta NASA Earthdata.

## 4. Longitud de onda y bandas

| Banda | Longitud de onda | Comportamiento |
|---|---|---|
| L | ~24 cm | Atraviesa hojas; interactúa con troncos, ramas y suelo |
| S | ~10 cm | Intermedio |
| C (Sentinel-1) | ~5,6 cm | Se queda más en la copa |

Para PostFuego: la banda L "siente" la estructura del bosque y la humedad del suelo. Sin vegetación, ve el suelo con más claridad, lo que favorece la señal de humedad justo en la zona quemada.

## 5. Retrodispersión (backscatter)

La fracción de la energía emitida que vuelve al satélite. Píxel brillante = mucha energía de vuelta. Se expresa como σ⁰ o γ⁰ (gamma-cero, corregido por el ángulo del terreno) y se mide en decibeles (dB), escala logarítmica: −3 dB = la mitad de energía; −10 dB = una décima parte. ΔdB = diferencia de brillo entre dos fechas.

Factores que la controlan: rugosidad de la superficie respecto de la longitud de onda; humedad (el agua aumenta mucho la reflectividad del suelo); estructura (vegetación, paredes).

## 6. Mecanismos de dispersión

| Mecanismo | Dónde ocurre | Cómo se ve |
|---|---|---|
| Especular (espejo) | Agua lisa, superficies muy suaves | Muy oscuro: la energía rebota lejos del satélite |
| Superficie | Suelo desnudo | Intermedio; sube con la humedad |
| Volumen | Copa de árboles, follaje | Fuerte en polarización HV |
| Doble rebote | Paredes, árboles en agua | Muy brillante |

Para PostFuego: incendio → la ladera pasa de volumen a superficie → cae HV. Lluvia → la superficie se vuelve más reflectiva → sube HH.

## 7. Polarización (HH, HV)

La orientación de la onda emitida y recibida (H = horizontal, V = vertical).

- HH: emite H, recibe H. Responde a superficie y doble rebote. Sensible a la humedad del suelo.
- HV: emite H, recibe V. Aparece cuando la onda rebota muchas veces en estructuras desordenadas. Indicador de vegetación.

Para PostFuego: HV para la cicatriz del incendio; HH para el humedecimiento.

## 8. Fase e interferometría (InSAR)

El radar registra amplitud (cuánta energía volvió) y fase (en qué punto del ciclo llegó la onda). Comparar la fase de dos pasadas permite medir desplazamientos de milímetros a centímetros. El resultado se llama interferograma. Usos típicos: terremotos, hundimientos, glaciares.

## 9. Coherencia

Cuánto se parece la fase entre dos fechas, en una escala de 0 a 1.

- Alta: la superficie no cambió (roca, edificios, caminos).
- Baja: algo se reorganizó (vegetación, arado, nieve, agua, aluvión).

Para PostFuego: la caída de coherencia a lo largo del cauce es la huella del aluvión.

**No afirmar:** que la caída de coherencia del 8 de octubre se debe solo al depósito. En ese par también influye la humedad de las lluvias del 6 y 7. Presentarla como huella del cambio.

## 10. DEM — Modelo digital de elevación

Un mapa de alturas del terreno, del que se derivan pendiente, cuencas y dirección de flujo. Usaremos el Copernicus DEM (30 m), generado con interferometría de radar (misión TanDEM-X). Se puede decir con propiedad que el modelo de terreno también es SAR.

**No hacer:** generar un DEM propio con NISAR durante la hackathon. Con 12 días entre pasadas la señal se degrada y el procesamiento es largo.

## 11. Moteado (speckle)

La textura granulada propia de las imágenes de radar, por interferencia entre ecos dentro de cada píxel. Es física, no un error.

Para PostFuego: comparar zonas (cuenca quemada vs. ladera intacta), no píxeles sueltos. Promediar antes de interpretar.

## 12. Geometría lateral: escorzo y sombra

Como el radar mira de lado, en montaña: las laderas que miran al satélite se comprimen y brillan de más (escorzo o layover); las que le dan la espalda pueden quedar en sombra, sin dato.

Para PostFuego: la quebrada está en la precordillera. Conviene combinar órbitas ascendentes y descendentes, que miran desde lados opuestos.

## 13. Órbitas y tracks

- Ascendente (A): el satélite pasa de sur a norte.
- Descendente (D): de norte a sur.
- Track: recorrido repetible numerado. A147 = ascendente, track 147.

Regla: solo se comparan imágenes del mismo track, porque la geometría de observación debe ser idéntica. Tracks verificados para el caso: A147, A75, D169.

## 14. Productos NISAR

Formato HDF5 (.h5). Descarga desde ASF con cuenta Earthdata.

| Producto | Contenido | Uso en PostFuego |
|---|---|---|
| GCOV (geocoded covariance) | Retrodispersión en HH, HV, etc., geocodificada y corregida por terreno | Cicatriz HV, humedecimiento HH |
| GUNW (geocoded unwrapped interferogram) | Interferograma entre dos fechas, desplazamiento y coherencia | Huella del aluvión |

## 15. Conceptos del lado del riesgo

- **Remoción en masa / aluvión / flujo de detritos:** movimiento de suelo, roca y agua ladera abajo. Un flujo de detritos post incendio mezcla agua con sedimento suelto y baja por el cauce.
- **Severidad de quema y dNBR:** índice óptico que compara el estado de la vegetación antes y después del incendio (con Sentinel-2 o HLS). Complementa la señal HV de NISAR.
- **Modelo M1 (USGS):** modelo empírico que estima la probabilidad de flujo de detritos post incendio a partir de la intensidad de lluvia de corta duración (15 o 30 min), la pendiente, la severidad de quema y la erodabilidad del suelo. Fue desarrollado para el oeste de EE. UU. con lluvias convectivas.
- **Lluvia antecedente (API):** índice que acumula la lluvia de los días previos, con peso decreciente hacia atrás. Representa cuán saturado está el suelo.
- **Umbral dinámico:** umbral de lluvia de gatillo que baja cuando el suelo está saturado (API alto) y cuando el cauce tiene sedimento acumulado.
- **Raíces quemadas:** el fuego puede avanzar por el subsuelo y quemar raíces. Al quemarse y pudrirse, el suelo pierde cohesión, lo que ayuda a explicar la ventana de riesgo de 1 a 3 años.

**No afirmar:** que el radar ve las raíces quemadas. Mide efectos en superficie.

- **"No eventos":** lluvias sobre la cicatriz que no produjeron aluvión. Son necesarias para acotar un umbral.

## 16. Otras fuentes NASA que suman relevancia

| Fuente | Qué aporta |
|---|---|
| GPM IMERG | Precipitación global cada 30 minutos (resolución gruesa, ~10 km) |
| HLS (Harmonized Landsat Sentinel-2) | Óptico con más fechas, para dNBR |
| SMAP | Humedad del suelo (9 km: contexto, no dato de la quebrada) |

## 17. Errores a evitar frente al jurado

- Decir que el radar ve raíces o fuego subterráneo.
- Atribuir toda la caída de coherencia del 8-oct al depósito.
- Usar el daño (viviendas) como medida de la magnitud del flujo.
- Presentar dos eventos como un modelo calibrado.
- Comparar imágenes de tracks distintos.
- Dejar NISAR como capa decorativa: es el centro del desafío.
