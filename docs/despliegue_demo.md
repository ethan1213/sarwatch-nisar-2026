# Despliegue del demo (Google Cloud Run)

Imagen con los derivados verificados dentro; sin buckets ni volúmenes. Los HDF5 originales no entran. La app no tiene usuarios: la URL es pública para quien la conozca.

La imagen de demo copia `data/` (sin `labels/`, `covariates/` ni `okavango/`) y `docs/*.md` salvo cuatro documentos internos (ver `Dockerfile.deploy.dockerignore`). Sin `docs/` el asistente solo recupera el glosario.

## Antes de construir

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python scripts/check_app.py
```

## Construir y probar en local

```powershell
docker compose build
docker build -f Dockerfile.deploy -t sarwatch-nisar:demo .
docker run --rm -p 8080:8080 sarwatch-nisar:demo
```

Abrir http://localhost:8080 y recorrer Pantanal, Santiago, Valparaíso, Mundo y el asistente. Esta imagen no monta nada: si funciona aquí, lleva todo lo que necesita.

## Publicar

Sustituir `PROYECTO` por el ID del proyecto de Google Cloud. Región `southamerica-west1` (Santiago).

```powershell
gcloud auth login
gcloud config set project PROYECTO
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
gcloud artifacts repositories create sarwatch --repository-format=docker --location=southamerica-west1
gcloud auth configure-docker southamerica-west1-docker.pkg.dev
docker tag sarwatch-nisar:demo southamerica-west1-docker.pkg.dev/PROYECTO/sarwatch/app:demo
docker push southamerica-west1-docker.pkg.dev/PROYECTO/sarwatch/app:demo
gcloud run deploy sarwatch --image southamerica-west1-docker.pkg.dev/PROYECTO/sarwatch/app:demo --region southamerica-west1 --port 8080 --memory 2Gi --cpu 2 --min-instances 1 --max-instances 2 --session-affinity --timeout 3600 --allow-unauthenticated
```

- `--min-instances 1` evita el arranque en frío durante la evaluación; tiene costo mientras esté encendida. Al terminar: `gcloud run services update sarwatch --region southamerica-west1 --min-instances 0`, o `gcloud run services delete sarwatch --region southamerica-west1`.
- `--session-affinity` mantiene la sesión WebSocket de Streamlit en la misma instancia.
- Crear una alerta de presupuesto en Facturación antes de publicar.

## Estado

Receta escrita el 14 de noviembre de 2026; no se ha construido ni desplegado todavía. Memoria y CPU son un punto de partida a confirmar con la app cargada.
