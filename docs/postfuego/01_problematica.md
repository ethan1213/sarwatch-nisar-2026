# 1. La problemática

Chile apaga incendios, pero nadie vigila la ladera quemada después.

- Chile quema en promedio ~153.000 ha al año (Senapred).
- Tras el fuego queda una ventana de 1 a 3 años de riesgo aluvional (documento municipal de Las Condes, junio de 2026).
- En Chile no existe monitoreo de remociones en masa: lo dijo la directora de Senapred la noche del 8-oct para explicar por qué no hubo alerta SAE.
- No hay pluviómetro dentro de la quebrada Honda (CR2). El dato más cercano está a 7 km.
- Las advertencias existieron (Sernageomin en febrero, municipio en junio), pero fueron cualitativas: "alto peligro", sin umbral ni fecha.
- Costo del vacío: 2.015 viviendas afectadas, 1.200 rescatados, US$172,8 millones en daños (estimación preliminar de Inciti), zona de catástrofe e investigación de Fiscalía.

## 2. La causalidad, con datos reales

Los dos eventos de 2026 en la misma quebrada

| | 31 de enero | 8 de octubre |
|---|---|---|
| Tipo de lluvia | Tormenta convectiva de verano | Frontal + baja segregada |
| Intensidad máx. (Parque El Arrayán, DGA) | 19,2 mm en 30 min | 8,8 mm en 30 min |
| Lluvia de los días previos | Casi nada (verano seco) | 70 a 140 mm el 6 y 7 de oct |
| Daño | 11 a 28 viviendas | 2.015 viviendas |

Lectura: con la mitad de intensidad, octubre fue muchísimo peor. Sernageomin lo atribuye a tres factores: suelo saturado por las lluvias previas, ladera sin vegetación por el incendio y obras insuficientes. Octubre fue el más lluvioso registrado en Santiago (107,9 mm en Quinta Normal, dato provisorio DMC).

### La cadena completa

1. **Incendio (dic-2025):** se queman 8,2 de 10,1 km² de las cuencas aportantes, con severidad mayormente baja a moderada. Menos infiltración, más sedimento suelto.
2. **Primer gatillo (31-ene):** chubasco muy intenso sobre suelo seco. Se activan cuatro quebradas; daño menor, pero los cauces quedan cargados de material.
3. **Carga (oct):** 70-140 mm en dos días saturan el suelo.
4. **Segundo gatillo (8-oct):** un pulso moderado (~18-22 mm/h) basta. Agua + sedimento bajan como flujo, tapan el ducto en Álvaro del Portillo y la calle se vuelve el cauce.

Frase para el pitch: "El fuego cargó el arma, las lluvias previas la amartillaron, y bastó media hora de chubasco para disparar."

### Lo que esto significa para la solución

Un umbral solo de intensidad (como el M1 de USGS) habría dado alerta el 31-ene y subestimado el 8-oct. El umbral correcto es dinámico: baja cuando el suelo está saturado y cuando la quebrada tiene sedimento acumulado. Ahí entra NISAR: la banda L es sensible a la humedad del suelo y ve cambios en el cauce (depósitos), a través de nubes, cada 12 días. Eso no lo hace ningún competidor.

## 3. La solución, ajustada

PostFuego = umbral dinámico de aluvión por quebrada quemada.

| Variable | Qué mide | Fuente |
|---|---|---|
| Quema | Cuánto y qué tan fuerte se quemó | NISAR (índice HH+HV) + dNBR Sentinel-2 |
| Pendiente y cuenca | Qué tan rápido concentra el agua | DEM Copernicus 30 m |
| Saturación | Lluvia de los 3-7 días previos + humedad del suelo | Pluviómetros DGA/CR2 + NISAR HH (+ SMAP) |
| Carga del cauce | Sedimento acumulado por eventos previos | Caída de coherencia NISAR |
| Gatillo | Lluvia pronosticada en 30 min | Pronóstico horario |
| Exposición | Casas y ductos aguas abajo | OSM |

Salida: semáforo por quebrada + "esta semana, con el suelo como está, bastan X mm en 30 min".

## 4. Datos disponibles

| Dato | Estado | Riesgo |
|---|---|---|
| NISAR GCOV/GUNW antes y después del 8-oct (A147, A75, D169) | Verificado en ASF | Nadie ha abierto un .h5 aún |
| NISAR antes y después del incendio (BETA, dic-ene) | Verificado | Sin calibrar |
| NISAR 31-ene | No existe (hueco 19-ene a 19-jun) | Ese evento solo con óptico y lluvia |
| Lluvia 30 min (DGA Parque El Arrayán, Río Molina) | Publicada en análisis CR2 y prensa | Descargar la serie puede tardar |
| dNBR Sentinel-2 | Libre | Nubes en invierno |
| DEM, OSM | Libres | Ninguno |
| Recorrido del aluvión | Reconstruido por asdr.cl y hirely.cl | Úsenlo como validación, cítenlos |

## 5. Viabilidad en ~20 horas

| Bloque | Horas | Dificultad |
|---|---|---|
| Subcuencas, pendiente, quema (dNBR) | 4-5 | Baja |
| Umbral dinámico (M1 + factor de saturación con lluvia previa) | 4 | Media |
| NISAR: ΔHH (humedad) y Δcoherencia (depósito) en A147 | 5-6 | Alta: el cuello de botella |
| Mapa web con semáforo y línea de tiempo ene-oct | 6-8 | Media |
| Pitch y video | En paralelo | Baja |

Hito de corte: si a las 17:00 no hay un ΔdB legible sobre la quebrada, NISAR queda como "capa de validación" con una imagen, y el motor corre con lluvia + quema.

Honestidad científica: dos eventos no calibran un modelo. Se presenta como prueba de concepto calibrable, con el plan de sumar Viña 2024 y otras cicatrices.

## 6. Potencial de ganar

Criterios oficiales (Space Apps): Impacto, Creatividad, Validez, Relevancia, Presentación.

| Criterio | Nota estimada | Por qué |
|---|---|---|
| Impacto | 5/5 | Catástrofe real, US$172 M, replicable a todo Chile |
| Creatividad | 4/5 | Umbral dinámico + radar es nuevo; el post-incendio ya lo trabajan otros |
| Validez | 3-4/5 | Depende de que NISAR muestre señal; el hallazgo enero vs octubre la sube |
| Relevancia (NISAR) | 3-5/5 | El punto débil: si NISAR es decorativo, cae a 3 |
| Presentación | 5/5 | La historia es local, fresca y con imágenes del bus |

Lectura: fuerte candidato a premio local y a nominación global, si NISAR hace trabajo real (humedad o depósito). Sin eso, buen proyecto de riesgo con poca relación con el desafío.

Cómo diferenciarse de kutralguard, asdr y hirely: ellos reconstruyen el pasado con óptico y modelos; nosotros predecimos con radar y explicamos por qué octubre fue peor que enero.

## 7. Riesgos que pueden hundirlo

- No abrir los .h5 a tiempo (credenciales Earthdata).
- Señal de humedad confundida con cambio de vegetación o rugosidad.
- Severidad de quema baja: el M1 puro daría probabilidades bajas. Por eso el factor de saturación es clave.
- El jurado pregunta "¿qué tiene de NASA?" y la respuesta es débil.
- Que otro equipo de la sede elija el mismo caso (es el desastre más mediático del año).

## Próximos 60 minutos (plan original)

1. Credenciales Earthdata y abrir un GCOV de A147 con gdalinfo.
2. Bajar la serie de 30 min de Parque El Arrayán y Río Molina (ene y oct).
3. Gráfico estrella del pitch: intensidad vs lluvia previa para ambos eventos.

## Qué dice el desafío

"La superficie de la Tierra es una danza sin fin de procesos naturales y actividades humanas, pero estos cambios suelen ser difíciles de visualizar, entender y comunicar." Esta frase define el problema: no es la falta de datos, sino que los cambios cuestan de ver y de explicar. El foco está en la comunicación tanto como en la ciencia.

"Desde la pérdida de humedales hasta incendios forestales, terremotos, actividades agrícolas, movimiento de glaciares y más…" Son ejemplos, no una lista cerrada. Cualquier cambio superficial vale, y los incendios aparecen explícitamente.

"Tu desafío es construir una aplicación interactiva que use datos de teledetección por radar de la misión NISAR para seguir y visualizar uno o más tipos de cambio superficial en lugares del mundo." Esta es la tarea. Tiene cuatro piezas obligatorias: aplicación interactiva, datos NISAR, seguimiento del cambio y alcance global.

### Qué les exige en concreto

- "Aplicación interactiva": el usuario tiene que poder hacer algo, como elegir un lugar, mover una línea de tiempo o comparar antes y después. Un mapa estático o una presentación no cumplen.
- "Seguir" (track): implica tiempo, una serie de fechas y no solo un par. La línea de tiempo de diciembre a octubre cumple justo esto.
- "Visualizar": el cambio tiene que entenderse sin ser experto en radar. Comunicar es la mitad del trabajo, y la historia de enero contra octubre es una ventaja ahí.
- "Uno o más tipos": con un tipo bien hecho basta. Hay incendio y aluvión, y está bien no intentar más.
- "En lugares del mundo": la app tiene que funcionar fuera de la quebrada Honda. Un segundo sitio, aunque sea simple, responde este punto.

En resumen, el desafío pide exactamente lo que PostFuego puede ser si NISAR va al centro: una app donde se ve, con radar, cómo una ladera se quema, se empapa y se viene abajo. El umbral dinámico es lo que la hace útil, pero lo que la evalúa es el cambio superficial visto por NISAR.
