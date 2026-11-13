# GitHub privado, Docker y nube

Repositorio creado: https://github.com/ethan1213/sarwatch-nisar-2026 (privado). Los colaboradores requieren usuario GitHub o correo verificable; no asumir que un alias Space Apps pertenece a esa misma persona en GitHub.

## Docker

Python 3.14, usuario 10001, `PORT` configurable (8080), escucha 0.0.0.0, healthcheck `/_stcore/health`. Compose publica localhost y monta `./data` como solo lectura. Validar con `docker compose config --quiet`; iniciar `docker compose up --build -d`; consultar `docker compose ps`.

Datos: `data/manifest.json` y sus COG. No se incluyen en Git ni imagen base. En nube montar almacenamiento compatible o descargar un conjunto verificado al iniciar; esa configuración es específica del proveedor. No existe todavía un adaptador universal de almacenamiento.

| Destino | Ruta | Adaptación |
|---|---|---|
| VM Linux en cualquier proveedor compatible | Docker Compose | Copiar derivados, proxy TLS/WebSocket, DNS y firewall. Ruta inicial más directa |
| Google Cloud Run | Imagen en Artifact Registry, puerto 8080 | Datos al inicio/volumen, RAM, timeout WebSocket y reconexión; no asumir persistencia del disco |
| Azure Container Apps | Imagen Linux amd64, ingress 8080 | Datos, probes, recursos y secretos |
| AWS ECS/Fargate | Imagen ECR, tarea y balanceador | Datos accesibles, IAM, red y timeout/WebSocket |

Portabilidad de imagen no elimina configuración de redes, almacenamiento e identidad. No se ha contratado ni aprovisionado nube. Para demos pequeñas puede construirse una imagen de despliegue que copie solo derivados verificados; HDF5 fuera. Para escala: COG en object storage y teselas separadas.

El código privado no hace privada la app. Este prototipo no implementa usuarios; para publicar con acceso restringido usar autenticación del proveedor/proxy. Earthdata solo se usa en adquisición separada, nunca en navegador.

Actualizaciones: imagen etiquetada con SHA, pruebas y salud, nueva revisión, conservar anterior para rollback. Publicar código no debe sobrescribir datos automáticamente.

Fuentes: https://docs.docker.com/reference/compose-file/services/ · https://docs.cloud.google.com/run/docs/container-contract · https://docs.cloud.google.com/run/docs/triggering/websockets · https://learn.microsoft.com/en-us/azure/container-apps/containers · https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
