# SARWatch · NISAR 2026

La entrada guiada explica lugar, fechas y significado antes de los detalles SAR. Incluye perfiles de público general/ciencia/desarrollo/comunicaciones/gestión, asistente local basado en reglas y fuentes, calculadora de almacenamiento y referencia predictiva retrospectiva. No hay un LLM instalado ni predicción validada de inundación. La evaluación detallada y el plan están en [experiencia, asistente y predicción](docs/experiencia_asistente_y_prediccion.md).

Explorador de cambios de retrodispersión para **Dancing with the SARs**. Equipo Software Detective, Santiago, Chile. Proyecto independiente, sin respaldo implícito de NASA o ISRO.

Pantanal: siete adquisiciones GCOV PROVISIONAL de 2026, HH/HV, frecuencia A. Originales fuera de Git. No hay clasificación de inundaciones validada.

## Ejecutar

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -r requirements-maps.txt
.\.venv\Scripts\python scripts/prepare.py --raw "RUTA_A_LOS_HDF5" --output data
.\.venv\Scripts\python -m streamlit run app.py
```

Con Docker Desktop iniciado y derivados preparados: `docker compose up --build -d`. Abrir http://localhost:8080. Detener con `docker compose down`. Sin derivados, se muestra el catálogo y cómo prepararlos.

Incluye procesamiento por ventana, COG, rechazo de grillas incompatibles, comparación temporal, diferencias, serie de punto y CSV. Meteorología opcional con histórico ERA5 y pronóstico separados; sus errores no bloquean SAR.

## Documentación y estado

- [Plan detallado](docs/plan_implementacion.md)
- [Arquitectura](docs/arquitectura.md)
- [Investigación oficial](docs/investigacion.md)
- [Docker y nube](docs/publicacion_y_github.md)
- [Meteorología](docs/meteorologia.md)
- [Comprobaciones y pendientes](docs/estado.md)

Pruebas: `python -m unittest discover -s tests -v`.

Prototipo exploratorio: filtrado de finitos positivos y fill values declarados. Se aplican las máscaras de calidad descritas por el producto; falta validación ambiental independiente. Incluye mapa geográfico y consulta con clic. Los gráficos conservan UTM. Siete fechas y un AOI no equivalen a cobertura anual o mundial. Código privado por instrucción del propietario; resolver apertura/licencia y acceso del jurado antes de enviar al desafío.

## Chile central

Selector de Pantanal, Región Metropolitana y Valparaíso continental. Chile incluye límites comunales CIREN, mapa base y satelital de contexto, consulta de puntos, pronóstico y candidatos NISAR CMR. No se presentan candidatos como series SAR procesadas. Ver docs/chile_y_mapas.md.

Los entornos urbanos de Santiago y Valparaíso/Viña del Mar incluyen capas NISAR reales del 5 y 17 octubre 2026, verificadas mediante checksum oficial, con HH/HV, diferencia y valores por punto. Son recortes urbanos; no equivalen a cobertura completa de las regiones. Los originales permanecen en data_raw/chile y derivados en data/metropolitana y data/valparaiso, fuera de Git.
