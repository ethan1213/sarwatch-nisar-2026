"""Audit real Chilean GCOV availability across BETA/PROVISIONAL/VALIDATED collections.

All granules are paginated; version/cohort groups remain separate. Footprint intersection is
catalog availability, not guaranteed usable pixels. No authentication or raster download needed.
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

COLLECTIONS = {'BETA': 'NISAR_L2_GCOV_BETA_V1', 'PROVISIONAL': 'NISAR_L2_GCOV_PROVISIONAL_V1', 'VALIDATED': 'NISAR_L2_GCOV_V1'}
AOIS = {
    'concepcion_penco': {'label': 'Concepción, Penco y entorno urbano', 'bbox': [-73.25, -36.95, -72.70, -36.50]},
    'biobio': {'label': 'Biobío · ventana regional de búsqueda (no límite administrativo)', 'bbox': [-74.00, -38.65, -70.85, -36.00]},
}


def search(short_name, bbox, start, end):
    entries, queries, expected = [], [], None
    page = 1
    while True:
        url = 'https://cmr.earthdata.nasa.gov/search/granules.json?' + urlencode({
            'short_name': short_name, 'bounding_box': ','.join(map(str, bbox)),
            'temporal': f'{start}T00:00:00Z,{end}T23:59:59Z',
            'page_size': 200, 'page_num': page, 'sort_key': 'start_date'})
        with urlopen(url, timeout=90) as response:
            expected = int(response.headers.get('CMR-Hits', 0))
            rows = json.load(response)['feed']['entry']
        queries.append(url)
        entries.extend(rows)
        if len(rows) < 200:
            break
        page += 1
    if len(entries) != expected:
        raise ValueError(f'Catálogo cambió durante consulta: {len(entries)} filas frente a {expected} declaradas; repetir auditoría')
    return entries, queries


def describe(entry, maturity, collection):
    name = entry['producer_granule_id']
    parts = name.split('_')
    crid = next((p for p in parts if re.fullmatch(r'[PX]\d{5}', p)), 'unknown')
    return {'id': entry['id'], 'granulo': name, 'fecha_observacion': entry['time_start'],
            'maturity': maturity, 'collection': collection, 'collection_version': '1',
            'crid': crid, 'product_revision': parts[-1], 'geometry': '_'.join(parts[5:11]),
            'estimated_mib': float(entry.get('granule_size', 0)),
            'url_metadatos': f"https://cmr.earthdata.nasa.gov/search/concepts/{entry['id']}.umm_json",
            'url_hdf5': next((link['href'] for link in entry.get('links', []) if link.get('href', '').startswith('https://') and link['href'].endswith('.h5')), None)}


def audit(end):
    result = {'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'requested_period': ['2025-07-30', end],
              'mission_source': 'https://nisar-docs.asf.alaska.edu/availability-overview/',
              'status': 'catalog_audit_not_raster_validation', 'aois': {},
              'limitations': ['Intersección de huellas no garantiza cobertura útil del recorte.',
                             'BETA, PROVISIONAL y VALIDATED no se mezclan automáticamente como una serie radiométrica.',
                             'CRID, revisión de archivo y versión de colección son conceptos distintos.',
                             'Ausencia en el catálogo consultado no demuestra ausencia de adquisición de la misión.']}
    for slug, spec in AOIS.items():
        all_scenes, queries = [], []
        for maturity, collection in COLLECTIONS.items():
            entries, urls = search(collection, spec['bbox'], '2025-07-30', end)
            all_scenes.extend(describe(e, maturity, collection) for e in entries)
            queries.extend(urls)
            print(f'{slug} {maturity}: {len(entries)} granulos', flush=True)
        groups = defaultdict(list)
        for scene in all_scenes:
            groups[(scene['maturity'], scene['crid'], scene['geometry'])].append(scene)
        cohorts = []
        for (maturity, crid, geometry), scenes in groups.items():
            latest = {}
            for scene in scenes:
                when = scene['fecha_observacion']
                if when not in latest or scene['product_revision'] > latest[when]['product_revision']:
                    latest[when] = scene
            selected = sorted(latest.values(), key=lambda s: s['fecha_observacion'])
            cohorts.append({'maturity': maturity, 'crid': crid, 'geometry': geometry, 'n_dates': len(selected),
                            'first_date': selected[0]['fecha_observacion'], 'last_date': selected[-1]['fecha_observacion'],
                            'download_gib': sum(s['estimated_mib'] for s in selected) / 1024, 'scenes': selected})
        cohorts.sort(key=lambda g: (g['maturity'] != 'VALIDATED', -g['n_dates'], g['geometry']))
        result['aois'][slug] = {**spec, 'queries': queries, 'n_granules': len(all_scenes), 'cohorts': cohorts}
    Path('catalog/chile_nisar_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--end', default='2026-11-14')
    audit(parser.parse_args().end)
