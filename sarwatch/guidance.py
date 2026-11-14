"""Plain-language reading, audience guidance and an explicitly bounded chat."""
import streamlit as st
import json
from pathlib import Path
from sarwatch.interpretation import GUIDES,describe,answer,storage_bytes


def reading(context,profile):
    st.subheader('Qué nos muestran estas observaciones')
    st.write(describe(context))
    st.caption('La cobertura indica disponibilidad de datos, no precisión de una predicción. El recorte no representa toda la región.')
    st.caption('Una mediana cercana a cero puede ocultar cambios localizados. Revisa el mapa y los puntos antes de sacar conclusiones.')
    with st.expander('Cómo leer esta vista',expanded=profile=='Público general'):
        st.write(GUIDES[profile])
        st.markdown('1. Revisa lugar y fechas.\n2. Compara la señal en el mapa.\n3. Haz clic dentro de la capa para consultar valores.\n4. Revisa las fuentes antes de atribuir una causa.')
    if profile=='Comunicaciones':
        st.text_area('Borrador informativo verificable',describe(context)+' No se ha confirmado un evento ambiental con estas observaciones.',height=120,key='brief-'+context['region'])
    if profile=='Ciencia':
        s=context['statistics']
        st.write(f"Píxeles comparables: {s['pixels']:,}. Cuartiles del cambio: {s['q25_db']} y {s['q75_db']} dB. Estadísticas descriptivas, sin prueba de significación ni clasificación.")


def assistant(context,profile):
    with st.expander('Qué podemos predecir hoy'):
        st.write('Todavía no hay un modelo validado para anticipar inundaciones o daños. El cambio de señal describe el pasado; el tiempo meteorológico es un pronóstico de otro proveedor.')
        reference=Path('catalog/prediction_reference.json')
        if reference.is_file():
            benchmark=json.loads(reference.read_text(encoding='utf-8'))
            st.write(f"Referencia retrospectiva en Pantanal: repetir la mediana HH anterior produjo {benchmark['n_evaluations']} evaluaciones a unos 12 días, con MAE {benchmark['mae_db']:.2f} dB. No es un porcentaje de exactitud ni un predictor de inundación; no se generaliza a Chile.")
            st.download_button('Descargar evaluación y límites',json.dumps(benchmark,ensure_ascii=False,indent=2),'persistence-reference.json','application/json')
    with st.expander('Pregúntale al asistente sobre estos datos'):
        st.caption('Asistente guiado local, basado en reglas y fuentes. No es un modelo generativo ni un predictor. No envía preguntas a servicios externos.')
        st.write('Puedes preguntar: «Resume el cambio», «¿Qué significan los colores?», «¿Es una inundación?» o «¿Se puede predecir?».')
        key='conversation-'+context['region']
        # Clear answers when evidence changes, so older replies are not attributed to a new pair.
        fingerprint=(context['before'],context['after'],context['polarization'],profile)
        if st.session_state.get(key+'-context')!=fingerprint:
            st.session_state[key]=[]
            st.session_state[key+'-context']=fingerprint
        question=st.chat_input('Pregunta sobre estas observaciones',key=key+'-input',max_chars=1000)
        if question:
            response,source=answer(question,context)
            st.session_state[key]=(st.session_state[key]+[(question,response,source)])[-6:]
        for question,response,source in st.session_state.get(key,[]):
            with st.chat_message('user'):
                st.write(question)
            with st.chat_message('assistant'):
                st.write(response)
                st.markdown(f'[Fuente de apoyo]({source})')


def scale_calculator():
    with st.expander('¿Cuánto ocuparía ampliar el estudio?'):
        st.caption('Estimación geométrica de capas float32 sin compresión; no es el tamaño total de la misión ni un presupuesto de nube. Incluye 4/3 para pirámides aproximadas.')
        area=st.number_input('Superficie a analizar (km²)',min_value=1.,value=10000.,key='scale-area')
        resolution=st.selectbox('Tamaño del píxel (m)',[20,80,100,200],key='scale-resolution')
        dates=st.number_input('Número de fechas',min_value=1,max_value=1000,value=30,key='scale-dates')
        size=storage_bytes(area,resolution,2,dates)
        st.metric('Dos canales · tamaño estimado',f'{size/1e9:,.2f} GB' if size<1e12 else f'{size/1e12:,.2f} TB')
        st.write('El navegador solo debe recibir teselas de la zona visible. Para cobertura mundial: catálogo global, procesamiento por zona solicitada, caché con vencimiento y productos regionales. No descargar todo el archivo a esta computadora.')
