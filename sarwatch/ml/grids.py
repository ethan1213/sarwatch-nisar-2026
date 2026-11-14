"""Grid helpers shared by label and covariate acquisition. All outputs land on the NISAR grid."""
import json
from pathlib import Path
import numpy as np
import rasterio
from affine import Affine


def manifest_grid(manifest):
    """(crs, Affine, (height, width)) from a SARWatch product manifest."""
    grid = manifest["grid"]
    transform = Affine(*grid["transform"][:6])
    return f"EPSG:{grid['epsg']}", transform, (int(grid["height"]), int(grid["width"]))


def geobox_from_manifest(manifest):
    from odc.geo.geobox import GeoBox
    crs, transform, shape = manifest_grid(manifest)
    return GeoBox(shape, transform, crs)


def write_cog(path, values, transform, crs, nodata, dtype, tags):
    """Write a single-band COG with explicit nodata, CRS and provenance tags."""
    values = np.asarray(values).astype(dtype)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="COG", width=values.shape[1], height=values.shape[0], count=1, dtype=dtype, crs=crs, transform=transform, nodata=nodata, compress="DEFLATE") as dst:
        dst.write(values, 1)
        dst.update_tags(**{k: str(v) for k, v in tags.items()})
    return path


def read_layer(path):
    with rasterio.open(path) as src:
        values = src.read(1, masked=True)
        return values.filled(np.nan).astype("float32") if np.issubdtype(values.dtype, np.floating) else values, src.transform, str(src.crs)


def load_manifest(root):
    root = Path(root)
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))
