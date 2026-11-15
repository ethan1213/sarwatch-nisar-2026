"""Download public recent VIIRS detections and filter to the Chilean study windows."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.firms import parse_csv
from scripts.audit_chile_nisar import AOIS

SOURCES = {
    'VIIRS NOAA-20': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_America_7d.csv',
    'VIIRS NOAA-21': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_South_America_7d.csv',
    'VIIRS Suomi-NPP': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_7d.csv',
}


def main():
    result = {'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'mode': 'public_recent_7d_NRT',
              'source_documentation': 'https://firms.modaps.eosdis.nasa.gov/content/active_fire/',
              'historical_status': 'Requiere archivo histórico autenticado; no se extrapolan focos recientes a fechas pasadas.',
              'limitations': ['Detecciones de calor, no incendios confirmados, frentes ni perímetros.',
                  'Un píxel VIIRS representa aproximadamente 375 m; no es una posición exacta del fuego.',
                  'Ausencia de detecciones no demuestra ausencia de incendio; influyen nubes y pasadas.',
                  'NRT puede cambiar al publicarse procesamiento científico estándar.',
                  'FRP en MW es potencia radiativa; no se convierte directamente a CO₂.'], 'sources': [],
              'aois': {slug: {'label': spec['label'], 'bbox': spec['bbox'], 'type': 'FeatureCollection', 'features': []} for slug, spec in AOIS.items()}}
    folder = Path('data_raw/firms')
    folder.mkdir(parents=True, exist_ok=True)
    for sensor, url in SOURCES.items():
        with urlopen(url, timeout=120) as response:
            payload = response.read()
        text = payload.decode('utf-8-sig')
        stamp = {'sensor': sensor, 'url': url, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
        result['sources'].append(stamp)
        (folder / url.rsplit('/', 1)[-1]).write_bytes(payload)
        for slug, spec in AOIS.items():
            result['aois'][slug]['features'].extend(parse_csv(text, sensor, spec['bbox']))
    for slug, aoi in result['aois'].items():
        dates = sorted(f['properties']['utc'] for f in aoi['features'])
        aoi['detections'] = len(dates)
        aoi['period_observed_utc'] = [dates[0], dates[-1]] if dates else None
        aoi['nominal_or_high_confidence'] = sum(f['properties']['confidence'] in ('n', 'h') for f in aoi['features'])
        print(slug, 'detecciones', len(dates), 'periodo observado', aoi['period_observed_utc'], flush=True)
    Path('catalog/firms_reference.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
