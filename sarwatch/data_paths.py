"""Local snapshots plus read-only Cloud Storage mount for newly published sites."""
import os
from pathlib import Path

SITES = {'pantanal', 'metropolitana', 'valparaiso', 'concepcion_penco', 'biobio'}


def site_data_root(slug):
    if slug not in SITES:
        raise ValueError('Sitio desconocido')
    base = Path(os.environ.get('DATA_DIR', 'data'))
    remote = os.environ.get('REMOTE_DATA_DIR')
    if slug == 'concepcion_penco' and remote:
        return Path(remote) / slug
    return base if slug == 'pantanal' else base / slug


def verified_manifest(manifest):
    if not manifest or not manifest.get('scenes'):
        return False
    integrity = manifest.get('integrity', {})
    return (integrity.get('official_md5_verified') is True and integrity.get('derived_grid_checked') is True
            and integrity.get('verified_scene_count') == len(manifest['scenes'])
            and all(len(s.get('sha256', '')) == 64 and len(s.get('md5_calculado', '')) == 32 for s in manifest['scenes']))
