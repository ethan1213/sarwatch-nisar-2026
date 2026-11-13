# Plan detallado — 13 noviembre 2026

## Objetivo

Explorar cambios NISAR sobre Pantanal entre siete fechas reales de julio-septiembre de 2026, con procedencia y contexto meteorológico. Ampliar regiones solo con datos comparables. No presentar cambio SAR como inundación confirmada ni pronóstico meteorológico como predicción SAR.

## Fases y aceptación

| Fase | Trabajo y cómo hacerlo | Responsable funcional propuesto | Salida verificable |
|---|---|---|---|
| 1. Inventario | ID CMR, granulo, URL, fecha UTC, bytes y hashes; verificar archivos antes de nuevos procesamientos | Datos | Fuentes trazables; originales y credenciales fuera de Git |
| 2. Calidad SAR | Revisar versión/calibración, atributos de máscaras, looks, geometría, fill y extremos; comparar x/y, CRS y polarización | Ciencia | Informe de códigos y exclusiones; fracción válida por fecha; rechazar grillas incompatibles |
| 3. Productos | Recortar por ventana; 10 log10 de intensidad positiva; COG con nodata, CRS y procedencia | Procesamiento | Valores coincidentes con HDF5; diferencia de una escena consigo misma igual a cero; nodata preservado |
| 4. Visor | HH/HV, fechas, antes/después, diferencia, serie; después mapa geográfico y clic | Interfaz | Controles probados, escalas iguales, huecos explícitos y exportación |
| 5. Meteorología | Adaptador opcional, histórico/pronóstico separados, caché, timeout; lluvia antecedente solo con cobertura completa | Integración | Caída API no afecta SAR; unidad, modelo, proveedor y fecha visibles |
| 6. Validación | Hidrometría/óptico/mapas independientes próximos a adquisición; controlar vegetación y humedad | Validación | Evidencia espacial/temporal; clasificación solo con etiquetas evaluadas |
| 7. Nube | Imagen, derivados persistentes, HTTPS y WebSocket; medir memoria y latencia; probar desde otra red | DevOps | Imagen healthy, URL y audiencia previstas, recuperación tras reinicio |
| 8. Entrega | Historia, método, demo, límites, fuentes, licencia y acceso del jurado | Coordinación | Material accesible y reglas vigentes revisadas |

Repartir los roles entre los seis integrantes según disponibilidad; no se presume especialización por sus nombres.

## Orden de trabajo

1. Revisar el primer recorte y QA antes de entrenar modelos o ampliar funcionalidades.
2. Validar las siete escenas y fijar un conjunto reproducible.
3. Cerrar navegación y errores; meteorología como complemento que no altera SAR.
4. Segundo AOI solo con dos fechas comparables y evidencia independiente disponible.
5. Medir derivados, memoria y latencia; elegir nube/presupuesto y probar externamente.
6. Preparar demostración para uso válido de datos/ciencia y relato ambiental.

## Decisiones y riesgos

- PROVISIONAL: conservar madurez y versión; no mezclar productos sin evaluación.
- Agua abierta y vegetación inundada responden distinto: no usar un umbral universal de dB.
- ERA5 tiene escala mucho mayor que 20 m: no asignar lluvia observada a cada píxel.
- No rellenar meses ausentes ni inventar una serie anual.
- La arquitectura podrá extenderse; hoy solo existe catálogo Pantanal.
- HDF5 fuera de Git; derivados pequeños versionados mediante manifiesto y hashes.
- Privado durante desarrollo; resolver apertura y licencia antes de entregar la solución abierta solicitada por el enunciado.
- Un predictor propio de inundaciones requeriría hidrología, más historia, etiquetas y evaluación temporal independiente. No se incluye en el pronóstico meteorológico.

## Cierre final

App accesible al público/jurado previsto, controles comprobados, método y calidad documentados, validación ambiental independiente y despliegue reproducible. El prototipo no equivale a una entrega científica final. Ver estado.md para pruebas realizadas y pendientes concretos.
