"""Validate prepared AOIs before a final manifest can expose them to the viewer."""
import copy
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine


def validate_prepared(manifest, verification, root):
    result = copy.deepcopy(manifest)
    root = Path(root).resolve()
    if not str(verification.get('status', '')).startswith('integridad verificada'):
        raise ValueError('El informe no confirma integridad oficial')
    checked = {s['id']: s for s in verification['scenes']}
    if set(checked) != {s['id'] for s in result['scenes']}:
        raise ValueError('Las escenas procesadas no coinciden con las verificadas')
    grid = result['grid']
    expected = (int(grid['height']), int(grid['width']), Affine(*grid['transform'][:6]), rasterio.crs.CRS.from_epsg(grid['epsg']))
    for scene in result['scenes']:
        original = checked[scene['id']]
        if not re.fullmatch(r'[a-f0-9]{32}', original.get('md5_calculado', '')) or not re.fullmatch(r'[a-f0-9]{64}', original.get('sha256', '')):
            raise ValueError('Falta checksum verificado del original')
        for key in ('md5_calculado', 'sha256', 'tamano_bytes', 'product_identification'):
            if key in original:
                scene[key] = original[key]
        for pol in ('HH', 'HV'):
            path = (root / scene['products'][pol]).resolve()
            if not path.is_relative_to(root):
                raise ValueError('Producto fuera del AOI')
            with rasterio.open(path) as src:
                if (src.height, src.width, src.transform, src.crs) != expected or src.tags().get('unit') != 'dB':
                    raise ValueError('Grilla o unidades incompatibles')
                values = src.read(1, masked=True).filled(np.nan)
                fraction = float(np.isfinite(values).mean())
            if fraction < .5 or abs(fraction - scene['finite_positive_fraction'][pol]) > 1e-6:
                raise ValueError('Cobertura insuficiente o distinta al manifiesto')
    result['integrity'] = {'official_md5_verified': True, 'derived_grid_checked': True,
                           'verified_scene_count': len(result['scenes']), 'checked_utc': datetime.now(timezone.utc).isoformat()}
    return result
