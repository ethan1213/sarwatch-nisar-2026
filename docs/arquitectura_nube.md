# Arquitecturas de nube para SARWatch — análisis con cifras medidas

Fecha: 14 noviembre 2026. Hechos de partida medidos en CMR y en este equipo:

| Hecho | Valor |
|---|---|
| Granulos NISAR GCOV provisionales en el catálogo | 163.672 (más 23.527 beta) |
| Tamaño medio de un granulo | 1,82 GB; huella ≈ 336 × 325 km |
| Volumen total del archivo GCOV | ≈ 291 TB, creciendo con el ciclo de 12 días |
| Derivados por sitio de 0,5° y fecha (HH, HV, looks, máscaras) | ≈ 60 MB |
| Tiempo de preparación de un sitio por fecha en la laptop | 1 a 2 minutos por granulo |
| Velocidad de descarga observada desde ASF a Chile | ≈ 8 MB/s (3,3 GB en 7 minutos) |
| Disco local | C: 8 GB libres; D: externo 465 GB libres |

Conclusión que ordena todo lo demás: **el archivo completo no se copia; se indexa completo y se procesa por sitio donde viven los datos**. Los datos NISAR están en Earthdata Cloud (AWS, región `us-west-2`) y ASF documenta que el acceso directo S3 solo funciona desde esa región. Mover el cómputo allí elimina la descarga; mover los datos a otra nube la multiplica.

## Opción A · Local + disco externo (hoy)

Índice mundial desde CMR en la laptop; sitios bajo demanda descargados a `D:\NISAR\raw` con Earthdata Login; derivados en `data/`; app en Docker local.

- Capacidad: D: admite unos 250 granulos (≈ 60 sitios × 4 fechas). Tiempo: 4 minutos por granulo entre descarga y preparación.
- Costo: cero. Límite: una persona, una conexión, sin acceso externo.
- Sirve para: desarrollo, validación científica y la demo del desafío.

## Opción B · Procesamiento en AWS us-west-2 junto a los datos (recomendada para escalar)

```
usuario → CloudFront → app (ECS Fargate o App Runner, Streamlit)
                 ↓ pide un sitio
            API + cola (SQS) → AWS Batch / Fargate Spot en us-west-2
                 ↓ earthaccess, acceso directo S3 a Earthdata (sin descarga)
            prepare.py → COG + máscaras → S3 propio → STAC (pgstac en RDS o archivo estático)
                 ↓
            titiler (Lambda) sirve teselas; la app solo recibe teselas y JSON de punto
```

- Lectura de HDF5 por ventana desde S3 sin copiar el granulo: el recorte de 0,5° lee del orden de 100 a 200 MB en vez de 1,8 GB.
- Costo orientativo (precios públicos redondeados, noviembre 2026, a confirmar en la calculadora de AWS): cómputo Spot ≈ USD 0,01 a 0,03 por granulo procesado; almacenamiento S3 de derivados ≈ USD 0,023 por GB-mes (1.000 sitios × 10 fechas ≈ 600 GB ≈ USD 14 al mes); teselas por Lambda y CloudFront: centavos por mil peticiones; app Fargate pequeña ≈ USD 30 a 40 al mes si está siempre encendida.
- Egreso: servir teselas a usuarios tiene costo por GB; los HDF5 nunca salen de AWS.
- Riesgo: cuenta AWS, IAM y presupuesto que hoy no existen. Capa gratuita y créditos para estudiantes o startups pueden cubrir el piloto.

## Opción C · Google Cloud o Azure

Cloud Run / Container Apps para la app y Batch para procesar. Problema: cada granulo debe salir de AWS por HTTPS (NASA no cobra el egreso al usuario, pero la velocidad es la de internet pública) y entrar a la otra nube. Útil solo si ya existen créditos en esa nube. Microsoft Planetary Computer sigue siendo la fuente de etiquetas ópticas y covariables desde cualquier nube.

## Opción D · Serverless puro bajo demanda

Sin servidores encendidos: la app estática (mapa de cobertura + teselas) en S3 + CloudFront; peticiones de sitio nuevo disparan Lambda o Batch; Streamlit se reemplaza por una SPA ligera (MapLibre) que consume STAC y teselas. Costo casi nulo en reposo; requiere reescribir la interfaz. Camino natural después de B.

## Comparación

| Criterio | A Local | B AWS us-west-2 | C GCP/Azure | D Serverless |
|---|---|---|---|---|
| Copia del archivo | No (índice) | No (lee S3 en sitio) | Descarga por HTTPS | No |
| Costo mensual piloto (10 sitios) | 0 | ≈ 40 a 60 USD | ≈ 60 a 100 USD | < 10 USD en reposo |
| Tiempo por sitio nuevo (4 fechas) | ≈ 15 min | ≈ 3 a 5 min | ≈ 15 min | ≈ 5 min |
| Acceso público | No | Sí | Sí | Sí |
| Esfuerzo de implementación | Hecho | Medio | Medio | Alto |
| Historia para NASA | Débil | Fuerte (usa Earthdata Cloud como está diseñado) | Media | Fuerte |

## Lo que la app muestra en cada caso

1. **Mapa mundial de cobertura** (índice CMR completo): dónde hay datos, cuántas fechas, primera y última fecha. Esto cubre "toda la Tierra" sin descargarla.
2. **Sitios procesados** con sus capas evaluadas y métricas.
3. **Botón "procesar este lugar"**: en A genera la orden para el operador; en B/D lanza el trabajo y avisa cuando está.

## Decisión propuesta

Seguir en A hasta la entrega del desafío con 8 a 10 sitios y varios tipos de cambio, y diseñar B en paralelo con una cuenta AWS de bajo presupuesto (≤ USD 50 al mes, con alarma de gasto). D queda como evolución si hay usuarios.

Fuentes: https://nisar-docs.asf.alaska.edu/earthaccess/ (acceso S3 en us-west-2) · https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html · https://aws.amazon.com/s3/pricing/ · https://aws.amazon.com/fargate/pricing/
