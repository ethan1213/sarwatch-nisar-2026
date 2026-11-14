"""Interactive Earthdata download of specific NISAR L2 GUNW interferogram pairs. Credentials never persist.

Reads a candidates JSON with a top-level list under --key (default 'pares_bracket_8oct') of entries with
id/granulo/url_hdf5/estimated_mib, same shape scripts/download_scenes.py already uses for GCOV.
"""
import argparse
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="catalog/las_condes_gunw_candidates.json")
    parser.add_argument("--key", default="pares_bracket_8oct")
    parser.add_argument("--target", default="D:/NISAR/raw/gunw_las_condes")
    parser.add_argument("--ids", nargs="*", help="Subconjunto de IDs CMR; por defecto todos los del bloque --key")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / args.candidates).read_text(encoding="utf-8"))
    scenes = data[args.key]
    if args.ids:
        scenes = [s for s in scenes if s["id"] in args.ids]
    if not scenes:
        raise SystemExit("No hay escenas seleccionadas")
    if any(not s["url_hdf5"] for s in scenes):
        raise SystemExit("CMR no entrega URL HTTPS HDF5 para alguna escena")
    target = Path(args.target) if Path(args.target).is_absolute() else root / args.target
    target.mkdir(parents=True, exist_ok=True)
    pending = [s for s in scenes if not (target / (s["granulo"] + ".h5")).is_file()]
    if not pending:
        print("Todos los pares GUNW ya estan descargados en", target)
        return
    estimated = sum(s["estimated_mib"] for s in pending) * 1024 * 1024
    if shutil.disk_usage(target).free < estimated * 1.3:
        raise SystemExit(f"Espacio insuficiente: se requieren ~{estimated/1e9:.1f} GB mas margen")
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
