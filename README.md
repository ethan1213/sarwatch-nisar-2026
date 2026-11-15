# SARWatch · análisis territorial para brigadas

[**Abrir la aplicación en GCP**](https://sarwatch-525550511866.southamerica-west1.run.app)

Plataforma de análisis territorial con focos FIRMS, clima horario a 48 horas, relieve 2D/3D, inspección de sectores laterales al viento y exportación de evidencia. El diseño adapta la propuesta compartida en Figma. Biobío incluye radar NISAR, calor histórico GOES y cinco delimitaciones Copernicus EMS del 21 al 25 de enero de 2026. Viña incorpora imágenes Sentinel-2 del 18 de enero y 12 de febrero de 2024, separadas del radar de octubre de 2026. Pantanal no aparece en la navegación pública.

[Funcionamiento, fuentes y alcance de los modelos](docs/figma_y_brigadas.md).

- Calor GOES-19 por hora y meteorología histórica ERA5.
- Señal de quema Sentinel-2 y evolución posterior NISAR L2 GCOV (febrero, junio y octubre).
- Prioridad de vigilancia exploratoria, con resultados en fechas y bloques espaciales retenidos.
- Consulta guardada de FIRMS VIIRS, separada del pronóstico meteorológico actual.
- Elevación y pendiente por celda, relieve 3D y fotografía Esri de contexto.
- Comparación lateral respecto al viento con alturas y pendientes; sin inferir una ruta segura.
- Caso óptico del incendio de Viña 2024 y delimitaciones observadas de Copernicus EMS para Biobío.
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
- [Video narrado con capturas y voz sintética local](docs/entrega/demo_narrada.mp4), [guion](docs/entrega/guion_2min.md), [resumen en inglés](docs/entrega/resumen_en.md) y [uso de IA y fuentes](docs/entrega/uso_de_ia.md).
- [Despliegue y presupuesto GCP](docs/cierre_gcp.md).

## Licencia

Código propio bajo [Apache-2.0](LICENSE), autorizado por el propietario el 15 de noviembre de 2026. Los datos, mapas, dependencias y tipografías conservan las licencias y atribuciones de sus proveedores. No se publica ningún modelo de lenguaje externo en el producto.
