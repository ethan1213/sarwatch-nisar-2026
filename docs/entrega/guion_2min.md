# Guion de demostración · objetivo de dos minutos

Texto para una persona presentadora. Versión narrada con voz sintética local y capturas: demo_narrada.mp4 (aproximadamente 1:57). Una lectura humana debe cronometrarse por separado.

**0:00–0:35 · Qué ocurrió.**
Estamos en Biobío. Queremos comprender un incendio sin tener que interpretar primero una pantalla llena de mapas. SARWatch empieza con una pregunta: ¿dónde se observó calor? Esta reproducción recorre enero de 2026. Los cuadros rojos indican áreas donde GOES detectó calor en esa hora; los ámbar conservan lo observado antes. Son observaciones del satélite, no el borde del fuego. Al seleccionar una celda podemos consultar el viento, la humedad y la temperatura del reanálisis ERA5. Ese contexto no indica por dónde entrar al terreno.

**0:35–1:15 · Qué quedó.**
Pasamos ahora a las señales posteriores. Sentinel-2 aporta una comparación óptica: en el recorte encontramos 185,7 kilómetros cuadrados con señal moderada o alta. No es un perímetro oficial; también pueden influir sequía y cosecha. Abrimos después la evolución NISAR y deslizamos entre febrero y octubre. Ambas imágenes son posteriores al incendio. No tenemos una pasada anterior de esta geometría para atribuir todo el cambio al fuego. El radar describe una señal del terreno: no mide temperatura ni confirma recuperación del bosque.

**1:15–1:45 · Qué podemos anticipar.**
La tercera pregunta sigue abierta. Probamos un índice de prioridad de vigilancia y reservamos fechas que el modelo no vio. Mostramos sus aciertos y sus límites. El resultado todavía no basta para emitir alertas operativas. Mantener visible esa limitación es parte del producto.

**1:45–2:00 · Cierre.**
La demo funciona en GCP y conserva fuentes, fechas y evaluaciones reproducibles. El siguiente paso es contrastarla con especialistas y personas usuarias. SARWatch ayuda a explorar evidencia; las decisiones en terreno requieren información independiente.

Cifras: catalog/fire_story/story.json → after.area_km2.land_by_class. Fechas: after.radar. Descripción de evaluación: before.benchmark y before.limits. Código público y licencia: comprobar el repositorio antes de afirmarlo en una presentación.
