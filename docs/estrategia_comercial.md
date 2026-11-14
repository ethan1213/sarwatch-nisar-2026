# Estrategia para que SARWatch sea vendible — borrador honesto

Fecha: 14 noviembre 2026. Documento de trabajo del equipo Software Detective; no es asesoría legal ni financiera.

## 1. Qué tenemos y qué no

Tenemos: un visor reproducible (Docker) de productos NISAR GCOV con procedencia verificada por checksum; detección de agua abierta evaluada contra etiquetas ópticas independientes en bloques y fechas retenidos; una prueba estadística de cambio (Conradsen) para pares urbanos; un benchmark de pronóstico con baselines obligatorias; un asistente local que no inventa cifras; y documentación de límites en cada capa.

No tenemos: validación con observaciones de terreno, cobertura más allá de tres recortes, usuarios reales que hayan probado la herramienta, licencia definida (el código sigue privado y el desafío pide un resultado abierto), ni una entidad legal que pueda contratar.

## 2. «Venderle a la NASA»: lo que es realista

- **NASA SBIR/STTR** (Phase I hasta USD 225.000; Phase II hasta USD 1.275.000, BAA 2026–2027) exige una *small business concern* con fines de lucro **radicada en Estados Unidos**, registrada en SAM.gov y con mayoría de propiedad estadounidense. Un equipo chileno no califica directamente; sí podría participar como subcontratista de una empresa estadounidense o mediante un socio académico en STTR.
- **NASA no compra aplicaciones de hackatón.** Lo que sí hace: premiar (Space Apps Global Awards), dar visibilidad (ARSET, Applied Sciences, NISAR Science Team), y abrir convocatorias ROSES para investigación (requieren institución elegible).
- **Rutas con NASA que sí están a nuestro alcance:** 1) ganar o quedar finalistas en Space Apps 2026 con evidencia de validación; 2) publicar el método como *open science* (código + datos derivados + métricas) y citarlo en el programa NISAR Early Adopters / ASF; 3) proponer un caso de uso a NASA Applied Sciences Disasters como *demonstration* en Chile con una contraparte local.

## 3. Compradores plausibles (Chile y región)

| Comprador | Necesidad | Qué debemos demostrar |
|---|---|---|
| SENAPRED, gobiernos regionales | Mapas rápidos de agua/cambio tras eventos, con límites claros | Latencia desde adquisición a mapa; F1 por tipo de superficie; procedimiento de QA |
| DGA / MOP | Seguimiento de cuerpos de agua, humedales y crecidas | Serie temporal validada en una cuenca piloto |
| Municipios y planificación urbana | Cambio de suelo y expansión urbana | Prueba de cambio con tasa de falsas alarmas medida |
| Aseguradoras y reaseguradoras | Extensión de inundación para siniestros | Intervalos de incertidumbre y calibración |
| Minería, agricultura, forestal | Monitoreo de faenas, riego, cosecha | AOI bajo demanda con costo medido |
| Universidades y ONG | Plataforma docente y de investigación | Reproducibilidad y licencia abierta |

Fuera de Chile: Brasil (Pantanal) con INPE/ANA como referencia científica, no como comprador inmediato.

## 4. Qué exigirá cualquier comprador (y este plan produce)

1. Métricas en conjuntos retenidos con tarjeta de modelo por capa (`models/*.card.json`, `docs/detection_benchmark.json`, `docs/forecast_benchmark.json`).
2. Reproducibilidad: imagen Docker, manifiestos con hashes, scripts de adquisición sin credenciales embebidas.
3. Procedencia y límites visibles en la interfaz, no solo en documentación.
4. Un piloto con contraparte real (una cuenca o comuna), con criterios de éxito acordados antes de empezar.
5. Licencia definida. Opción recomendada: código abierto (Apache 2.0 o MIT) y servicio de pago por AOI bajo demanda, soporte y despliegue; es compatible con el requisito de resultado abierto del desafío.
6. Material: demo de 3 minutos, una página por perfil (ciencia, gestión, comunicaciones), y un informe de validación.

## 5. Modelo de negocio sugerido

Software abierto + servicio: procesamiento de AOI bajo demanda (precio por km² y fecha, medido en la Fase 7), despliegue gestionado para instituciones, y desarrollo de modelos específicos (cuenca, cultivo) por contrato. Evitar vender «alertas» hasta tener calibración demostrada: una falsa alarma pública destruye la credibilidad del producto.

## 6. Próximos pasos concretos

- Decidir licencia y abrir el repositorio antes de la entrega del desafío.
- Elegir una contraparte piloto en Chile (DGA o un gobierno regional) y una cuenca con datos de terreno.
- Constituir o aliarse con una entidad que pueda contratar; evaluar un socio estadounidense si se busca SBIR/STTR.
- Medir costo por AOI (tiempo, RAM, bytes) con `scripts/request_aoi.py` y publicarlo.

Fuente SBIR/STTR: https://www.nasa.gov/wp-content/uploads/2024/01/nasa-2026-2027-sbir-sttr-baa-appendix-26a-i-sbir.pdf
