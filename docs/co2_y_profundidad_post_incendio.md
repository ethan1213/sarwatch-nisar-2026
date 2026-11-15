# Diseño: CO2 post-incendio y profundidad/volumen de aluvión — antes de programar

> Actualización de implementación: los módulos y laboratorio React ya existen; ver `cierre_gcp.md`.
> Corrección científica del diseño original: Tabla 2.4 del IPCC informa SE, no SD; Tabla 2.5 informa SD.
> El rango implementado es sensibilidad, no confianza estadística. El volumen no se calcula sin i15
> observada y no se sustituye por precipitación horaria. El texto siguiente se conserva como diseño histórico.

Pedido del propietario (14 nov 2026): medir CO2 después de un incendio, un modelo con el DEM para
estimar profundidad y ayudar a los equipos de forma correctiva, y confirmar que SAR + infrarrojo ya
está listo. Este documento es el diseño, revisable antes de escribir una sola línea de
`sarwatch/ml/*`. Sigue el mismo patrón que `docs/postfuego_las_condes.md` y
`sarwatch/ml/debris_flow.py`: cada número viene de una fuente citable, cada supuesto propio (no de la
fuente) queda marcado como tal, y nada se presenta como calibrado para Chile porque no lo está.

## 0. Lo que ya está listo (confirmado, no se repite)

**SAR + infrarrojo: ya construido.** `sarwatch/views/thermal.py` (vista "Calor y focos"),
`scripts/fetch_thermal.py` y `scripts/evaluate_fire.py` cruzan focos térmicos GOES-19 (3,9/11,2 µm,
temperatura de brillo y LST) con NISAR, DEM y WorldCover por celda, evaluado en
`docs/fire_benchmark.json` / `catalog/thermal_reference.json`. `docs/calor_y_focos.md` ya documenta
por qué no se usa LSA SAF (EUMETSAT): no cubre Chile y está bloqueado desde esta máquina; GOES-19 es
su equivalente real para América. No hay nada pendiente aquí salvo lo que ya lista ese documento.

Lo que sigue (CO2 y profundidad) son dos módulos nuevos. Ninguno existe hoy en el repositorio
(verificado con búsqueda de texto completo).

## 1. Módulo A — CO2 emitido por el incendio

### Método: IPCC 2006, Volumen 4 ("AFOLU"), Capítulo 2, Ecuación 2.27 (Tier 1)

Es el método estándar usado en inventarios nacionales de gases de efecto invernadero para emisiones
de incendios; no requiere modelo propio ni calibración, solo área quemada y tipo de vegetación, que
ya podemos obtener.

```
L_fire = A · M_B · C_f · G_ef · 10⁻³
```

- `L_fire`: toneladas del gas (aquí, CO2).
- `A`: área quemada, ha. **Ya la tenemos**: `sarwatch/ml/wildfire.py::severity_class` da 5 clases
  (0 sin quema … 4 alta) por píxel de dNBR; contar píxeles por clase × área de píxel = `A` por clase.
- `M_B · C_f`: cuando no hay biomasa y factor de combustión medidos por separado (no los tenemos),
  IPCC permite usar directamente el **consumo de combustible por defecto** de su Tabla 2.4
  (toneladas de materia seca por hectárea), ya multiplicado.
- `G_ef`: factor de emisión de su Tabla 2.5 (g de CO2 por kg de materia seca quemada).

Valores verificados directamente del PDF oficial (`2006gl/pdf/4_Volume4/V4_02_Ch2_Generic.pdf`,
Tablas 2.4 y 2.5; media ± desviación estándar, revisión de Andreae & Merlet 2001):

| Categoría (Tabla 2.4, consumo de combustible) | t materia seca / ha |
|---|---|
| Todos los matorrales ("All Shrublands") | 14,3 ± 9,0 |
| Bosque templado, todos ("other" temperate forests) | 50,4 ± 53,7 |
| Pastizal/sabana, quema media-tardía | 10,0 ± 10,1 |

| Categoría (Tabla 2.5, factor de emisión) | g CO2 / kg materia seca |
|---|---|
| Sabana y pastizal | 1613 ± 95 |
| Bosque extratropical (incluye todo bosque no tropical) | 1569 ± 131 |

### Qué falta y cómo se resuelve con fuentes ya identificadas en el proyecto

- **Tipo de vegetación por píxel**: no viene de NISAR ni del dNBR. Se resuelve con **ESA WorldCover
  10 m**, ya identificado como covariable en `docs/modelos_ia_ml.md` (Fase 1, vía Planetary
  Computer/`pystac-client`, sin cuenta). Mapeo WorldCover → categoría IPCC: `Shrubland`→matorrales,
  `Tree cover`→bosque templado, `Grassland`→sabana/pastizal. Clases no vegetadas (`Built-up`,
  `Bare/sparse`, `Water`) se excluyen del cálculo.
- **Severidad → fracción de combustible realmente consumido**: IPCC no desglosa esto por severidad
  remota (su tabla es un promedio "por incendio"). Propuesta propia (no es un valor de IPCC, se
  documenta así en el código): escalar el consumo de la Tabla 2.4 por clase dNBR, con la clase 4
  (alta) como referencia 1,0 — `{1: 0.15, 2: 0.4, 3: 0.7, 4: 1.0}` — mismo patrón de factores
  acotados y nombrados que `sarwatch/ml/debris_flow.py`. Estos cuatro números son un supuesto de
  ingeniería, no de la literatura; quedan abiertos a que el equipo los ajuste antes de publicar nada.

### Salida propuesta

Toneladas de CO2 por clase de severidad y total, **como rango** (propagando la ± de ambas tablas, no
un número único), con la receta exacta impresa junto al resultado (igual que `debris_flow.py::explain`).
Comparación de magnitud contra GFED (Global Fire Emissions Database) solo como control de orden de
magnitud, nunca como validación.

**Límites que van en el mismo archivo, no en una nota aparte:** son valores por defecto de Tier 1
globales, no calibrados para matorral chileno; WorldCover a 10 m puede confundir matorral ralo con
suelo desnudo; la escala por severidad es un supuesto propio explícito; esto es un orden de magnitud
para comunicar impacto, no un inventario de carbono certificable.

### Archivos propuestos

`sarwatch/ml/emissions.py` (tablas IPCC como constantes citadas, `co2_emitted(severity, worldcover, pixel_area_m2)`),
`scripts/estimate_fire_emissions.py` (pipeline → `docs/emissions_benchmark.json`,
`catalog/emissions_reference.json`), `tool_emissions` en `sarwatch/assistant/tools.py`, capa/caption
en el visor (`sarwatch/postfire.py` o la vista que corresponda).

## 2. Módulo B — Profundidad y volumen de aluvión (apoyo correctivo a brigadas)

Dos niveles. El primero no tiene huecos de datos y se puede construir ya; el segundo da un número en
m³ pero depende de un dato de lluvia que hoy no tenemos a la resolución que pide el modelo.

### Nivel 1 (disponible ya): índice relativo de concentración/profundidad

Responde exactamente lo que pidió el experto citado en `docs/postfuego_las_condes.md` §4: dónde es
más difícil el acceso y dónde se concentraría más material, para priorizar brigadas — no un volumen
en metros cúbicos. Reutiliza lo que ya existe en `sarwatch/ml/hydrology.py`
(`flow_accumulation`, pendiente del DEM) y la severidad del incendio, combinados con el mismo patrón
multiplicativo y acotado de `debris_flow.py`:

```
índice = concentración(flow_accumulation) × pendiente_normalizada × severidad_alta_fracción
```

Salida: 0–1 por sub-cuenca (`subbasin_labels` ya etiqueta sub-cuencas), solo un **ranking**, nunca
presentado en metros. Esto sí se puede programar hoy sin dato adicional.

### Nivel 2 (da m³ reales, con un hueco de dato pendiente): modelo de Gartner et al. (2014)

Verificado directamente del PDF del artículo original (Engineering Geology 176, 45–56,
doi:10.1016/j.enggeo.2014.04.008), es el modelo que USGS usa operativamente para evaluaciones de
emergencia de aluviones post-incendio ("emergency assessment model", su Ecuación 3):

```
ln(V) = 4,22 + 0,39·√i15 + 0,36·ln(Bmh) + 0,13·√R
```

- `V`: volumen de sedimento (m³).
- `i15`: intensidad de lluvia pico en 15 minutos (mm/h).
- `Bmh`: área de la cuenca quemada a severidad moderada-alta y alta (km²). **Ya la tenemos** (misma
  fuente que `coarse_high_fraction` en `scripts/evaluate_postfire.py`, solo falta convertir fracción
  a km² con el área real de la sub-cuenca).
- `R`: relieve de la cuenca = elevación máxima − mínima dentro de la sub-cuenca (m). **Se calcula
  directo del DEM** ya cargado (`covariates/dem.tif`) usando las etiquetas de `subbasin_labels`, que
  ya existen; no hay módulo nuevo que escribir para esto, es una agregación.
- Ajuste del modelo: R² ajustado 67,0 %, error estándar residual en escala log `S = 1,04`, n = 79.
  Esto permite dar un intervalo, no un número suelto:
  `V ∈ [exp(ln V − 1,96·S), exp(ln V + 1,96·S)]` (≈ intervalo del 95 %).
- Rango de calibración de los datos del artículo (fuera de este rango, se debe avisar
  "fuera del rango de calibración del modelo", no ocultarlo): `i15` 3–72 mm/h, `Bmh` 0,01–15,01 km²,
  `R` 100–2028 m.

**El hueco real: no tenemos `i15`.** `weather.py::fetch_weather` (Open-Meteo) da precipitación diaria
acumulada, no intensidad pico en 15 minutos; `docs/postfuego_las_condes.md` §5 ya señalaba esto como
pendiente para el factor "carga del cauce". Antes de programar el Nivel 2 hay que resolver esto, en
orden de preferencia:

1. Revisar si el endpoint horario de Open-Meteo (`hourly=precipitation`) alcanza una aproximación
   razonable (no es 15 min real, pero acerca más que el dato diario; se documentaría la diferencia).
2. Pedir series pluviométricas sub-horarias reales a DGA/Senapred/CR2 para Quebrada Honda (la misma
   fuente que `docs/postfuego_las_condes.md` ya recomienda para calibrar el umbral).
3. Si ninguna está lista a tiempo, publicar solo el **Nivel 1** (índice relativo) y dejar el Nivel 2
   documentado como "pendiente de dato de lluvia sub-horaria", igual que el proyecto ya hace con la
   interferometría GUNW (implementada, sin datos reales aún).

### Archivos propuestos

`sarwatch/ml/debris_volume.py`: `relative_depth_index(flow_accumulation, slope, severity_fraction)`
(Nivel 1, sin dependencias nuevas) y `gartner_emergency_volume(i15_mm_h, burned_moderate_high_km2,
relief_m)` (Nivel 2, cita el paper en el docstring, implementado pero gateado por disponibilidad de
`i15`). Extensión de `scripts/evaluate_postfire.py` para calcular `R` por sub-cuenca con el DEM ya
cargado. Tarjeta de modelo en `models/` como las demás, dejando explícito que el modelo fue calibrado
en California (Transverse Ranges), no en Chile.

## 3. Decisiones que necesito del propietario antes de programar

1. **CO2**: ¿de acuerdo con presentarlo como rango IPCC Tier 1 (orden de magnitud, no inventario
   certificado), con los cuatro factores de severidad como supuesto propio explícito, o prefieres
   otro reparto de esos factores?
2. **Profundidad/volumen**: ¿construyo el Nivel 1 (índice relativo) ahora mismo, y dejo el Nivel 2
   (volumen en m³, Gartner et al.) con el código escrito pero marcado "pendiente de i15" hasta que
   definamos la fuente de lluvia sub-horaria? ¿O prefieres que primero pruebe el endpoint horario de
   Open-Meteo como aproximación, aunque no sea el dato de 15 minutos real?

## Fuentes

- Gartner, J.E., Cannon, S.H., Santi, P.M. (2014). "Empirical models for predicting volumes of
  sediment deposited by debris flows and sediment-laden floods in the transverse ranges of southern
  California." *Engineering Geology*, 176, 45–56. doi:10.1016/j.enggeo.2014.04.008 — ecuación,
  coeficientes y estadísticas de ajuste verificados directamente del PDF del artículo.
- IPCC (2006). *2006 IPCC Guidelines for National Greenhouse Gas Inventories*, Volumen 4
  ("Agriculture, Forestry and Other Land Use"), Capítulo 2 ("Generic Methodologies Applicable to
  Multiple Land-Use Categories"): Ecuación 2.27, Tabla 2.4 (consumo de combustible), Tabla 2.5
  (factores de emisión). https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html — valores
  verificados directamente del PDF oficial del capítulo.
- `docs/postfuego_las_condes.md` y `sarwatch/ml/debris_flow.py` — patrón de factores multiplicativos
  acotados y honestidad obligatoria ya vigente en el proyecto.
