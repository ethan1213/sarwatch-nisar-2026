# Guion de pruebas con personas reales

Objetivo: comprobar que alguien de cada perfil entiende lugar, fechas, qué cambió y qué no se puede concluir **sin ayuda**. Una revisión de escritorio no demuestra comprensión; esto sí.

## Participantes

Cinco a ocho personas, al menos una por perfil: público general, ciencia (no necesariamente SAR), desarrollo y datos, comunicaciones, gestión territorial. Sesión individual de 30 minutos, pantalla compartida, con permiso para registrar notas (no grabación sin consentimiento).

## Tareas (en orden, sin pistas)

1. Abre la aplicación. ¿Qué lugar y qué fechas se comparan? (éxito: nombra ambos en < 1 minuto)
2. Mira el mapa. ¿Qué significa el color naranja? ¿Y lo transparente? (éxito: respuesta mayor / sin dato; fracaso: «peligro», «inundación»)
3. ¿Cuánta agua abierta estimó el sistema en la fecha final y qué tan confiable es esa estimación? (éxito: encuentra el km² y la métrica F1, y menciona que es agua abierta, no inundación)
4. ¿Esto sirve para predecir una inundación mañana? (éxito: «no» con la razón que da el sistema)
5. Pregunta al asistente algo que te preocupe del lugar. ¿La respuesta te dio una cifra? ¿Sabes de dónde salió?
6. Descarga la serie de un punto en CSV. (éxito: archivo descargado)
7. Cambia al perfil que mejor te describe. ¿Qué cambió y te ayudó?

## Qué registrar

- Tiempo por tarea y si necesitó ayuda.
- Frases textuales donde interpretó mal (p. ej., cobertura como precisión).
- Dónde se detuvo o buscó sin encontrar.
- Una pregunta que hizo al asistente y si la respuesta le pareció clara.

## Criterios de salida

Al menos 4 de 5 perfiles completan las tareas 1, 2 y 4 sin ayuda; nadie sale creyendo que la app confirma inundaciones o predice riesgo. Si no se cumple, se ajusta la vista y se repite con nuevas personas.

## Accesibilidad

Complementar con `scripts/check_a11y.py` (axe-core vía Playwright) para contraste, etiquetas y navegación por teclado. Las pruebas automáticas no sustituyen a las personas.
