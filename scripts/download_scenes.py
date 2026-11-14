"""Interactive Earthdata download of candidate granules into data_raw/<name>. Credentials never persist."""
import argparse
import json
import os
import shutil
from pathlib import Path


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
    files = earthaccess.download([s["url_hdf5"] for s in pending], local_path=str(target), threads=1)
    state = "download_complete_unverified" if len(files) == len(pending) else "download_incomplete"
    status.write_text(json.dumps({"state": state, "scene_ids": [s["id"] for s in pending]}), encoding="utf-8")
    print(state, "->", target)


if __name__ == "__main__":
    main()
