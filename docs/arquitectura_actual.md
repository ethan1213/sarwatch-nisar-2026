# Arquitectura implementada

La aplicación conserva Streamlit como adaptador de presentación. La estructura separa las responsabilidades sin introducir servicios de red que todavía no necesita el volumen actual.

| Componente | Responsabilidad |
|---|---|
| app.py | Flujo de exploración y estado de controles |
| sarwatch/repository.py | Validación de manifiesto, límites de rutas y lectura por ventana para series de puntos |
| sarwatch/charts.py | Representación raster con escalas y coordenadas explícitas |
| sarwatch/theme.py | Tratamiento visual compartido |
| science.py | Operaciones numéricas y máscara común |
| weather.py | Adaptador externo opcional, separado del procesamiento SAR |
| scripts/prepare.py | Preparación fuera del servidor web |

Los datos se montan como solo lectura. El procesamiento no se ejecuta al navegar. La interfaz almacena en caché las capas utilizadas para comparación; las series consultan ventanas de un píxel. Las rutas de productos deben permanecer dentro del directorio publicado. La consulta meteorológica falla independientemente de las observaciones SAR.

## Verificación

Pruebas unitarias: unidades, nodata, diferencias, contrato meteorológico y límites de acceso a productos. Prueba funcional AppTest con datos reales: carga, diferencia, polarización y continuidad ante caída meteorológica. La misma prueba se ejecuta en Linux dentro del contenedor.

## Trabajo todavía necesario

Esta separación mejora la base del prototipo; no equivale a una plataforma de producción terminada. Faltan mapa geográfico con interacción directa, evaluación completa de QA, validación ambiental, prueba visual responsive, observabilidad de despliegue y acceso externo. Esas etapas deben conservar la procedencia y comprobarse individualmente.
