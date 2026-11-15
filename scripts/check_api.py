"""HTTP acceptance checks against the actual local container or deployed Cloud Run service."""
import argparse
import json
import re
import gzip
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def check(base):
    results = []
    with urlopen(base.rstrip('/') + '/', timeout=180) as response:
        html = response.read().decode()
        assert response.status == 200 and '<div id="root">' in html
    results.append({'path': '/', 'status': 200})
    bundle_path = re.search(r'src="([^"]+\.js)"', html).group(1)
    with urlopen(base.rstrip('/') + bundle_path, timeout=180) as response:
        bundle = response.read().decode()
    worker_path = re.search(r'/assets/maplibre-gl-worker-[A-Za-z0-9_-]+\.js', bundle).group(0)
    with urlopen(base.rstrip('/') + worker_path, timeout=180) as response:
        assert response.status == 200 and len(response.read()) > 1000
    results.append({'path': worker_path, 'status': 200})

    def get(path, body=None, expected=200):
        request = Request(base.rstrip('/') + path, data=json.dumps(body).encode() if body else None,
                          headers={'Content-Type': 'application/json'} if body else {})
        try:
            with urlopen(request, timeout=180) as response:
                assert response.status == expected, path
                result = json.load(response)
        except HTTPError as exc:
            assert exc.code == expected, (path, exc.code, exc.read().decode()[:500])
            result = None
        results.append({'path': path, 'status': expected})
        return result

    assert get('/api/health')['status'] == 'ok'
    for slug in ('pantanal', 'metropolitana', 'valparaiso'):
        manifest = get(f'/api/{slug}/manifest')
        last = len(manifest['scenes']) - 1
        layer = get(f'/api/{slug}/layer?before=0&after={last}&pol=HV&mode=diff')
        assert layer['context']['region'] == manifest['region']
        assert layer['png_data_url'].startswith('data:image/png;base64,')
        get(f'/api/{slug}/layer?before=0&after={last}&pol=invalid', expected=400)
        west, south, east, north = manifest['bbox_wgs84']
        series = get(f'/api/{slug}/point-series?lon={(west+east)/2}&lat={(south+north)/2}&pol=HH')
        assert len(series['rows']) == len(manifest['scenes'])
        thermal = get(f'/api/study/{slug}/thermal')
        assert thermal['cells_available'] and thermal['radar_dates']
        for kind in ('bt_tir', 'hv_last', 'pendiente_grados'):
            cells = get(f'/api/study/{slug}/thermal-cells?layer={kind}')
            assert cells['features']
        if slug != 'pantanal':
            get(f'/api/{slug}/prediction-reference', expected=404)
    get('/api/study/metropolitana/overlay?kind=postfire')
    get('/api/study/metropolitana/overlay?kind=concentration')
    get('/api/study/metropolitana/overlay?kind=change')
    impacts = get('/api/study/metropolitana/impacts')
    assert impacts['terrain']['volume']['volume_m3'] is None
    get('/api/study/valparaiso/impacts', expected=404)
    reply = get('/api/metropolitana/assistant', {'question': '¿Cuánto CO2 emitió?', 'before': 0, 'after': 1})
    assert reply['verified'] and reply['intent'] == 'impactos_incendio'
    world = get('/api/world/meta')
    assert world['n_cells'] > 0
    request = Request(base.rstrip('/') + '/api/world/cells', headers={'Accept-Encoding':'gzip'})
    with urlopen(request, timeout=180) as response:
        assert response.headers.get('Content-Encoding') == 'gzip', 'World data must be compressed for bandwidth and cost'
        coverage = json.loads(gzip.decompress(response.read()))
    assert len(coverage['features']) == world['n_cells']
    results.append({'path':'/api/world/cells (gzip)','status':200})
    for slug in ('concepcion_penco', 'biobio'):
        overview = get(f'/api/chile/{slug}/overview')
        assert overview['audit']['cohorts'] and overview['firms']['type'] == 'FeatureCollection'
        assert all(f['properties']['confidence'] in ('l','n','h') for f in overview['firms']['features'])
        assert isinstance(overview['rasters_ready'], bool)
    print(json.dumps({'tested_utc': datetime.now(timezone.utc).isoformat(), 'base': base, 'passed': len(results), 'checks': results}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('base', nargs='?', default='http://127.0.0.1:8090')
    check(parser.parse_args().base)
