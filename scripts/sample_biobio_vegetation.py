"""Exploratory Sentinel-2 samples at one documented coordinate; not fuel moisture."""
import json, math
from datetime import datetime, timezone
import planetary_computer as pc
import pystac_client
import rasterio
from rasterio.warp import transform
from sarwatch.ml.wildfire import boa_reflectance

LON, LAT = -72.99, -36.74
catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
rows=[]
for month in range(1, 12):
    end = 15 if month == 11 else 28
    items = list(catalog.search(collections=["sentinel-2-l2a"], intersects={"type":"Point","coordinates":[LON,LAT]}, datetime=f"2026-{month:02d}-01/2026-{month:02d}-{end:02d}", query={"eo:cloud_cover":{"lt":20}}, max_items=5).items())
    for item in items:
        try:
            values={}
            for band in ("B04","B08","B11","SCL"):
                with rasterio.open(pc.sign(item.assets[band].href)) as src:
                    x,y=transform("EPSG:4326",src.crs,[LON],[LAT])
                    values[band]=int(next(src.sample([(x[0],y[0])]))[0])
            if values["SCL"] != 4: continue
            import numpy as np
            baseline=item.properties["s2:processing_baseline"]
            red,nir,swir=[float(boa_reflectance(np.array([values[b]]),baseline)[0]) for b in ("B04","B08","B11")]
            if min(red,nir,swir)<0 or nir+red<=0 or nir+swir<=0:continue
            rows.append({"date":item.datetime.isoformat(),"item":item.id,"cloud_scene_pct":item.properties.get("eo:cloud_cover"),"scl":values["SCL"],"ndvi":round((nir-red)/(nir+red),4),"ndmi":round((nir-swir)/(nir+swir),4),"baseline":baseline})
            break
        except Exception as exc:
            print(month, type(exc).__name__)
result={"generated_utc":datetime.now(timezone.utc).isoformat(),"point":{"lon":LON,"lat":LAT},"source":"Copernicus Sentinel-2 L2A via Microsoft Planetary Computer","observations":rows,"limits":["Single pixel sample, not an area or operational fuel moisture.","SCL class 4 selected; cloud mask can fail, scene coverage and revisit vary.","NDMI uses B08 10m and B11 20m sampled at a point; resolutions differ.","No calibration against local vegetation or independent events."]}
from pathlib import Path
Path("catalog/biobio_vegetation_sample.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
