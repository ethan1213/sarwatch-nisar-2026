"""Thermal observations over an AOI from GOES-19 ABI (public NOAA bucket, no credentials).

Per time step: fire/hot-spot characterisation (ABI-L2-FDCF: mask, fire radiative power, temperature, area),
brightness temperature at 3.9 um (band 7, mid-infrared) and 11.2 um (band 14, thermal infrared) from
ABI-L2-CMIPF, and hourly land surface temperature (ABI-L2-LST2KMF). Only the AOI window is read, with
HTTP range requests. Writes <data>/<aoi>/thermal/{cube.npz,hotspots.json,manifest.json}.

    python scripts/fetch_thermal.py --aoi pantanal valparaiso --start 2026-07-01 --end 2026-10-25 --step-minutes 60
"""
import argparse
import io
import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.grids import load_manifest
from sarwatch.ml.thermal import CLOUD_CODES, FIRE_CLASSES, aoi_window, decode, fire_class, footprint_km, window_geometry

BUCKET = "https://noaa-goes19.s3.amazonaws.com/"
PRODUCTS = {"fdc": ("ABI-L2-FDCF", ""), "mir": ("ABI-L2-CMIPF", "C07"), "tir": ("ABI-L2-CMIPF", "C14"), "lst": ("ABI-L2-LST2KMF", "")}
START = re.compile(r"_s(\d{11})\d+_e")


class RangeFile(io.RawIOBase):
    """Read-only seekable view of an HTTP object that fetches fixed blocks on demand."""

    def __init__(self, url, session, block=1 << 18):
        super().__init__()
        self.url, self.session, self.block, self.position, self.blocks, self.fetched = url, session, block, 0, {}, 0
        response = session.get(url, headers={"Range": f"bytes=0-{block - 1}"}, timeout=60)
        response.raise_for_status()
        self.size = int(response.headers["Content-Range"].rsplit("/", 1)[1])
        self.blocks[0], self.fetched = response.content, len(response.content)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        return self.position

    def _block(self, index):
        if index not in self.blocks:
            first, last = index * self.block, min((index + 1) * self.block, self.size) - 1
            response = self.session.get(self.url, headers={"Range": f"bytes={first}-{last}"}, timeout=60)
            response.raise_for_status()
            self.blocks[index] = response.content
            self.fetched += len(response.content)
        return self.blocks[index]

    def readinto(self, buffer):
        wanted = min(len(buffer), self.size - self.position)
        if wanted <= 0:
            return 0
        out, position = bytearray(), self.position
        while len(out) < wanted:
            index, offset = divmod(position, self.block)
            piece = self._block(index)[offset:offset + wanted - len(out)]
            out += piece
            position += len(piece)
        buffer[:wanted] = out
        self.position += wanted
        return wanted


def list_keys(session, prefix):
    keys, token = [], None
    while True:
        params = {"list-type": "2", "prefix": prefix}
        if token:
            params["continuation-token"] = token
        response = session.get(BUCKET, params=params, timeout=60)
        response.raise_for_status()
        keys += re.findall(r"<Key>([^<]+)</Key>", response.text)
        token = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", response.text)
        if not token:
            return keys
        token = token.group(1)


def index_day(session, day):
    """{product: {YYYYDDDHHMM: key}} for one UTC day."""
    stamp = day.strftime("%Y/%j/")
    out = {name: {} for name in PRODUCTS}
    for collection in {c for c, _ in PRODUCTS.values()}:
        for key in list_keys(session, f"{collection}/{stamp}"):
            match = START.search(key)
            for name, (owner, channel) in PRODUCTS.items():
                if match and owner == collection and (not channel or f"M6{channel}_" in key or f"M3{channel}_" in key or f"M4{channel}_" in key):
                    out[name][match.group(1)] = key
    return out


def axis(dataset):
    return float(dataset.attrs["scale_factor"][0]), float(dataset.attrs["add_offset"][0]), int(dataset.shape[0])


def read_windows(session, key, variables, bboxes, state):
    """{aoi: {variable: decoded window}} from one file; the navigation must match the reference in state."""
    import h5py
    handle = RangeFile(BUCKET + key, session)
    out = {}
    with h5py.File(io.BufferedReader(handle, buffer_size=handle.block), "r") as source:
        proj = {k: float(np.asarray(v).ravel()[0]) for k, v in source["goes_imager_projection"].attrs.items() if k in ("semi_major_axis", "semi_minor_axis", "perspective_point_height", "longitude_of_projection_origin")}
        navigation = (axis(source["x"]), axis(source["y"]), tuple(sorted(proj.items())))
        if state.setdefault("navigation", navigation) != navigation:
            raise ValueError(f"Navegación distinta en {key}")
        for aoi, bbox in bboxes.items():
            row0, row1, col0, col1 = state["windows"].setdefault(aoi, aoi_window(bbox, navigation[0], navigation[1], proj))
            out[aoi] = {}
            for variable in variables:
                dataset = source[variable]
                attrs = {k: dataset.attrs[k] for k in ("_FillValue", "scale_factor", "add_offset") if k in dataset.attrs}
                if "_Unsigned" in dataset.attrs:
                    attrs["_Unsigned"] = dataset.attrs["_Unsigned"].decode() if isinstance(dataset.attrs["_Unsigned"], bytes) else dataset.attrs["_Unsigned"]
                raw = dataset[row0:row1, col0:col1]
                out[aoi][variable] = raw if variable in ("Mask", "DQF") else decode(raw, attrs)
    state["bytes"] = state.get("bytes", 0) + handle.fetched
    return out


_SESSION = None


def read_step(job):
    """All products of one time step for every AOI. Runs in a worker process (h5py holds a global lock per process).

    job = (stamp, {product: key}, bboxes, state) with state = {"windows", "navigation"} (empty on the first call).
    Returns (stamp, {aoi: {layer: window}}, state) where state also carries bytes read and failures.
    """
    global _SESSION
    if _SESSION is None:
        import requests
        _SESSION = requests.Session()
    stamp, keys, bboxes, state = job
    state = {"windows": dict(state.get("windows", {})), "failures": [], "bytes": 0, **({"navigation": state["navigation"]} if "navigation" in state else {})}
    result = {aoi: {} for aoi in bboxes}
    for name, variables in (("fdc", ("Mask", "Power", "Temp", "Area")), ("mir", ("CMI", "DQF")), ("tir", ("CMI", "DQF")), ("lst", ("LST", "DQF"))):
        key = keys.get(name)
        if not key:
            continue
        windows = None
        for attempt in range(4):
            try:
                windows = read_windows(_SESSION, key, variables, bboxes, state)
                break
            except Exception as error:  # network hiccups are retried; a persistent failure is recorded
                if attempt == 3:
                    state["failures"].append({"key": key, "error": f"{type(error).__name__}: {error}"})
                else:
                    time.sleep(2 ** attempt)
        if windows is None:
            continue
        for aoi, values in windows.items():
            if name == "fdc":
                result[aoi].update(mask=values["Mask"], frp=values["Power"], fire_temp=values["Temp"], fire_area=values["Area"])
            elif name == "lst":
                result[aoi]["lst"] = np.where(values["DQF"] == 0, values["LST"], np.nan)
            else:
                result[aoi][f"bt_{name}"] = np.where(values["DQF"] <= 1, values["CMI"], np.nan)
    return stamp, result, state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoi", nargs="+", required=True, help="pantanal usa la raíz de --data-dir; el resto, su subcarpeta")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="inclusive, UTC")
    parser.add_argument("--step-minutes", type=int, default=60, choices=(10, 20, 30, 60))
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    import requests
    from requests.adapters import HTTPAdapter
    session = requests.Session()
    session.mount("https://", HTTPAdapter(pool_connections=16, pool_maxsize=32))
    roots = {aoi: Path(args.data_dir) if aoi == "pantanal" else Path(args.data_dir) / aoi for aoi in args.aoi}
    bboxes = {aoi: load_manifest(root)["bbox_wgs84"] for aoi, root in roots.items()}
    first, last = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc), datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    started = time.time()
    with ThreadPoolExecutor(16) as pool:
        indexes = list(pool.map(lambda day: index_day(session, day), days))
    keys = {name: {} for name in PRODUCTS}
    for index in indexes:
        for name in PRODUCTS:
            keys[name].update(index[name])
    stamps = sorted(s for s in keys["fdc"] if int(s[9:11]) % args.step_minutes == 0)
    if not stamps:
        raise SystemExit("Sin archivos FDC en el período")
    job = lambda stamp, state: (stamp, {name: keys[name].get(stamp) for name in PRODUCTS}, bboxes, state)
    _, first_result, state = read_step(job(stamps[0], {}))  # fixes navigation and windows for every worker
    if "navigation" not in state:
        raise SystemExit(f"No se pudo leer el primer paso: {state['failures']}")
    reference = {"windows": state["windows"], "navigation": state["navigation"]}
    steps, failures, fetched = {stamps[0]: first_result}, list(state["failures"]), state["bytes"]
    with ProcessPoolExecutor(args.workers) as pool:
        for stamp, result, worker_state in pool.map(read_step, [job(s, reference) for s in stamps[1:]], chunksize=4):
            steps[stamp] = result
            failures += worker_state["failures"]
            fetched += worker_state["bytes"]
    state = {**reference, "failures": failures, "bytes": fetched, "proj": dict(reference["navigation"][2])}
    times = [datetime.strptime(s, "%Y%j%H%M").replace(tzinfo=timezone.utc) for s in stamps]
    for aoi, root in roots.items():
        window = state["windows"][aoi]
        lat, lon, corner_lat, corner_lon = window_geometry(window, state["navigation"][0], state["navigation"][1], state["proj"])
        shape = lat.shape
        cube = {name: np.full((len(stamps), *shape), np.nan, dtype=np.float32) for name in ("bt_mir", "bt_tir", "lst", "frp", "fire_temp", "fire_area")}
        mask = np.full((len(stamps), *shape), -1, dtype=np.int16)
        for i, stamp in enumerate(stamps):
            for name, values in steps[stamp][aoi].items():
                (mask if name == "mask" else cube[name])[i] = values
        classes = fire_class(mask)
        hotspots = []
        for i, row, col in zip(*np.nonzero(classes)):
            value = lambda name: None if not np.isfinite(cube[name][i, row, col]) else round(float(cube[name][i, row, col]), 2)
            hotspots.append({"utc": times[i].strftime("%Y-%m-%dT%H:%MZ"), "row": int(row), "col": int(col), "lat": round(float(lat[row, col]), 5), "lon": round(float(lon[row, col]), 5), "clase": int(classes[i, row, col]), "frp_mw": value("frp"), "temperatura_fuego_k": value("fire_temp"), "bt_mir_k": value("bt_mir"), "bt_tir_k": value("bt_tir")})
        out = root / "thermal"
        out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out / "cube.npz", times=np.array([t.strftime("%Y-%m-%dT%H:%MZ") for t in times]), lat=lat, lon=lon, corner_lat=corner_lat, corner_lon=corner_lon, mask=mask, **cube)
        (out / "hotspots.json").write_text(json.dumps(hotspots, ensure_ascii=False), encoding="utf-8")
        width, height = footprint_km(corner_lat, corner_lon)
        processed = mask >= 0
        manifest = {
            "aoi": aoi, "bbox_wgs84": bboxes[aoi], "generated_utc": datetime.now(timezone.utc).isoformat(), "satellite": "GOES-19 (GOES-East, 75,2° O)", "bucket": BUCKET,
            "products": {"focos": "ABI-L2-FDCF (Mask, Power, Temp, Area)", "bt_mir": "ABI-L2-CMIPF banda 7, 3,9 µm, K", "bt_tir": "ABI-L2-CMIPF banda 14, 11,2 µm, K", "lst": "ABI-L2-LST2KMF, K, horario, solo DQF=0"},
            "period_utc": [times[0].isoformat(), times[-1].isoformat()], "step_minutes": args.step_minutes, "time_steps": len(stamps),
            "steps_with": {name: int(np.isfinite(cube[name]).any(axis=(1, 2)).sum()) for name in ("bt_mir", "bt_tir", "lst")},
            "navigation": {"x": list(state["navigation"][0]), "y": list(state["navigation"][1]), "projection": state["proj"]},
            "window_rows_cols": list(window), "grid_shape": list(shape), "pixels": int(lat.size), "pixel_km_east_west": round(float(np.median(width)), 2), "pixel_km_north_south": round(float(np.median(height)), 2),
            "hotspot_detections": len(hotspots), "hotspot_detections_by_class": {FIRE_CLASSES[c]: int((classes == c).sum()) for c in FIRE_CLASSES},
            "days_with_hotspots": len({h["utc"][:10] for h in hotspots}), "pixels_ever_hot": int((classes > 0).any(axis=0).sum()),
            "cloud_fraction_of_processed": round(float(np.isin(mask, CLOUD_CODES).sum() / max(processed.sum(), 1)), 4),
            "failures": [f for f in state["failures"]],
            "limits": "Píxel de 2 km en el nadir, mayor en el AOI; un foco indica anomalía térmica dentro del píxel, no su posición ni un incendio confirmado. Nubes y humo denso impiden la detección.",
        }
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(aoi, {k: manifest[k] for k in ("time_steps", "pixels", "pixel_km_east_west", "pixel_km_north_south", "hotspot_detections", "days_with_hotspots", "pixels_ever_hot", "cloud_fraction_of_processed")})
    print(f"{len(stamps)} pasos, {state.get('bytes', 0) / 1e9:.2f} GB leídos, {len(state['failures'])} fallos, {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
