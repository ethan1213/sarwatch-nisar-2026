# Adquisición local de Chile

Se seleccionaron candidatos por inclusión del punto de ciudad en la huella CMR y coincidencia de track, dirección, frame, modo, polarización y frecuencia nominal. No basta la intersección del bbox regional.

La primera opción para ambas ciudades corresponde a 5 y 17 octubre 2026, track 075, ascendente, frame 161, DHDH. Comparte los mismos dos archivos; el destino común evita duplicarlos por región. Tamaño anunciado conjunto: aproximadamente 3,2 GiB. No implica cobertura completa de ambas regiones ni calidad suficiente hasta revisar HDF5.

## Comandos desde la carpeta del proyecto

```powershell
.\.venv\Scripts\python -m pip install -r requirements-acquisition.txt
.\.venv\Scripts\python scripts/download_chile.py --region santiago
```

Earthdata solicitará usuario y contraseña en la terminal local, sin persistir credenciales. No introducirlos en el chat ni en la aplicación web. Los archivos se guardan en data_raw/chile, excluido de Git. El descargador comprueba espacio libre y no declara validación científica ni checksum por completar una transferencia.

Antes de procesar: contrastar checksum oficial CMR, inspeccionar metadatos HDF5, confirmar límites y grillas y recortar áreas de estudio verificadas. La selección nominal no reemplaza esas comprobaciones. La descarga autenticada aún no se ejecutó en esta actualización.

Fuentes y procedimiento oficial: https://nisar-docs.asf.alaska.edu/earthaccess/ y URLs CMR conservadas en catalog/chile_pairs.json.
