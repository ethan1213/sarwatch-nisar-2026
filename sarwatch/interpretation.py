"""Evidence-bound descriptions. These statistics are not a hazard classifier."""
import unicodedata
import numpy as np

PROFILES=['Público general','Ciencia','Desarrollo y datos','Comunicaciones','Gestión territorial']
GUIDES={
 'Público general':'Empieza por el resumen, mira dónde cambia el color y selecciona un punto. El radar mide una respuesta de la superficie, no una fotografía ni un diagnóstico.',
 'Ciencia':'Revisa máscara común, unidades, geometría y distribución del cambio. Contrasta hipótesis con evidencia independiente; calidad técnica no equivale a precisión temática.',
 'Desarrollo y datos':'Los COG conservan grilla y procedencia. Las estadísticas se calculan en el servidor; el mapa reduce resolución solo para mostrar. Consulta el CSV antes de integrar resultados.',
 'Comunicaciones':'Cuenta qué lugar y fechas se comparan, qué midió el instrumento y qué no se puede concluir. No uses «inundación detectada» sin validación independiente.',
 'Gestión territorial':'Usa estas observaciones para orientar una revisión del territorio. No constituyen alerta ni delimitación de daños; contrasta con información local y responsables del área.'}


def summarize(before,after):
    if before.shape!=after.shape:
        raise ValueError('Grillas incompatibles')
    valid=np.isfinite(before)&np.isfinite(after)
    delta=after[valid]-before[valid]
    result={'coverage':float(valid.mean()),'pixels':int(valid.sum()),'median_db':None,'q25_db':None,'q75_db':None}
    if delta.size:
        result.update(zip(['q25_db','median_db','q75_db'],map(float,np.percentile(delta,[25,50,75]))))
    return result


def describe(context):
    stats=context['statistics']
    intro=f"Comparamos {context['region']} entre {context['before']} y {context['after']}, con el canal {context['polarization']}."
    if stats['median_db'] is None:
        return intro+' No hay píxeles válidos comunes; no podemos describir el cambio de este par.'
    median=stats['median_db']
    movement='aumentó' if median>0 else 'disminuyó' if median<0 else 'se mantuvo'
    return intro+f" La respuesta típica del radar {movement}: diferencia mediana {median:+.2f} dB. Se puede comparar el {stats['coverage']:.1%} del recorte. Esto describe la señal; no identifica por sí solo la causa del cambio."


def answer(question,context):
    q=''.join(c for c in unicodedata.normalize('NFKD',question.lower()) if not unicodedata.combining(c))
    if any(word in q for word in ['predec','predic','futuro','manana','alerta','riesgo','seguro']):
        return 'Todavía no podemos predecir inundaciones, daños o cambios futuros con este conjunto. En Chile hay dos fechas. El pronóstico meteorológico estima el tiempo, no el comportamiento futuro de cada píxel SAR. Primero necesitamos una serie más larga, etiquetas independientes y evaluación temporal y geográfica fuera del entrenamiento. No hay un modelo de riesgo validado.', 'https://open-meteo.com/en/docs/flood-api'
    if any(word in q for word in ['inund','agua','incend','terrem','causa','por que']):
        return 'El cambio de radar puede relacionarse con humedad, vegetación, geometría, construcciones u otros procesos. Estos datos no permiten confirmar por sí solos inundación, incendio o daño. Necesitamos comparar con observaciones independientes de esas fechas y revisar la coherencia espacial.', 'https://nisar-docs.asf.alaska.edu/using-overview/'
    if any(word in q for word in ['color','rojo','azul','mapa']):
        return 'En diferencia, azul indica menor respuesta del radar y naranja mayor respuesta en la fecha final; el tono claro queda cerca de cero. En una fecha individual, el color representa intensidad. Transparente significa sin dato válido, no ausencia de cambio. Los colores no representan peligro ni agua confirmada.', 'https://nisar-docs.asf.alaska.edu/using-overview/'
    if any(word in q for word in ['db','polar','hh','hv','radar']):
        return 'dB es una escala logarítmica para expresar la respuesta del radar. HH y HV son dos formas de enviar y recibir la señal: no son tipos de desastre. Aquí convertimos potencia positiva con 10·log10 y comparamos el mismo canal entre fechas; no mezclamos HH con HV.', 'https://nisar-docs.asf.alaska.edu/using-overview/'
    if any(word in q for word in ['calidad','confian','precision','valido','99','100']):
        return 'Cobertura comparable significa proporción del recorte con datos técnicos válidos en ambas fechas. Un 99,9 % de cobertura NO significa 99,9 % de precisión, probabilidad de inundación ni certeza científica. Las máscaras filtran muestras inválidas; falta validar la interpretación ambiental.', 'https://nisar-docs.asf.alaska.edu/using-overview/'
    if any(word in q for word in ['fuente','origen','fecha','resum','cambio','entiend','observ','explica']):
        return describe(context)+' Procedencia: los identificadores oficiales de las escenas están en el panel de calidad.', context['source']
    return 'Puedo explicar este par de observaciones, sus colores, HH/HV, calidad y límites de predicción. No tengo evidencia para responder esa pregunta fuera de esos temas. Prueba «Resume el cambio» o «¿Qué significan los colores?».',context['source']


def storage_bytes(area_km2,resolution_m,layers,dates,overviews=True):
    if min(area_km2,resolution_m,layers,dates)<=0:
        raise ValueError('Los parámetros deben ser positivos')
    return area_km2*1_000_000/resolution_m**2*layers*dates*4*(4/3 if overviews else 1)
