# Arquitectura GCP recomendada: eficiente y escalable, dentro de los USD 300

Fecha: 14 noviembre 2026. Decisión única (no opciones) para los USD 300 de la oferta global de Space Apps. Complementa `docs/arquitectura_nube.md` (comparación inicial) y `docs/despliegue_demo.md` (receta de demo ya escrita por el equipo, que esta arquitectura reutiliza y extiende para que escale más allá de una demo puntual).

**Regla de seguridad, repetida porque ya se pegaron credenciales dos veces en el chat:** ninguna contraseña, email o clave entra a este documento, a un comando, ni a mí. Todo `gcloud auth login` lo escribes tú en el navegador. Las claves de Earthdata para los *Jobs* de procesamiento se crean con `gcloud secrets create ... --data-file=-` y las escribes tú en tu propia terminal.

## 1. Por qué esta forma y no otra

| Necesidad | Servicio elegido | Por qué es el eficiente |
|---|---|---|
| Servir la app al público | **Cloud Run (servicio)**, `min-instances=0` | Pago por uso real; en reposo cuesta 0. Para la demo del jurado se sube a `min-instances=1` solo esas horas |
| Procesar un AOI nuevo (HDF5 → COG → etiquetas → evaluación) | **Cloud Run Jobs** | Un contenedor por AOI, se apaga al terminar; no hay un servidor de cómputo encendido esperando trabajo |
| Guardar derivados (COG, catálogos, referencias) más allá de lo que trae la imagen | **Cloud Storage**, clase Standard, con regla de borrado automático de intermedios | 5 GB gratis todo el tiempo; el resto a ~USD 0,02/GB-mes, mucho más barato que mantener un disco de VM |
| Credencial Earthdata para los Jobs | **Secret Manager** | Nunca en el código ni en variables de entorno planas del servicio web |
| Imagen Docker | **Artifact Registry** | Ya lo usa `docs/despliegue_demo.md`; sin cambios |
| Índice mundial (163 mil granulos) | Un archivo en el propio Cloud Storage, servido por Cloud Run, **no BigQuery** | BigQuery sería correcto a mayor escala, pero para 35.553 celdas y un archivo de 7 MB es sobre-ingeniería hoy; se revisita en la sección 5 |

No se usa Compute Engine, GKE ni Cloud SQL: a esta escala (tres sitios y creciendo) agregan costo fijo sin necesidad.

## 2. Diagrama

```
Usuario → Cloud Run (app Streamlit, southamerica-west1, min=0, max=3)
             lee de → Cloud Storage: gs://sarwatch-PROYECTO-data/ (derivados, catálogo mundial)
             lee secreto → Secret Manager (solo si el usuario pide procesar un AOI desde la UI; hoy no)

Operador (tú) → Cloud Run Jobs "sarwatch-prepare-aoi"
             lee secreto Earthdata de Secret Manager
             descarga HDF5 a disco efímero del Job, prepara COG, sube a Cloud Storage, borra el HDF5
             nunca escribe el HDF5 en un volumen persistente

Cloud Scheduler (opcional, semanal) → dispara un Job "sarwatch-refresh-index" que corre
             scripts/build_global_catalog.py y sube el resultado a Cloud Storage
```

## 3. Eficiencia concreta (no genérica)

1. **Escala a cero por defecto.** `--min-instances 0` en el servicio. Solo durante la presentación al jurado: `gcloud run services update sarwatch --min-instances 1`, y volver a 0 después.
2. **Imagen pequeña.** Reusar la imagen base (`Dockerfile`) sin los derivados pesados; los derivados viven en Cloud Storage y se montan con `gcsfuse` o se leen por HTTP firmado, no se hornean en la imagen salvo para la demo puntual (`Dockerfile.deploy` ya hace esto bien para esa demo).
3. **Ciclo de vida en Cloud Storage.** Regla de borrado a 30 días para cualquier cosa bajo `tmp/` o `raw-cache/`; los COG verificados quedan indefinidamente porque pesan poco (medido: ~0,6 GB por los tres sitios actuales).
4. **Concurrencia del servicio.** Streamlit es monousuario por sesión (WebSocket); usar `--concurrency 4` y `--cpu 1 --memory 1Gi` por instancia en vez de una instancia grande: Cloud Run factura por instancia activa, no por usuario, así que varias instancias pequeñas escalan mejor que una grande con `min-instances` alto.
5. **Región southamerica-west1 (Santiago).** Menor latencia para el público objetivo (Chile) y es la misma región que ya eligió el equipo en `docs/despliegue_demo.md`; no hay beneficio real en us-west1 porque los datos NISAR llegan por HTTPS vía Planetary Computer/ASF, no por lectura directa S3 desde GCP.
6. **Jobs, no un servidor de cómputo permanente, para procesar AOI.** Un Job de Cloud Run con `--tasks N` puede preparar N AOI en paralelo y cobra solo los minutos de CPU usados; esto es lo que de verdad hace la arquitectura "escalable": agregar un AOI nuevo es ejecutar el Job, no aprovisionar más infraestructura.

## 4. Comandos (ejecútalos tú, en orden, después de `gcloud auth login`)

```powershell
# 0. Autenticación (se abre el navegador; tú escribes tu cuenta de Google ahí, nunca aquí)
gcloud auth login
gcloud config set project PROYECTO

# 1. Presupuesto y alarma ANTES de crear nada (ajusta el monto)
gcloud billing budgets create --billing-account=CUENTA_FACTURACION --display-name="SARWatch 300" --budget-amount=300 --threshold-rule=percent=0.5 --threshold-rule=percent=0.9

# 2. APIs necesarias
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com cloudscheduler.googleapis.com

# 3. Bucket de derivados (Standard, una sola región para evitar cargos de multi-región)
gcloud storage buckets create gs://sarwatch-PROYECTO-data --location=southamerica-west1 --uniform-bucket-level-access
gcloud storage buckets update gs://sarwatch-PROYECTO-data --lifecycle-file=- <<'JSON'
{"rule":[{"action":{"type":"Delete"},"condition":{"age":30,"matchesPrefix":["tmp/","raw-cache/"]}}]}
JSON

# 4. Repositorio de imágenes
gcloud artifacts repositories create sarwatch --repository-format=docker --location=southamerica-west1
gcloud auth configure-docker southamerica-west1-docker.pkg.dev

# 5. Secreto de Earthdata para los Jobs (escribe tu usuario:contraseña reales AQUÍ, en tu terminal, no en el chat)
#    El valor nunca se muestra ni se repite en ningún log.
echo -n "TU_USUARIO_EARTHDATA" | gcloud secrets create earthdata-username --data-file=-
# PowerShell pedirá la contraseña de forma interactiva con Read-Host -AsSecureString si prefieres no tipearla en texto plano:
gcloud secrets create earthdata-password --data-file=-   # pega y Ctrl+Z Enter (Windows) para cerrar stdin

# 6. Construir y publicar la imagen base
docker build -t southamerica-west1-docker.pkg.dev/PROYECTO/sarwatch/app:latest .
docker push southamerica-west1-docker.pkg.dev/PROYECTO/sarwatch/app:latest

# 7. Desplegar el servicio web, escalado a cero
gcloud run deploy sarwatch `
  --image southamerica-west1-docker.pkg.dev/PROYECTO/sarwatch/app:latest `
  --region southamerica-west1 --port 8080 `
  --cpu 1 --memory 1Gi --concurrency 4 `
  --min-instances 0 --max-instances 3 `
  --session-affinity --timeout 3600 `
  --set-env-vars DATA_DIR=/app/data `
  --allow-unauthenticated

# 8. Job de procesamiento de AOI bajo demanda (usa el mismo Dockerfile; el comando cambia)
gcloud run jobs create sarwatch-prepare-aoi `
  --image southamerica-west1-docker.pkg.dev/PROYECTO/sarwatch/app:latest `
  --region southamerica-west1 --cpu 2 --memory 4Gi --task-timeout 1800 `
  --set-secrets EARTHDATA_USERNAME=earthdata-username:latest,EARTHDATA_PASSWORD=earthdata-password:latest `
  --command python --args scripts/request_aoi.py,prepare,--name,SITIO

# Ejecutar el job para un sitio puntual:
gcloud run jobs execute sarwatch-prepare-aoi --region southamerica-west1 --update-env-vars SITIO_NAME=araucania
```

**Antes de la evaluación del jurado**, y solo entonces:
```powershell
gcloud run services update sarwatch --region southamerica-west1 --min-instances 1
```
**Al terminar**, siempre:
```powershell
gcloud run services update sarwatch --region southamerica-west1 --min-instances 0
```

## 5. Cuándo esta arquitectura deja de ser suficiente (y qué agregar entonces)

| Señal de que hay que escalar más | Qué agregar |
|---|---|
| Más de ~50 sitios o el índice mundial ya no cabe cómodo en un archivo | BigQuery para el índice, consultado por SQL en vez de pandas en memoria |
| Varios usuarios concurrentes pidiendo el mismo AOI a la vez | Cola (Cloud Tasks o Pub/Sub) delante de los Jobs, para no duplicar procesamiento |
| Necesidad de servir teselas (no solo capas completas) | `titiler` en una Cloud Run aparte, leyendo los COG directo de Cloud Storage por rango HTTP |
| Presupuesto agotado antes de terminar | Bajar a `--cpu 1 --memory 512Mi`, o mover el servicio web a la capa Always Free (2 M peticiones/mes) y dejar Jobs solo para lo imprescindible |

No agregar nada de esta tabla antes de necesitarlo: es la forma de que los USD 300 duren todo el período de evaluación.
