"""Real catalog and FIRMS context for Chile, with explicit availability states."""
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sarwatch.data_paths import site_data_root, verified_manifest
from sarwatch.repository import RasterRepository

router = APIRouter(prefix='/api/chile', tags=['chile'])
DATA = Path(os.environ.get('DATA_DIR', 'data'))


def read_optional(path):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


@router.get('/{slug}/overview')
def overview(slug: str):
    if slug not in {'concepcion_penco', 'biobio'}:
        raise HTTPException(404, 'Área desconocida')
    audit = read_optional('catalog/chile_nisar_audit.json')
    firms = read_optional('catalog/firms_reference.json')
    root = site_data_root(slug)
    manifest = read_optional(root / 'manifest.json')
    verified = read_optional(f'catalog/{slug}_verified.json')
    ready = bool(manifest and (verified_manifest(manifest) or verified))
    if ready:
        try:
            RasterRepository(root).manifest()
        except (FileNotFoundError, ValueError):
            ready = False
    area = (audit or {}).get('aois', {}).get(slug)
    return {'slug': slug, 'audit': area, 'retrieved_utc': (audit or {}).get('retrieved_utc'),
            'rasters_ready': ready, 'manifest': manifest if ready else None,
            'firms': (firms or {}).get('aois', {}).get(slug),
            'firms_sources': (firms or {}).get('sources', []),
            'firms_retrieved_utc': (firms or {}).get('retrieved_utc'),
            'historical_status': (firms or {}).get('historical_status'),
            'limitations': (audit or {}).get('limitations', []) + (firms or {}).get('limitations', [])}
