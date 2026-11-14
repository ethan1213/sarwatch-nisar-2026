"""Refresh public continental cartography and a bounded CMR candidate page."""
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen


def refresh():
    output=Path(__file__).resolve().parents[1]/'catalog'
    for slug,layer in [('valparaiso',8),('metropolitana',9)]:
        url=f'https://esri.ciren.cl/server/rest/services/Hosted/LIMITES_ADMINISTRATIVOS_1/FeatureServer/{layer}/query?'+urlencode({'where':'1=1','outFields':'*','outSR':'4326','f':'geojson','maxAllowableOffset':'0.001'})
        with urlopen(url,timeout=60) as response:
            result=json.load(response)
        if not result.get('features') or result.get('exceededTransferLimit'):
            raise ValueError('Respuesta cartográfica vacía o truncada')
        (output/(slug+'.geojson')).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    end=datetime.now(timezone.utc).date().isoformat()
    url='https://cmr.earthdata.nasa.gov/search/granules.json?'+urlencode({'short_name':'NISAR_L2_GCOV_PROVISIONAL_V1','bounding_box':'-72,-34.3,-69.7,-32','temporal':f'2026-01-01T00:00:00Z,{end}T23:59:59Z','page_size':30,'sort_key':'-start_date'})
    with urlopen(url,timeout=60) as response:
        result=json.load(response)
    if 'feed' not in result:
        raise ValueError('Respuesta CMR no reconocida')
    (output/'chile_cmr.json').write_text(json.dumps({'query':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'response':result},indent=2),encoding='utf-8')


if __name__=='__main__':
    refresh()
