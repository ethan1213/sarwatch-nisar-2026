"""Prepare a bounded native-grid GCOV subset; refuses misaligned time series."""
import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from science import power_db


def prepare(raw, output, catalog_path):
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    scenes, reference = [], None
    for scene in catalog["scenes"]:
        path = Path(raw) / (scene["granulo"] + ".h5")
        if not path.is_file():
            raise FileNotFoundError(path)
        with h5py.File(path) as f:
            g = f["/science/LSAR/GCOV/grids/frequencyA"]
            x, y = g["xCoordinates"][:], g["yCoordinates"][:]
            epsg = int(g["projection"][()])
            dx, dy = float(g["xCoordinateSpacing"][()]), float(g["yCoordinateSpacing"][()])
            if dx <= 0 or dy >= 0:
                raise ValueError("Unsupported grid orientation")
            # Densified AOI edges avoid assuming a geographic rectangle projects linearly.
            from rasterio.warp import transform_bounds
            bounds = transform_bounds("EPSG:4326", f"EPSG:{epsg}", *catalog["bbox_wgs84"], densify_pts=21)
            cols = np.flatnonzero((x >= bounds[0]) & (x <= bounds[2]))
            rows = np.flatnonzero((y >= bounds[1]) & (y <= bounds[3]))
            if not len(cols) or not len(rows):
                raise ValueError("AOI fuera de la escena")
            c0, c1, r0, r1 = int(cols[0]), int(cols[-1])+1, int(rows[0]), int(rows[-1])+1
            transform = from_origin(x[c0]-dx/2, y[r0]-dy/2, dx, -dy)
            grid = (epsg, r1-r0, c1-c0, tuple(transform))
            if reference is not None and grid != reference:
                raise ValueError("Grillas no alineadas; requiere reproyección explícita")
            reference = grid
            mask = g['mask'][r0:r1, c0:c1]
            exceptions = g['inputDataExceptionMask'][r0:r1, c0:c1]
            looks = g['numberOfLooks'][r0:r1, c0:c1]
            description = str(g['mask'].attrs.get('description', ''))
            if 'fully-focused' not in description or '255' not in description:
                raise ValueError('Semántica de máscara no reconocida; revisar versión del producto')
            exception_description = str(g['inputDataExceptionMask'].attrs.get('description', ''))
            if '0: no anomaly' not in exception_description:
                raise ValueError('Semántica de excepciones no reconocida')
            qa = (mask > 0) & (mask <= int(g['numberOfSubSwaths'][()])) & (exceptions == 0) & np.isfinite(looks) & (looks > 0)
            products = {}
            coverage = {}
            for pol, layer in [("HH", "HHHH"), ("HV", "HVHV")]:
                ds = g[layer]
                power = ds[r0:r1, c0:c1].astype("float32")
                for key in ("_FillValue", "missing_value"):
                    if key in ds.attrs:
                        for missing in np.atleast_1d(ds.attrs[key]):
                            power[power == missing] = np.nan
                values = power_db(power)
                values[~qa] = np.nan
                coverage[pol] = float(np.isfinite(values).mean())
                name = f"{scene['id']}_{pol}.tif"
                with rasterio.open(output/name, "w", driver="COG", width=values.shape[1], height=values.shape[0], count=1, dtype="float32", crs=f"EPSG:{epsg}", transform=transform, nodata=np.nan, compress="DEFLATE") as dst:
                    dst.write(values, 1)
                    dst.update_tags(unit="dB", source=scene["granulo"], quality="fully_focused_subswath; exception_zero; positive_looks; finite_positive_power", frequency="A", polarization=pol)
                products[pol] = name
            # Number of looks per pixel is needed by statistical change tests; stored outside `products`.
            looks_name = f"{scene['id']}_looks.tif"
            looks_values = np.where(qa, looks.astype("float32"), np.nan).astype("float32")
            with rasterio.open(output/looks_name, "w", driver="COG", width=looks_values.shape[1], height=looks_values.shape[0], count=1, dtype="float32", crs=f"EPSG:{epsg}", transform=transform, nodata=np.nan, compress="DEFLATE") as dst:
                dst.write(looks_values, 1)
                dst.update_tags(unit="looks", source=scene["granulo"], meaning="numberOfLooks del producto GCOV en píxeles con QA válida")
            scenes.append({**scene, "products": products, "ancillary": {"looks": looks_name}, "finite_positive_fraction": coverage})
            print(scene["id"], coverage, flush=True)
    result = {**catalog, "scenes": scenes, "quality_status": "QA aplicada según atributos del producto: sub-swath válido y completamente enfocado, excepción cero, looks finitos positivos y potencia válida. Validación ambiental independiente pendiente.", "grid": {"epsg": reference[0], "height": reference[1], "width": reference[2], "transform": reference[3]}}
    (output/"manifest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", default="data")
    parser.add_argument("--catalog", default="catalog/scenes.json")
    args = parser.parse_args()
    prepare(args.raw, args.output, args.catalog)
