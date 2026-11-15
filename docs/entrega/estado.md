# Estado de cierre · 15 de noviembre de 2026

## Entregado

- Interfaz centrada en Biobío, tres pasos con preguntas claras, un mapa principal y detalle técnico plegado.
- Pantanal retirado de la navegación; estudios adicionales en un menú secundario.
- Reproducción térmica GOES, contexto ERA5, señal óptica Sentinel-2, comparador posterior NISAR e índice exploratorio.
- FIRMS rotulado como consulta guardada; pronóstico de Open-Meteo separado de las observaciones.
- Sin mezcla de cifras de enero con el modo de detecciones recientes. Fechas del comparador en orden cronológico.
- Flechas de viento como geometría: no dependen de una fuente tipográfica remota.
- Imagen Cloud Run publicada conservando máximo 2 instancias, mínimo 0, CPU 1 y memoria 2 GiB. Sin cambiar facturación ni contratar servicios adicionales.
- Rásteres pequeños regenerados de Las Condes incluidos al construir la imagen; no se mezclan con cifras anteriores.
- 114 pruebas unitarias, 63/63 del asistente, lint y build. 48 comprobaciones HTTP sobre la imagen local y las mismas 48 en la URL pública. Informe: api_publica.json.
- Recorrido visual de los tres pasos, comparador y ancho móvil 390 px; sin desborde horizontal observado.
- Licencia Apache-2.0 incorporada por elección explícita del propietario. Licencias de las fuentes conservadas.
- Guion de dos minutos, resumen inglés, declaración de uso de IA y capturas de la aplicación pública en esta carpeta.
- Pronóstico público comprobado: HTTP 200 y 48 horas. Consola sin errores ni advertencias observados durante el recorrido público.
- Repositorio público: https://github.com/ethan1213/sarwatch-nisar-2026 (main).

## Límites y trabajo que no se declara completo

- El modelo exploratorio no demuestra capacidad de alerta operativa ni generalización fuera de sus fechas y zonas evaluadas.
- Falta contrastar perímetro y daño con referencia oficial independiente y revisión científica externa.
- Falta una prueba de comprensión con personas reales. La revisión automática y visual no demuestra comprensión universal.
- Video narrado con capturas estáticas: demo_narrada.mp4, aproximadamente 1:57, con voz sintética local explícitamente rotulada. No equivale a una presentación grabada por una persona ni a una prueba de comprensión.
- Deep learning y foundation models requieren entrenamiento y evaluación propios; los cuadernos no equivalen a modelos ya validados.
- Sin prueba nueva de glaciar, ingesta continua con secretos Earthdata ni integración Vercel/Supabase. No son requisitos para abrir esta demo.
- Apache-2.0 autoriza el código propio; las fuentes de datos conservan sus condiciones. Repositorio público comprobado sin autenticación en GitHub; licencia detectada Apache-2.0.

El plan original continúa en docs/plan_mvp_incendios.md. Este estado reemplaza sus instrucciones de mostrar Pantanal y de llamar «Antes» a datos posteriores a enero. No se fuerza una narrativa científica que las adquisiciones no respaldan.
