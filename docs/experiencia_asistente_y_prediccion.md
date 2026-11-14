# SARWatch: comprensión, asistente, escala mundial y predicción

Revisión del 13 noviembre 2026. Se distingue lo implementado de lo propuesto. El alcance de ejecución sigue siendo Docker local, sin servicios contratados ni descargas mundiales.

## 1. Diagnóstico de la experiencia

La vista anterior mostraba primero dB, polarizaciones, coordenadas UTM, porcentajes técnicos y tablas de granulos. Eso permite inspeccionar archivos, pero obliga a conocer SAR antes de entender el propósito. Los colores no contestaban «qué cambió», y 99,9 % de cobertura podía confundirse con precisión. La pestaña del navegador conservaba además una versión anterior a la última actualización.

Se recargó la versión activa y se revisó su estructura. La evaluación por perfiles es una revisión de escritorio, no entrevistas ni pruebas con participantes reales. No se atribuye a personas una opinión que no dieron.

## 2. Perfiles y recorridos

| Perfil | Pregunta principal | Vista o salida apropiada | Error que debemos evitar |
|---|---|---|---|
| Público general | ¿Qué estoy viendo y qué significa? | Lugar, fechas, resumen de señal, guía breve y mapa | Presentar dB como peligro o esconder que falta validación |
| Ciencia | ¿Se pueden comparar estas observaciones? | Máscara común, distribución, grilla, versiones y fuentes | Llamar precisión a la cobertura o inferir causalidad |
| Desarrollo y datos | ¿Cómo reproduzco e integro el resultado? | COG, contrato del manifiesto, CSV, hashes y proceso | Confundir productos locales con cobertura mundial |
| Comunicaciones | ¿Qué podemos comunicar responsablemente? | Borrador basado en fechas y medición, con límites explícitos | Publicar «inundación detectada» o cifras de daños sin evidencia |
| Gestión territorial | ¿Dónde conviene revisar y con quién contrastar? | Recorte, contexto territorial, datos faltantes y evidencia local | Usar el prototipo como alerta operativa |

Cambios implementados: Santiago como entrada, encuadre urbano y diferencia como opciones iniciales en Chile; selector de perfil; resumen calculado de las observaciones; instrucciones de lectura; gráficos nativos y catálogo técnico plegados; paleta coherente azul–claro–naranja; escala individual ampliada a +10 dB para no saturar los retornos urbanos positivos con un techo de 0 dB. Las escalas de color siguen siendo de visualización, no umbrales de clasificación.

La lectura descriptiva usa mediana y cuartiles sobre píxeles válidos comunes. Una mediana pequeña no descarta cambios localizados. No se asignan etiquetas ambientales ni significación estadística a esa cifra.

## 3. Asistente: dos niveles, sin confundirlos

**Implementado ahora:** chat guiado local, basado en reglas, contexto y fuentes. Explica colores, dB, HH/HV, cobertura, causas posibles y límites de predicción. Usa el área, par y canal seleccionados, conserva una conversación corta y la reinicia cuando cambia la evidencia. No hay una llamada a un LLM ni envío de preguntas a terceros. Ante una pregunta fuera de su alcance, declara falta de evidencia. No simula capacidad generativa ni responde sobre riesgos que no se han modelado.

**Siguiente nivel propuesto:** un LLM que redacte a partir de herramientas verificables, sin ejecutar comandos ni acceder a credenciales. Sus entradas deberían ser un resumen numérico cerrado, fuente por afirmación, glosario SAR y documentación seleccionada. Los cálculos deben venir de funciones, nunca de números inventados por el lenguaje. El recuperador puede empezar con búsqueda textual en documentos locales; una base vectorial no es obligatoria para este volumen.

Arquitectura propuesta: pregunta → clasificación de intención → herramienta de estadísticas/punto/calidad/meteorología → evidencia estructurada → redacción opcional → comprobación de citas y números → respuesta. La salida debe indicar observación, hipótesis y dato ausente. El asistente explica el modelo científico; no reemplaza ese modelo.

Opciones a evaluar:

| Opción | Ventaja | Límite |
|---|---|---|
| Chat guiado actual | Reproducible, sin pesos ni dependencia de una API | Conjunto limitado de intenciones; no conversa libremente |
| Modelo local pequeño, por ejemplo Qwen3-4B-Instruct-2507 | Candidato multilingüe y licencia Apache 2.0 según su ficha | Requiere evaluación en español y recursos adicionales; no está instalado ni probado aquí |
| Modelo remoto | Evita cargar pesos en este equipo | Coste, privacidad, red y proveedor por decidir; no se habilita sin elección del propietario |

Un modelo de 4.000 millones de parámetros a 4 bits supone aproximadamente 2 GB solo de pesos por aritmética; formato, metadatos, caché de contexto y runtime añaden memoria. Presupuestar varios GB adicionales y medir latencia/RAM antes de elegir. El PC informa aproximadamente 16 GB de RAM total y ya ejecuta Docker: no se promete que una combinación concreta quepa o responda con fluidez. No se descargó ningún modelo.

Pruebas de aceptación del LLM: coincide exactamente con las cifras de herramientas; cita fuentes existentes; no transforma cobertura en probabilidad; se abstiene sin evidencia; distingue fecha de observación y de pronóstico; no mezcla recortes; resiste instrucciones maliciosas dentro de documentos; conserva límites en cada perfil. Necesita un conjunto revisado de preguntas y evaluación humana, no una impresión de fluidez.

## 4. Qué entendemos por «modelo»

Hay tres componentes distintos: procesamiento SAR (calidad/grilla/unidades), interpretación ambiental (qué fenómeno explica el cambio) y pronóstico (qué ocurrirá después). El chatbot es un cuarto componente de comunicación. Mejorar su lenguaje no mejora automáticamente la precisión científica.

Hoy existe procesamiento reproducible de GCOV y descripción del cambio. No existe clasificador validado de inundación ni predictor de daños. Dos fechas en Chile sirven para una diferencia, no para entrenar y demostrar un pronóstico. Los siete registros de Pantanal tampoco constituyen una base suficiente para un modelo mundial.

## 5. Primer experimento predictivo ejecutado

Se añadió un benchmark retrospectivo de persistencia: para la mediana HH del recorte, repetir el valor de la fecha anterior como referencia de la siguiente. Solo evalúa pares separados aproximadamente 12 días y escenas con al menos 50 % de cobertura técnica. Esa selección de cobertura es una regla de evaluación, no una clasificación ambiental.

Resultado sobre Pantanal: **4 evaluaciones**, MAE **0,45154 dB**. Detalle reproducible en persistence_benchmark.json y scripts/evaluate_baseline.py. No es «45 % de error» ni una exactitud de inundación. Es una referencia mínima para la mediana de la señal, en un solo lugar y con muy pocas fechas. La máscara común usa disponibilidad retrospectiva del par: el experimento no reproduce un servicio de pronóstico operativo. No se entrenó un modelo ni se demostró generalización.

## 6. Problema predictivo recomendado

Acotar primero a humedales/inundación en una cuenca con evidencia independiente, en vez de intentar predecir incendios, terremotos, cultivos y glaciares con una sola arquitectura.

1. **Detección observada:** ¿cambió la extensión de agua entre fechas? Requiere referencia contemporánea, definición de agua abierta/vegetación inundada y tratamiento de sombra radar, pendiente y humedad.
2. **Pronóstico experimental:** probabilidad o extensión de inundación para un horizonte definido, por ejemplo 1–3 días, usando hidrología y meteorología. La repetición orbital NISAR no convierte la imagen en una medición diaria; deben registrarse edad del último dato y retraso de publicación.
3. **Validación antes de alertas:** eventos separados por tiempo y cuenca; pruebas de estacionalidad, errores de localización y cobertura fuera de distribución. No emitir alertas operativas hasta demostrar utilidad y calibración.

Variables candidatas: HH/HV en dB, diferencia y textura controlada, lluvia antecedente, pronóstico emitido antes de la fecha objetivo, humedad de suelo, pendiente, elevación y distancia a drenajes. No introducir un reanálisis revisado después del evento como si hubiese estado disponible al predecir. Registrar adquisición, publicación y momento de emisión.

Empezar comparando persistencia, climatología estacional y una regla interpretable, después un modelo tabular regularizado o de árboles. Modelos temporales profundos solo si cantidad y diversidad de eventos lo justifican. Separar entrenamiento/validación/prueba por evento, tiempo y geografía; no repartir píxeles vecinos aleatoriamente entre conjuntos.

Métricas: para agua/inundación, precisión, recall, F1/IoU y errores por tipo de superficie; para probabilidad, Brier y calibración; para área/caudal, MAE y sesgo; para operación, anticipación, cobertura y tasa de falsas alarmas. Comparar contra baselines en el mismo conjunto congelado. Sin etiquetas adecuadas, no publicar porcentajes de exactitud.

La Global Flood API de Open-Meteo ofrece caudal modelado GloFAS a escala mucho más gruesa que SAR. Puede contextualizar ríos si se valida el tramo/cuenca, pero caudal en una celda no equivale a profundidad o inundación de una calle. No se conectó aún como predictor del proyecto.

## 7. Cobertura mundial: sí como arquitectura, no descargando todo

NASA describe cobertura global de tierra/hielo con ciclo orbital de 12 días y distintas pasadas; disponibilidad útil y productos deben comprobarse en catálogo. No garantiza una escena interpretable para cualquier coordenada/fecha ni cobertura SAR validada dentro de SARWatch.

Arquitectura mundial propuesta: mapa global ligero → búsqueda CMR/ASF por área y fechas → catálogo STAC interno de productos derivados → trabajos por AOI y ventana → COG en almacenamiento de objetos → teselas/rangos HTTP y CDN → resumen y consultas de punto. Colas, límites por AOI, presupuesto por trabajo, caducidad de caché y manifiestos versionados evitan procesar el planeta a cada visita. Los HDF5 y credenciales quedan fuera del cliente y del LLM.

La demo actual sigue local y publica tres AOI preparados. Aún no hay buscador mundial, cola distribuida, servicio de teselas ni operación multicuenca. El siguiente experimento de escala debe ser un cuarto AOI solicitado bajo demanda, midiendo tiempo, RAM, bytes transferidos y costo, antes de diseñar infraestructura masiva.

«Para todo el mundo» tiene también una dimensión de acceso: un enlace HTTPS, móvil y teclado, idiomas, unidades comprensibles y control de concurrencia. No exige duplicar el archivo satelital por visitante. Código privado y audiencia de la app son decisiones distintas. Hoy localhost solo sirve desde el equipo anfitrión; la publicación externa sigue fuera del alcance autorizado. Antes de declarar accesibilidad o comprensión universal hay que probar teclado, contraste, lectores de pantalla y tareas con participantes reales. La revisión actual verifica estructura y una interacción de chat en el navegador, no certifica accesibilidad.

## 8. Tamaño: medido y estimado

Medición del proyecto en esta revisión: aproximadamente **3,393 GB** de originales chilenos y **0,592 GB** de productos/manifiestos en data. Existe además un directorio data_qa con **0,406 GB** de derivados de una etapa anterior. No se borró. Esto no incluye el entorno Python, imágenes/cachés Docker, mapas remotos ni los aproximadamente 13 GB de originales Pantanal almacenados fuera de esta carpeta.

Fórmula de escenario: área_km² × 1.000.000 / resolución_m² × canales × fechas × 4 bytes, multiplicado por 4/3 para overviews aproximadas. No incluye máscaras adicionales, incertidumbre, índices, réplicas, versiones, bruto de misión, solapamientos, proyecciones ni transmisión. Se asume float32 sin compresión; la compresión real se debe medir y no se garantiza.

| Escenario hipotético | Dos canales, 30 fechas, overviews | Interpretación |
|---|---:|---|
| 10.000 km² a 20 m | 8 GB | Estudio regional acotado |
| 1.000.000 km² a 20 m | 800 GB | Varias áreas/regiones |
| 150 millones km² a 20 m | 120 TB | Escenario redondeado de escala terrestre, no inventario de misión |
| Mismo escenario a 80 m | 7,5 TB | Menor detalle espacial |
| Mismo escenario a 100 m | 4,8 TB | Visión regional/global general |
| Mismo escenario a 200 m | 1,2 TB | Exploración gruesa |

El escenario de 150 millones km² es una hipótesis de dimensionamiento redondeada, no un área exacta de cobertura validada. 30 fechas tampoco incluye automáticamente ambas direcciones orbitales. El visor debe recibir únicamente teselas y datos del punto consultado, no terabytes. La calculadora en la app permite cambiar área, resolución y fechas. Ninguna cifra anterior es precio de nube; no se contrató almacenamiento.

## 9. Orden de avance y criterios de salida

1. Probar la nueva lectura con personas reales de los cinco perfiles. Deben identificar lugar/fechas, diferenciar señal de riesgo y explicar un dato ausente sin asistencia. Registrar dónde se pierden, no solo si les gusta el diseño.
2. Revisar manualmente un conjunto pequeño de preguntas del chat; exigir trazabilidad de cifras y abstención fuera de evidencia. Evaluar LLM opcional contra el chat guiado antes de asumir que mejora la comprensión.
3. Elegir cuenca/evento/etiquetas y generar una serie temporal comparable más extensa. Mantener precisión de objetivo y no ampliar fenómenos a la vez.
4. Congelar protocolo temporal/geográfico y ejecutar baselines; entrenar solo después de reunir datos adecuados. Publicar resultados negativos y límites.
5. Probar adquisición/procesamiento de un AOI adicional bajo demanda. Medir recursos y experiencia; presupuestar despliegue únicamente si el propietario cambia el alcance local.

## 10. Fuentes primarias consultadas

- NASA, misión y repetición orbital: https://science.nasa.gov/mission/nisar/mission-overview/
- ASF, uso de productos NISAR: https://nisar-docs.asf.alaska.edu/using-overview/
- ASF, acceso a datos y restricciones S3: https://nisar-docs.asf.alaska.edu/earthaccess/
- Open-Meteo, caudal modelado y GloFAS: https://open-meteo.com/en/docs/flood-api
- Qwen, ficha/licencia del candidato local: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- Ollama, contrato API local propuesto: https://docs.ollama.com/api/chat

Fuentes de resultados propios: manifiestos locales, hashes CMR verificados, estadísticas calculadas y benchmark. Las recomendaciones de producto/arquitectura de este documento son propuestas del proyecto, no requisitos de NASA.
