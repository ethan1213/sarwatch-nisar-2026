"""Prepare display-only simplifications of official EMSR859 polygons.

Raw input inventory records acquisition times and SHA256 from the public CEMS API.
Original full-resolution coordinates stay in work/emsr859. No simplified geometry is used to
compute area, train a model or assert a sub-hourly fire-front position.
"""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape,mapping
from shapely.ops import transform

if __name__=="__main__":
    raw=Path("work/emsr859");out=Path("catalog/official_fire_perimeters");out.mkdir(exist_ok=True)
    rows=sorted(json.loads((raw/"inventory.json").read_text()),key=lambda r:r["date_utc"])
    forward=Transformer.from_crs(4326,32718,always_xy=True).transform
    backward=Transformer.from_crs(32718,4326,always_xy=True).transform
    products=[]
    for i,row in enumerate(rows):
        content=(raw/row["file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest()==row["sha256"]
        data=json.loads(content);features=[];bounds=[]
        for f in data["features"]:
            geometry=shape(f["geometry"])
            if geometry.is_empty:continue
            simplified=transform(backward,transform(forward,geometry).simplify(20,preserve_topology=True))
            pieces=list(simplified.geoms) if simplified.geom_type=="MultiPolygon" else [simplified]
            for part in pieces:
                if part.geom_type!="Polygon":continue
                features.append({"type":"Feature","geometry":mapping(part),"properties":{"source":"Copernicus EMSR859","acquisition_utc":row["date_utc"],"notation":f["properties"].get("notation","Observed extent")}})
                bounds.append(part.bounds)
        bbox=[min(b[0]for b in bounds),min(b[1]for b in bounds),max(b[2]for b in bounds),max(b[3]for b in bounds)]
        name=f"extent_{i}.json";fc={"type":"FeatureCollection","features":features,"bbox":bbox}
        (out/name).write_text(json.dumps(fc,separators=(',',':')),encoding="utf-8")
        original=json.loads(Path("catalog/emsr859_concepcion_inventory.json").read_text(encoding="utf-8"))
        sensor=next(p["images"][0]["sensor"] for p in original["products"] if p["type"]==row["product"] and p["monitoringNumber"]==row["monitoring"])
        products.append({**row,"sensor":sensor,"asset":name,"display_sha256":hashlib.sha256((out/name).read_bytes()).hexdigest(),"display_features":len(features),"bbox":bbox})
    report={"source":"Copernicus Emergency Management Service · EMSR859 · AOI04 Concepción","retrieved_utc":datetime.now(timezone.utc).isoformat(),"products":products,"display_simplification_m":20,
       "source_url":"https://mapping.emergency.copernicus.eu/activations/EMSR859/",
       "limits":["Delimitaciones por fotointerpretación de imágenes en fechas concretas; no es un frente de fuego en tiempo real.","La primera observación es del 21 de enero; no cubre el avance inicial del 17–18.","Las diferencias entre productos también pueden reflejar sensores, visibilidad y revisión cartográfica, no solo crecimiento del incendio.","Geometrías simplificadas a 20 m para visualizar; las métricas requieren los originales."]}
    (out/"manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding="utf-8")
    print('Productos:',len(products),'bytes publicados:',sum(p.stat().st_size for p in out.glob('*.json')))
