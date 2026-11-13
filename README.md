# SARWatch · NISAR 2026

Explorador de cambios de retrodispersión para **Dancing with the SARs**. Equipo Software Detective, Santiago, Chile. Proyecto independiente, sin respaldo implícito de NASA o ISRO.

Pantanal: siete adquisiciones GCOV PROVISIONAL de 2026, HH/HV, frecuencia A. Originales fuera de Git. No hay clasificación de inundaciones validada.

## Ejecutar

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
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

Prototipo exploratorio: filtrado de finitos positivos y fill values declarados. Falta revisar máscaras QA, validación ambiental, mapa base mundial y consulta con clic. La vista usa UTM. Siete fechas y un AOI no equivalen a cobertura anual o mundial. Código privado por instrucción del propietario; resolver apertura/licencia y acceso del jurado antes de enviar al desafío.
