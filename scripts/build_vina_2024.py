"""Reproduce a small, cloud-masked Sentinel-2 comparison around the 2–3 Feb 2024 fire.

Requires fetch_fire_dnbr.py outputs under work/historical/vina_2024/wildfire; no data is invented.
The public pack contains PNGs and traceable metadata, not raw imagery or signed credentials.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image
from rasterio.warp import Resampling
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sarwatch.ml.grids import geobox_from_manifest, read_layer
from sarwatch.ml.wildfire import boa_reflectance
from scripts.build_fire_story import to_lonlat, severity_png


def build(root=Path("work/historical/vina_2024"), output=Path("catalog/vina_2024")):
    import planetary_computer as pc
    import pystac_client
    import odc.stac
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    source=json.loads((root/"wildfire/manifest.json").read_text(encoding="utf-8"))
    assert len(source["pre_items_used"])==len(source["post_items_used"])==1, "RGB comparison currently requires one actual acquisition per side"
    catalog=pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
    geobox=geobox_from_manifest(manifest)
    output.mkdir(parents=True,exist_ok=True)
    layers=[]; masks=[]
    for key in ("pre","post"):
        identity=source[key+"_items_used"][0]["id"]
        item=catalog.get_collection("sentinel-2-l2a").get_item(identity)
        assert item is not None
        data=odc.stac.load([item],bands=["B04","B03","B02","SCL"],geobox=geobox,patch_url=pc.sign,
            resampling={"B04":"average","B03":"average","B02":"average","SCL":"nearest"},chunks=None).isel(time=0)
        valid=~np.isin(data.SCL.values,(0,1,2,3,8,9,10,11))
        masks.append(valid & (data.SCL.values!=6))
        rgba=None
        for channel,band in enumerate(("B04","B03","B02")):
            values=boa_reflectance(data[band].values,item.properties["s2:processing_baseline"])
            values[~valid]=np.nan
            grid,bounds=to_lonlat(values,geobox.transform,str(geobox.crs),Resampling.average,np.nan)
            if rgba is None:rgba=np.zeros(grid.shape+(4,),dtype="uint8");rgba[:,:,3]=np.isfinite(grid).astype("uint8")*255
            rgba[:,:,channel]=(np.nan_to_num(np.clip(grid/0.3,0,1))**(1/1.4)*255).astype("uint8")
        name=key+".png";Image.fromarray(rgba,"RGBA").save(output/name,optimize=True)
        layers.append({"date":item.datetime.isoformat(),"png":name,"bounds":bounds,"item":identity,"valid_fraction":float(valid.mean()),"display":"RGB B04/B03/B02, fixed reflectance stretch 0–0.3, gamma 1.4"})
    severity,transform,crs=read_layer(root/"wildfire/severity.tif")
    land=masks[0]&masks[1]
    bounds=severity_png(output/"severity.png",severity,land,transform,crs)
    px_area=abs(transform.a*transform.e-transform.b*transform.d)
    valid=land & (np.asarray(severity)!=255)
    affected=valid & (np.asarray(severity)>=2)
    report={"place":"Viña del Mar y entorno · incendio de febrero de 2024","generated_utc":datetime.now(timezone.utc).isoformat(),
      "source":"Sentinel-2 L2A / Copernicus, Microsoft Planetary Computer","bbox_wgs84":manifest["bbox_wgs84"],"resolution_m":30,
      "fire_dates":["2024-02-02","2024-02-03"],"observations":layers,
      "severity":{"png":"severity.png","bounds":bounds,"label":"Señal óptica de quema, dNBR"},
      "valid_comparison_fraction":float(valid.mean()),"moderate_or_high_signal_km2":round(float(affected.sum()*px_area/1e6),3),
      "raw_derivatives_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/"wildfire").glob("*.tif")},
      "sources":["https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a","https://cigiden.cl/producto/informe-de-danos-evento-incendios-02-y-03-de-febrero-de-2024-vina-del-mar-region-de-valparaiso/"],
      "limits":["No es NISAR: el incendio de 2024 es anterior a esa misión.","Señal dNBR sin validación independiente contra perímetro oficial; no es superficie quemada oficial ni clasificación de daño a viviendas.","Máscara SCL excluye nubes, sombras, nieve y agua; puede haber errores de clasificación.","Imágenes de dos días distintos, con un tramo sin observación durante el incendio. No muestran una trayectoria horaria."]}
    report["assets_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.png")}
    (output/"story.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"dates":[l["date"] for l in layers],"valid_fraction":report["valid_comparison_fraction"]}))

if __name__=="__main__":build()
