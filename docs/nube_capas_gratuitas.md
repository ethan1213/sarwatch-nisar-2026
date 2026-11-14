# SARWatch con la capa gratuita de AWS y los USD 300 de Google Cloud

Fecha: 14 noviembre 2026. Diseños concretos para dos presupuestos reales: el plan gratuito de AWS (hasta USD 200 en créditos durante 6 meses más los servicios "siempre gratis") y la prueba de Google Cloud (USD 300 durante 90 días más su capa "Always Free"). Cifras de los proveedores consultadas hoy; confirmar en la consola al crear la cuenta, porque cambian.

## Qué ofrece cada uno (resumen verificado)

| | AWS plan gratuito (2025–2026) | Google Cloud prueba gratuita |
|---|---|---|
| Créditos | USD 100 al registrarse + USD 100 por completar actividades; expiran a los 6 meses o al agotarse | USD 300; expiran a los 90 días o al agotarse |
| Qué pasa al terminar | La cuenta del plan gratuito se cierra salvo que pases a plan de pago | La cuenta de prueba se cierra; no cobran si no la actualizas manualmente |
| Siempre gratis relevante | Lambda 1 M peticiones y 400.000 GB-s al mes; S3 5 GB; API Gateway 1 M llamadas; DynamoDB 25 GB; CloudFront 1 TB de salida al mes | Cloud Run 2 M peticiones, 180.000 vCPU-s y 360.000 GB-s al mes; Cloud Storage 5 GB regional (us-east1/us-west1/us-central1); BigQuery 1 TB de consultas y 10 GB; una VM e2-micro |
| Ventaja para NISAR | Los datos NISAR están en AWS us-west-2: Lambda puede leerlos por ventana sin descargarlos | Más crédito y Cloud Run es la forma más simple de publicar Streamlit |
| Límite para NISAR | El plan gratuito solo habilita un subconjunto de servicios; nada de Fargate ni GPU; S3 de 5 GB | Cada granulo debe bajarse por HTTPS desde ASF (1,8 GB; NASA no cobra la salida) |

## Diseño 1 · AWS plan gratuito: procesar junto a los datos

```
Pedido de sitio (JSON en S3 o llamada API Gateway)
   → Lambda (us-west-2, 4–6 GB RAM, 10 GB disco efímero, 15 min máx)
       · earthaccess con credenciales Earthdata guardadas en Secrets Manager (o variables cifradas)
       · abre el HDF5 directamente en S3 (acceso directo solo funciona en us-west-2)
       · lee solo la ventana del sitio (100–200 MB en vez de 1,8 GB) y corre prepare.py
       · escribe COG HH/HV/looks y manifiesto en nuestro bucket S3
   → S3 (derivados) + DynamoDB (índice de sitios y fechas)
   → CloudFront sirve COG y JSON a la app (los COG se leen por rangos HTTP)
```

Qué cabe en lo gratuito: con 400.000 GB-s al mes y trabajos de 4 GB × 120 s (480 GB-s) salen unos 800 recortes de sitio-fecha al mes sin gastar crédito. S3 gratis de 5 GB equivale a unos 80 recortes de 60 MB; los siguientes 100 GB cuestan unos USD 2,3 al mes de crédito.

Qué no cabe: la app Streamlit. Fargate y App Runner no están en el plan gratuito; EC2 consumiría crédito. Dos salidas: servir la app desde la laptop o desde Google Cloud Run (Diseño 3), o convertir la vista mundial en una página estática (S3 + CloudFront) que lea los COG por rangos con MapLibre y titiler en Lambda.

Pasos:
1. Crear la cuenta con el plan gratuito, fijar un presupuesto de USD 10 con alarma, no activar servicios de pago.
2. Guardar las credenciales Earthdata en Secrets Manager (nunca en el código).
3. Construir la imagen Lambda desde este repositorio (`python:3.12-slim` con rasterio, h5py, earthaccess y `sarwatch`), subir a ECR y crear la función en us-west-2 con 6 GB de memoria y 10 GB de almacenamiento efímero.
4. Probar con Pantanal una fecha: medir segundos, GB-s y bytes leídos; anotar en `catalog/aois.json`.
5. Publicar los derivados con CloudFront y apuntar `DATA_DIR` de la app a una copia local sincronizada (`aws s3 sync`) o a lectura remota.

Riesgo principal: h5py sobre S3 lee muchos rangos pequeños; si una fecha supera 15 minutos, dividir el sitio en dos ventanas o pasar a AWS Batch cuando haya plan de pago.

## Diseño 2 · Google Cloud con USD 300: todo en una nube, 90 días

```
Usuario → Cloud Run (Streamlit, 1 vCPU, 2 GB, escala a cero) 
            ↓ pedido de sitio
         Cloud Run Jobs (4 vCPU, 8 GB, hasta 24 h): descarga HTTPS desde ASF con Earthdata Login,
            corre prepare.py, borra el HDF5, sube COG a Cloud Storage
         Cloud Storage (derivados, 60 MB por sitio-fecha) montado en Cloud Run con GCS FUSE o leído por HTTPS
         BigQuery: índice mundial de 163.672 granulos (10 GB gratis; 1 TB de consultas gratis) para la vista «Mundo»
         Secret Manager: credenciales Earthdata
```

Presupuesto estimado para 90 días (precios públicos redondeados):

| Partida | Supuesto | Costo 90 días |
|---|---|---|
| Cloud Run app | 2 GB, escala a cero, 3 h de uso real al día | USD 20–30 |
| Cloud Run app durante la demo | mínimo 1 instancia encendida 5 días | USD 10 |
| Cloud Run Jobs | 40 granulos × 15 min × 4 vCPU | USD 8–12 |
| Salida de red hacia usuarios | 20 GB de teselas y COG | USD 2–3 |
| Cloud Storage | 5 GB derivados (dentro de lo gratuito) | 0 |
| BigQuery índice mundial | dentro de lo gratuito | 0 |
| Secret Manager, logs | mínimos | USD 1–3 |
| **Total** | | **USD 45–60 de 300** |

Sobran unos USD 240: alcanzan para 150 granulos más (unos 35 sitios con 4 fechas) o para tener la app encendida sin escalar a cero durante todo el período de evaluación del desafío.

Pasos:
1. Crear el proyecto, activar la prueba, fijar presupuesto de USD 100 con alertas al 50 y 90 %.
2. `gcloud run deploy sarwatch --source . --region us-central1 --memory 2Gi --cpu 1 --port 8080 --allow-unauthenticated --set-env-vars DATA_DIR=/data` con un bucket montado en `/data` (Cloud Run admite volúmenes GCS).
3. Crear el job `sarwatch-prepare` con la misma imagen y el comando `scripts/request_aoi.py prepare`, con la credencial Earthdata desde Secret Manager; el job descarga a disco temporal, prepara y sube.
4. Cargar `catalog/global/gcov_index.csv.gz` en BigQuery y servir las consultas de la vista «Mundo» por punto con una consulta parametrizada (gratis dentro de 1 TB al mes).
5. Antes del día 85, exportar todo a `D:` y decidir si se actualiza a plan de pago o se apaga.

Limitación física: la descarga HTTPS desde ASF a us-central1 es más lenta que leer S3 en us-west-2, pero evita depender de AWS; con 4 jobs en paralelo, 40 granulos se preparan en una tarde.

## Diseño 3 · Híbrido recomendado para este equipo

- **AWS us-west-2 (gratis):** solo procesamiento junto a los datos con Lambda; derivados a S3 de 5 GB; nada de servidores encendidos.
- **Google Cloud (USD 300):** Cloud Run para la app pública, BigQuery para el índice mundial, Cloud Storage como réplica de los derivados (sincronizada con `gsutil rsync` desde S3 o desde la laptop).
- **Laptop + D:** desarrollo, validación científica y copia maestra de los HDF5 que ya tenemos.

Así la historia para el jurado es correcta y verificable: el cómputo pesado ocurre donde NASA aloja los datos, la app es pública en una URL, y ningún TB se copia. Costo total durante el desafío: menos de USD 60 de crédito, cero dinero propio.

## Reglas para no perder las cuentas

1. Presupuesto y alarma antes del primer despliegue en ambas nubes.
2. Nunca crear recursos fuera de las regiones indicadas ni activar GPU.
3. Credenciales Earthdata solo en Secrets Manager / Secret Manager; nunca en Git ni en la imagen.
4. Exportar derivados y manifiestos a `D:` cada semana: si una cuenta se cierra, nada se pierde.
5. Al terminar la prueba, apagar Cloud Run (escala a cero cuesta cero) y vaciar buckets que superen 5 GB.

Fuentes: https://aws.amazon.com/free/free-tier-faqs/ · https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/ · https://cloud.google.com/signup-faqs · https://nisar-docs.asf.alaska.edu/earthaccess/
