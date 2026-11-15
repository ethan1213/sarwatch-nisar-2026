# SARWatch · cierre técnico del despliegue

**Estado real: código comprobado en local; URL pública de Cloud Run aún pendiente.**
La subida de la imagen sufrió una interrupción de red y se reintenta. Los originales de
Concepción/Penco siguen descargándose; no se presentan como rásteres verificados.

Actualización: interfaz para público general con comparación visual de dos fechas, mapa de contexto,
preguntas guiadas y detalle técnico plegable. Inventario CMR completo para Concepción/Penco y
ventana regional de Biobío, separado por madurez, CRID y geometría. FIRMS VIIRS NOAA-20/NOAA-21/S-NPP
consultado desde descargas públicas recientes: 15 detecciones en la ventana urbana y 269 en la
regional; son observaciones, no incidentes distintos ni perímetros. Fuente `catalog/firms_reference.json`.

## Alcance implementado

React/MapLibre servido por FastAPI, sin Streamlit en el proceso publicado. Sitios: Pantanal,
Región Metropolitana, Valparaíso y cobertura mundial. Incluye HH/HV, fechas, diferencia,
series por punto y CSV, lecturas por cinco perfiles, cambio estadístico de Chile, meteorología
opcional, asistente verificado, PostFuego y laboratorio CO₂/DEM.

El laboratorio nuevo es experimental y está separado de las capas evaluadas: no tiene etiquetas
independientes que permitan puntuar validación espacial o temporal. No se presenta como modelo
operativo. Gartner 2014 está implementado y bloquea la salida de volumen sin intensidad observada
de 15 minutos. Ni el DEM ni el modelo de volumen proporcionan profundidad de depósito o rutas seguras.

CO₂ usa la ecuación 2.27 del IPCC 2006 con equivalencias de combustible y factores por severidad
explícitamente supuestos. La Tabla 2.4 reporta SE y la Tabla 2.5 SD: el rango calculado es sensibilidad,
no intervalo de confianza. Estima liberación bruta durante combustión, no emisiones netas posteriores.
Las señales dNBR del recorte completo no equivalen a un perímetro de incendio confirmado.

## Datos y reproducibilidad

- `scripts/estimate_fire_impacts.py`: grillas coincidentes, CRS métrico, área por determinante afín,
  checksums SHA-256, estimaciones tabuladas, índice raster y cuencas aproximadas.
- `catalog/fire_impacts_reference.json` y `docs/fire_impacts_estimate.json`: resultados generados,
  supuestos, procedencia y ausencias; `models/fire_impacts.card.json`: tarjeta no validada.
- GOES recuperado de NOAA para el 13 de noviembre de 2026, 24 pasos horarios por sitio. Cero fallos
  de adquisición. El mapa de este día se distingue del resumen histórico julio–noviembre.
- `scripts/evaluate_fire.py` ejecutado con salidas alternativas `thermal_current_benchmark.json` y
  `thermal_current_reference.json`; conserva el benchmark histórico y genera el cruce SAR/DEM por celda.
- HDF5 originales, contraseñas, transcript de conversación, credenciales y entradas de entrenamiento
  no forman parte de la imagen publicada. Datos derivados incluidos en la imagen para reproducir
  la versión servida sin depender de una unidad del computador.

## Infraestructura y límite de gasto

Proyecto `project-6fff6574-07af-4183-b83`, región `southamerica-west1`. Cloud Run, Artifact Registry
y bucket privado `sarwatch-525550511866-data`. Identidad web dedicada sin roles añadidos para acceso
a otros servicios. Datos experimentales respaldados en Storage; imagen incluye los derivados del visor.

Límite del propietario: US$300 de crédito total. Se conserva la cuenta en prueba gratuita, sin
actualizar a pago. Según las condiciones de Google, al agotar créditos o vencer la prueba se detienen
los recursos si la cuenta no fue actualizada: https://docs.cloud.google.com/free/docs/free-cloud-features

Alerta de presupuesto mensual conservadora de 20.000 CLP, proyecto filtrado, umbrales 50/90/100 %,
excluyendo créditos del cálculo para avisar del consumo bruto. **Una alerta no es un corte de gasto.**
Cloud Run con 1 CPU, 2 GiB, concurrencia 4, mínimo 0 y máximo 2 instancias. Sin GPU, entrenamiento
continuo, APIs LLM de pago, máquinas virtuales o bases de datos permanentes.

`scripts/deploy_gcp.ps1` reproduce construcción, publicación, despliegue y pruebas HTTP. Requiere
autenticación del operador y los recursos iniciales ya creados; no actualiza cuentas de facturación.

## Verificación

101 pruebas unitarias, 63/63 casos del asistente y 38 comprobaciones HTTP sobre la aplicación completa.
Frontend compilado con Vite y lint sin avisos. Memoria observada tras recorrido HTTP local: aproximadamente
500 MiB en un contenedor limitado a 2 GiB y 1 CPU. Esto es una prueba funcional, no un ensayo de carga.

## Límites que impiden declarar terminada toda la investigación del historial

- Sin mediciones independientes de CO₂, depósitos ni lluvia subhoraria local: no se puede certificar
  precisión, profundidad o seguridad de brigadas.
- Generalización entre humedales no demostrada; Okavango conserva resultado negativo y no se publica
  como detección válida. No se inventan etiquetas ni métricas para habilitar modelos.
- Foundation models y deep learning tienen cuaderno y adaptadores, pero no un entrenamiento nuevo
  ejecutado y validado en esta entrega. No se ejecuta GPU de pago contra el crédito limitado.
- Falta estudio con personas reales, revisión científica externa, versión inglesa completa, animación
  y comparador deslizante, datos/validación de glaciar y materiales finales de comunicación.
- No se cambió visibilidad/licencia del repositorio ni se afirma respaldo, venta o aprobación de NASA.
- No se crearon Jobs de adquisición con credenciales Earthdata ni automatizaciones de actualización:
  esta publicación sirve una instantánea verificable, no una plataforma de ingesta continua.

Estas tareas requieren sus propios datos, evaluaciones o decisiones; un despliegue funcional no las sustituye.
