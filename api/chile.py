"""Real catalog and FIRMS context for Chile, with explicit availability states."""
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

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
    manifest = read_optional(DATA / slug / 'manifest.json')
    verified = read_optional(f'catalog/{slug}_verified.json')
    area = (audit or {}).get('aois', {}).get(slug)
    return {'slug': slug, 'audit': area, 'retrieved_utc': (audit or {}).get('retrieved_utc'),
            'rasters_ready': bool(manifest and verified), 'manifest': manifest if verified else None,
            'firms': (firms or {}).get('aois', {}).get(slug),
            'firms_sources': (firms or {}).get('sources', []),
            'firms_retrieved_utc': (firms or {}).get('retrieved_utc'),
            'historical_status': (firms or {}).get('historical_status'),
            'limitations': (audit or {}).get('limitations', []) + (firms or {}).get('limitations', [])}
