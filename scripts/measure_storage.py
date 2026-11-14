"""Measure real on-disk size of derived COGs versus their uncompressed float32 footprint; feeds the scale calculator."""
import json
from datetime import datetime, timezone
from pathlib import Path

import rasterio


def main():
    results = {}
    total_disk = total_raw = 0
    for aoi, folder in (("pantanal", Path("data")), ("metropolitana", Path("data/metropolitana")), ("valparaiso", Path("data/valparaiso"))):
        disk = raw = 0
        n = 0
        for path in sorted(folder.glob("*_H?.tif")):
            with rasterio.open(path) as src:
                itemsize = {"float32": 4, "float64": 8, "uint8": 1, "uint16": 2, "int16": 2}[src.dtypes[0]]
                raw += src.width * src.height * src.count * itemsize
            disk += path.stat().st_size
            n += 1
        if n:
            results[aoi] = {"files": n, "disk_bytes": disk, "float32_bytes": raw, "disk_over_float32": round(disk / raw, 3)}
            total_disk += disk
            total_raw += raw
    output = {"measured_utc": datetime.now(timezone.utc).isoformat(), "method": "COG float32 dB con DEFLATE y pirámides, tamaño real en disco dividido por alto×ancho×4 bytes", "aois": results, "overall_disk_over_float32": round(total_disk / total_raw, 3) if total_raw else None, "note": "Los dB en float32 comprimen mal; las pirámides añaden ~1/3. Cuantizar a int16 (0,01 dB) reduciría a la mitad; no se ha aplicado."}
    Path("catalog/storage_measurement.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
