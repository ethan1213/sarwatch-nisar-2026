# Meteorología complementaria

Open-Meteo es el primer proveedor: API de pronóstico y API histórica con formato similar. Uso gratuito no comercial sujeto a límites y atribución. `weather.py` está separado; consulta bajo demanda, timeout de 12 s y caché de una hora en el visor. No modifica HDF5, COG ni catálogo.

| Fuente | Uso | Estado |
|---|---|---|
| Open-Meteo Forecast | Lluvia y temperatura próximos siete días | Adaptador opcional |
| Open-Meteo Historical / ERA5 | Contexto de las fechas SAR y lluvia previa | Adaptador opcional, marcado reanálisis |
| NASA POWER | Histórico meteorológico listo para análisis | Evaluado como complemento futuro; no es un pronóstico operativo por llamarse POWER |

Histórico: desde siete días antes de la fecha SAR más temprana seleccionada hasta la más tardía. Pronóstico: horizonte actual. JSON exportado incluye coordenadas solicitadas, grilla del proveedor, unidades y momento UTC de consulta. Se conserva null; no se convierte en cero.

Condiciones consultadas el 13 noviembre 2026: API gratuita no comercial, menos de 10.000 llamadas/día, 5.000/hora y 600/minuto; CC BY 4.0 y atribución. Sin garantía de exactitud/disponibilidad. Revisar plan comercial si cambia el uso; no se contrata ningún plan.

ERA5 es reanálisis de grilla gruesa, no estación sobre cada píxel. Correlación lluvia/SAR no prueba causalidad. Pronóstico no reconstruye julio-septiembre ni predice automáticamente inundaciones.

Próximas mejoras: lluvia acumulada de 7/30 días con cobertura completa, humedad del suelo indicando profundidad/modelo y caudal con validación de cuenca. Predictor hidrológico y alertas necesitan estudio independiente.

Fuentes: https://open-meteo.com/en/docs · https://open-meteo.com/en/docs/historical-weather-api · https://open-meteo.com/en/terms · https://power.larc.nasa.gov/docs/services/api/
