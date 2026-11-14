"""Verify downloaded GCOV HDF5 files against official CMR metadata (size + MD5) and record SHA-256 and grid.

Generic version of verify_chile_downloads.py: takes a candidates/scenes JSON and a raw directory.
Fetches UMM-JSON metadata from CMR when it is not cached under catalog/.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import h5py


def official_metadata(scene, root):
    cache = root / "catalog" / f"{scene['id']}.umm.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    with urlopen(scene["url_metadatos"], timeout=60) as response:
        body = response.read().decode("utf-8")
    cache.write_text(body, encoding="utf-8")
    return json.loads(body)


def verify_scene(scene, raw, root):
    metadata = official_metadata(scene, root)
    name = scene["granulo"] + ".h5"
    official = next(x for x in metadata["DataGranule"]["ArchiveAndDistributionInformation"] if x["Name"] == name)
    path = raw / name
    if not path.is_file() or path.stat().st_size != official["SizeInBytes"]:
        raise ValueError(f"{scene['id']}: archivo ausente o tamaño incompleto")
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            md5.update(chunk)
            sha.update(chunk)
    if official["Checksum"]["Algorithm"] != "MD5" or md5.hexdigest() != official["Checksum"]["Value"].lower().zfill(32):
        raise ValueError(f"{scene['id']}: checksum no coincide")
    with h5py.File(path) as source:
        g = source["/science/LSAR/GCOV/grids/frequencyA"]
        grid = {"epsg": int(g["projection"][()]), "shape": list(g["HHHH"].shape), "bounds_centers": [float(g["xCoordinates"][0]), float(g["yCoordinates"][-1]), float(g["xCoordinates"][-1]), float(g["yCoordinates"][0])]}
    return {**scene, "tamano_bytes": path.stat().st_size, "md5_calculado": md5.hexdigest(), "sha256": sha.hexdigest(), "grid": grid}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", required=True, help="JSON con lista bajo 'candidates' o 'scenes'")
    parser.add_argument("--raw", required=True, help="Directorio con los .h5")
    parser.add_argument("--output", required=True, help="JSON de salida con la verificación")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = json.loads(Path(args.scenes).read_text(encoding="utf-8"))
    scenes = data.get("candidates") or data.get("scenes")
    report = []
    for scene in scenes:
        report.append(verify_scene(scene, Path(args.raw), root))
        print(scene["id"], "MD5 oficial verificado", flush=True)
    Path(args.output).write_text(json.dumps({"scenes": report, "raw_dir": str(args.raw), "status": "integridad verificada; cobertura y calidad espacial pendientes"}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
