"""Select repeat-geometry candidates containing each city, not just bbox overlap."""
import json
from collections import defaultdict
from pathlib import Path
from rasterio.features import geometry_mask
from rasterio.transform import from_origin


def contains(entry, lon, lat):
    for group in entry.get('polygons', []):
        for ring in group:
            coordinates=list(map(float,ring.split()))
            points=[[coordinates[i+1],coordinates[i]] for i in range(0,len(coordinates),2)]
            if geometry_mask([{'type':'Polygon','coordinates':[points]}],(1,1),from_origin(lon-.0000005,lat+.0000005,.000001,.000001),invert=True)[0,0]:
                return True
    return False


def select(entries,lon,lat):
    groups=defaultdict(list)
    for entry in entries:
        parts=entry['producer_granule_id'].split('_')
        if contains(entry,lon,lat):
            # track, direction, frame, mode, polarization and frequency; cycle/date excluded.
            groups[tuple(parts[5:11])].append(entry)
    candidates=[]
    for key,scenes in groups.items():
        scenes.sort(key=lambda e:e['time_start'])
        if len(scenes)>=2:
            candidates.append((key,scenes[-2:]))
    candidates.sort(key=lambda item:item[1][-1]['time_start'],reverse=True)
    return candidates


def main():
    root=Path(__file__).resolve().parents[1]
    entries=json.loads((root/'catalog/chile_cmr.json').read_text())['response']['feed']['entry']
    result={'status':'candidatos por huella y geometría nominal; grilla y calidad pendientes de HDF5','regions':{}}
    for name,lon,lat in [('santiago',-70.66,-33.45),('valparaiso',-71.613,-33.047)]:
        candidates=select(entries,lon,lat)
        pairs=[]
        for key,scenes in candidates:
            pairs.append({'geometry_key':list(key),'scenes':[{'id':e['id'],'granulo':e['producer_granule_id'],'fecha_observacion':e['time_start'],'url_metadatos':f"https://cmr.earthdata.nasa.gov/search/concepts/{e['id']}.umm_json",'estimated_mib':float(e.get('granule_size',0)),'url_hdf5':next((x['href'] for x in e.get('links',[]) if x.get('href','').endswith('.h5') and x.get('href','').startswith('https://')),None)} for e in scenes]})
        result['regions'][name]={'point_wgs84':[lon,lat],'pairs':pairs}
        print(name,len(pairs),'compatible candidate pairs')
    (root/'catalog/chile_pairs.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':
    main()
