"""Geographic reference sectors around a thermal cell, relative to observed wind.

These are not inferred fire flanks, safe approaches, spread probabilities or routes.
"""
import math
from pyproj import Geod
GEOD = Geod(ellps="WGS84")

def centroid(feature):
    ring=feature["geometry"]["coordinates"][0]
    points=ring[:-1] if ring[0]==ring[-1] else ring
    return tuple(sum(p[k] for p in points)/len(points) for k in (0,1))

def wind_reference_sectors(lon,lat,wind_from_deg,distance_m=2000):
    if not all(math.isfinite(v) for v in (lon,lat,wind_from_deg,distance_m)) or not 0<distance_m<=5000 or not -180<=lon<=180 or not -90<=lat<=90:
        raise ValueError("Coordenadas, viento o distancia inválidos")
    toward=(wind_from_deg+180)%360
    sectors=[]
    for key,label,bearing in (("downwind","A sotavento (referencia del viento)",toward),
            ("left","Lateral izquierdo respecto al viento",(toward-90)%360),
            ("right","Lateral derecho respecto al viento",(toward+90)%360)):
        x,y,_=GEOD.fwd(lon,lat,bearing,distance_m)
        sectors.append({"key":key,"label":label,"bearing_deg":bearing,"lon":x,"lat":y,"distance_m":distance_m})
    return sectors

def spatial_context(story,lon,lat,wind_from,speed):
    sectors=wind_reference_sectors(lon,lat,wind_from) if speed>=2 else []
    terrain=[(centroid(f),f["properties"]) for f in story["before"]["cells"]["features"]]
    for sector in sectors:
        nearest=min(terrain,key=lambda p:GEOD.inv(sector["lon"],sector["lat"],*p[0])[2])
        distance=GEOD.inv(sector["lon"],sector["lat"],*nearest[0])[2]
        sector.update({"terrain_sample_distance_m":round(distance),"elevation_m":nearest[1].get("elev_m") if distance<=3000 else None,
                       "slope_deg":nearest[1].get("slope_deg") if distance<=3000 else None})
    features=[{"type":"Feature","properties":{"kind":s["key"]},"geometry":{"type":"LineString","coordinates":[[lon,lat],[s["lon"],s["lat"]]]}} for s in sectors]
    return {"sectors":sectors,"geometry":{"type":"FeatureCollection","features":features},"safe_approach":None,"fire_flank_prediction":False,
       "limits":["Referencias geométricas al viento, no flancos reales del incendio ni rutas de ataque.",
           "Relieve: celda agregada del DEM más cercana a cada extremo, hasta 3 km; no es una medición puntual.",
           "No modela pavesas, convección, supresión ni viento dentro de quebradas."],
       "direction_status":"calm_wind_no_direction_interpretation" if speed<2 else "wind_reference_only"}

def context_for_cell(story,cell_id,time_utc):
    during=story["during"]
    cell=next((f for f in during["cells"]["features"] if f["properties"]["i"]==cell_id),None)
    if cell is None or time_utc not in during["weather"]["times"]:
        raise ValueError("Celda u hora sin observación meteorológica")
    lon,lat=centroid(cell)
    points=during["weather"]["points"]
    station=min(points,key=lambda p:GEOD.inv(lon,lat,p["lon"],p["lat"])[2])
    idx=during["weather"]["times"].index(time_utc)
    wind_from=station["wind_from_deg"][idx];speed=station["wind_kmh"][idx]
    if wind_from is None or speed is None or not math.isfinite(wind_from) or not math.isfinite(speed):
        raise ValueError("Sin viento válido para esa hora")
    result=spatial_context(story,lon,lat,wind_from,speed)
    result.update({"cell_id":cell_id,"time_utc":time_utc,"wind_from_deg":wind_from,"wind_speed_kmh":speed,
       "weather_source":"ERA5 reanálisis, punto de rejilla más cercano","weather_distance_km":round(GEOD.inv(lon,lat,station["lon"],station["lat"])[2]/1000,2)})
    return result
