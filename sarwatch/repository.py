"""Read-only access to published raster products and their provenance."""
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer


class RasterRepository:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def product_path(self, name):
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Producto fuera del directorio de datos")
        return path

    def manifest(self):
        result = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        if not result.get("scenes") or len(result.get("bbox_wgs84", [])) != 4:
            raise ValueError("Manifiesto sin escenas o área válida")
        for scene in result["scenes"]:
            for name in scene["products"].values():
                if not self.product_path(name).is_file():
                    raise FileNotFoundError(f"Producto no disponible: {name}")
        return result

    def point_series(self, scenes, polarization, longitude, latitude):
        rows, reference = [], None
        for scene in scenes:
            with rasterio.open(self.product_path(scene["products"][polarization])) as src:
                grid = (src.crs, src.transform, src.shape)
                if reference is not None and grid != reference:
                    raise ValueError("Serie con grillas incompatibles")
                reference = grid
                x, y = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform(longitude, latitude)
                row, col = src.index(x, y)
                value = np.nan
                if 0 <= row < src.height and 0 <= col < src.width:
                    sample = src.read(1, window=Window(col, row, 1, 1), masked=True)
                    if not np.ma.is_masked(sample[0, 0]) and np.isfinite(sample[0, 0]):
                        value = float(sample[0, 0])
                rows.append({"fecha":scene["fecha_observacion"], "dB":value, "granulo":scene["granulo"]})
        return rows
