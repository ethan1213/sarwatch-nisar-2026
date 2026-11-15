# SARWatch · evidencia satelital de Biobío

[**Abrir la aplicación en GCP**](https://sarwatch-525550511866.southamerica-west1.run.app)

Una historia en tres preguntas: **qué ocurrió, qué quedó y qué podemos anticipar**. La entrada pública se centra en los incendios de enero de 2026 en Biobío. Cada paso muestra un mapa principal; fuentes, métodos y métricas se consultan a demanda. Pantanal no aparece en la navegación pública.

- Calor GOES-19 por hora y meteorología histórica ERA5.
- Señal de quema Sentinel-2 y evolución posterior NISAR L2 GCOV (febrero, junio y octubre).
- Prioridad de vigilancia exploratoria, con resultados en fechas y bloques espaciales retenidos.
- Consulta guardada de FIRMS VIIRS, separada del pronóstico meteorológico actual.
- Estudios adicionales de Chile, asistente explicativo local con cifras verificadas y herramientas reproducibles.

No hay imagen NISAR anterior al incendio de enero en la geometría seleccionada. No se presenta como comparación radar antes/después del fuego. La señal óptica no es un perímetro oficial y el índice exploratorio no es una alerta operativa. No se ofrecen rutas seguras ni mediciones certificadas de emisiones. Proyecto independiente de Software Detective, sin patrocinio ni respaldo institucional de NASA, ISRO o NOAA.

## Ejecutar y verificar

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -r requirements-maps.txt -r requirements-api.txt -r requirements-ml.txt -r requirements-assistant.txt
.\.venv\Scripts\python -m uvicorn api.main:app --port 8010
```

En otra terminal:

```powershell
cd web
npm ci
npm run dev
```

La historia de Biobío usa `catalog/fire_story/`, incluido en Git. Otros comparadores requieren derivados locales o la instantánea Docker; no se inventan capas si faltan. Los originales HDF5 y las credenciales Earthdata están excluidos de Git. El visor Streamlit anterior se conserva como herramienta de trabajo; la aplicación pública usa React/MapLibre y FastAPI.

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -q
.\.venv\Scripts\python scripts/evaluate_assistant.py
.\.venv\Scripts\python scripts/check_api.py https://sarwatch-525550511866.southamerica-west1.run.app
cd web
npm run lint
npm run build
```

## Datos, resultados y entrega

- [Plan y estado de cierre](docs/entrega/estado.md).
- [Evaluaciones térmicas y correcciones del método](docs/calor_y_focos.md).
- [Resultados Biobío](docs/fire_benchmark_biobio.json) y [señal de quema](docs/burn_scar_benchmark.json).
- [Inventario de modelos](docs/modelos_ia_ml.md), [tarjetas](models/) y [plan original del MVP](docs/plan_mvp_incendios.md).
- [Guion de demostración](docs/entrega/guion_2min.md), [resumen en inglés](docs/entrega/resumen_en.md) y [uso de IA y fuentes](docs/entrega/uso_de_ia.md).
- [Despliegue y presupuesto GCP](docs/cierre_gcp.md).

## Licencia

Código propio bajo [Apache-2.0](LICENSE), autorizado por el propietario el 15 de noviembre de 2026. Los datos, mapas, dependencias y tipografías conservan las licencias y atribuciones de sus proveedores. No se publica ningún modelo de lenguaje externo en el producto.
