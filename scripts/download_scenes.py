"""Interactive Earthdata download of candidate granules into data_raw/<name>. Credentials never persist."""
import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.acquisition import download_verified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="catalog/pantanal_candidates.json")
    parser.add_argument("--target", default=os.path.join(os.environ.get("SARWATCH_RAW", "D:/NISAR/raw"), "pantanal"), help="Por defecto SARWATCH_RAW/pantanal (disco externo D:/NISAR/raw)")
    parser.add_argument("--ids", nargs="*", help="Subconjunto de IDs CMR; por defecto todos")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    scenes = json.loads((root / args.candidates).read_text(encoding="utf-8"))["candidates"]
    if args.ids:
        scenes = [s for s in scenes if s["id"] in args.ids]
    if not scenes:
        raise SystemExit("No hay escenas candidatas")
    if any(not s["url_hdf5"] for s in scenes):
        raise SystemExit("CMR no entrega URL HTTPS HDF5 para alguna escena")
    target = Path(args.target) if Path(args.target).is_absolute() else root / args.target
    target.mkdir(parents=True, exist_ok=True)
    pending = [s for s in scenes if not (target / (s["granulo"] + ".h5")).is_file()]
    estimated = sum(s["estimated_mib"] for s in pending) * 1024 * 1024
    if shutil.disk_usage(target).free < estimated * 1.3:
        raise SystemExit(f"Espacio insuficiente: se requieren ~{estimated/1e9:.1f} GB mas margen")
    if not pending:
        print("Todas las escenas ya estan descargadas; ejecutar verificacion")
        return
    import earthaccess
    status = target / "download_status.json"
    status.write_text(json.dumps({"state": "awaiting_local_login", "scene_ids": [s["id"] for s in pending]}), encoding="utf-8")
    print("Earthdata Login: introduce tus credenciales solo en esta terminal. No se guardaran.", flush=True)
    auth = earthaccess.login(strategy="interactive", persist=False)
    if not auth.authenticated:
        status.write_text(json.dumps({"state": "authentication_failed"}), encoding="utf-8")
        raise SystemExit("Earthdata no autenticado")
    status.write_text(json.dumps({"state": "downloading", "scene_ids": [s["id"] for s in pending]}), encoding="utf-8")
    files = []
    session = auth.get_session()
    try:
        for scene in pending:
            with urlopen(scene['url_metadatos'], timeout=60) as response:
                metadata = json.load(response)
            name = scene['granulo'] + '.h5'
            official = next(item for item in metadata['DataGranule']['ArchiveAndDistributionInformation'] if item['Name'] == name)
            if official['Checksum']['Algorithm'] != 'MD5':
                raise ValueError('Algoritmo de checksum oficial no soportado')
            last_report = [0.]
            def report(downloaded, total):
                now = time.monotonic()
                if now - last_report[0] < 5 and downloaded != total:
                    return
                last_report[0] = now
                status.write_text(json.dumps({'state': 'downloading', 'scene_id': scene['id'],
                    'completed_files': len(files), 'total_files': len(pending), 'bytes_downloaded': downloaded,
                    'bytes_expected': total, 'updated_utc': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')
                print(f"{scene['id']}: {downloaded/1e6:.1f}/{total/1e6:.1f} MB · parcial conservado", flush=True)
            files.append(download_verified(session, scene['url_hdf5'], target / name,
                int(official['SizeInBytes']), official['Checksum']['Value'].lower().zfill(32), progress=report))
    except Exception as exc:
        status.write_text(json.dumps({'state': 'download_failed_resumable', 'error_type': type(exc).__name__,
            'completed_files': len(files), 'updated_utc': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')
        print('Descarga interrumpida. Los parciales se conservan. Tipo:', type(exc).__name__, flush=True)
        raise SystemExit(1)
    state = "download_complete_unverified" if len(files) == len(pending) else "download_incomplete"
    status.write_text(json.dumps({"state": state, "scene_ids": [s["id"] for s in pending]}), encoding="utf-8")
    print(state, "->", target)


if __name__ == "__main__":
    main()
