"""Publish immutable COG revisions; replace the viewer manifest only after uploads succeed."""
import argparse
import copy
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.publication import validate_prepared


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--aoi', default='concepcion_penco', choices=['concepcion_penco'])
    parser.add_argument('--bucket', default='sarwatch-525550511866-data')
    parser.add_argument('--project', default='project-6fff6574-07af-4183-b83')
    parser.add_argument('--gcloud', required=True)
    parser.add_argument('--wait', action='store_true')
    parser.add_argument('--wait-hours', type=float, default=8)
    args = parser.parse_args()
    root = Path('data') / args.aoi
    report_path = Path('catalog') / f'{args.aoi}_verified.json'
    deadline = time.monotonic() + args.wait_hours * 3600
    while args.wait and not ((root / 'manifest.json').is_file() and report_path.is_file()):
        if time.monotonic() >= deadline:
            raise TimeoutError('La preparación no terminó dentro del plazo; no se publicó ningún manifiesto')
        time.sleep(20)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    report = json.loads(report_path.read_text(encoding='utf-8'))
    manifest = validate_prepared(manifest, report, root)
    (root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    revision = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prefix = f'gs://{args.bucket}/derived/{args.aoi}'
    gcloud_path = Path(args.gcloud).resolve()
    gcloud_py = gcloud_path.parent.parent / 'lib/gcloud.py'
    command = [sys.executable, str(gcloud_py)] if gcloud_py.is_file() else [str(gcloud_path)]
    def run(*parts):
        subprocess.run([*command, *parts, f'--project={args.project}', '--quiet'], check=True)
    run('storage', 'rsync', str(root), f'{prefix}/revisions/{revision}', '--recursive',
        r'--exclude=(^|/)(labels|covariates|wildfire|thermal|postfire)(/|$)|(^|/)manifest\.json$')
    published = copy.deepcopy(manifest)
    for scene in published['scenes']:
        for key in ('products', 'ancillary'):
            scene[key] = {name: f'revisions/{revision}/{path}' for name, path in scene.get(key, {}).items()}
    destination = Path('work/publication') / args.aoi / 'manifest.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(published, ensure_ascii=False, indent=2), encoding='utf-8')
    run('storage', 'cp', str(destination), f'{prefix}/manifest.json')
    receipt = {'aoi': args.aoi, 'revision': revision, 'manifest_uri': f'{prefix}/manifest.json',
               'source_integrity_verified': True, 'published_utc': datetime.now(timezone.utc).isoformat()}
    Path(f'catalog/{args.aoi}_publication.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
