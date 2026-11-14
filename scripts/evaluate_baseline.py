"""Retrospective persistence benchmark for AOI median backscatter, not flood risk."""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import rasterio


def evaluate(root):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    eligible=[s for s in manifest['scenes'] if s['finite_positive_fraction']['HH']>=.5]
    rows=[]
    for before,after in zip(eligible,eligible[1:]):
        days=(datetime.fromisoformat(after['fecha_observacion'].replace('Z','+00:00'))-datetime.fromisoformat(before['fecha_observacion'].replace('Z','+00:00'))).total_seconds()/86400
        if abs(days-12)>.01:
            continue
        with rasterio.open(root/before['products']['HH']) as source:
            a=source.read(1);grid=(source.crs,source.transform,source.shape)
        with rasterio.open(root/after['products']['HH']) as source:
            if grid!=(source.crs,source.transform,source.shape):
                raise ValueError('Grilla incompatible')
            b=source.read(1)
        valid=np.isfinite(a)&np.isfinite(b)
        if not valid.any():
            continue
        prediction=float(np.median(a[valid]));observed=float(np.median(b[valid]))
        rows.append({'issued_at':before['fecha_observacion'],'target_date':after['fecha_observacion'],'horizon_days':days,'prediction_db':prediction,'observed_db':observed,'absolute_error_db':abs(prediction-observed),'common_coverage':float(valid.mean())})
    return {'target':'Mediana HH del recorte en píxeles comunes válidos','method':'Persistencia: repetir mediana de la fecha anterior, sin entrenamiento','kind':'retrospective_reference_only','n_evaluations':len(rows),'mae_db':float(np.mean([r['absolute_error_db'] for r in rows])) if rows else None,'evaluations':rows,'limitations':['Pocas fechas y un único AOI; no demuestra capacidad de generalización.','No predice inundación, extensión de agua, daños ni riesgo.','No se seleccionaron hiperparámetros ni se entrenó un modelo.','Se usa máscara común del par para comparabilidad retrospectiva; no es un pipeline operativo de pronóstico.']}


if __name__=='__main__':
    result=evaluate(Path(os.environ.get('DATA_DIR','data')))
    Path('docs/persistence_benchmark.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    Path('catalog/prediction_reference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'n_evaluations':result['n_evaluations'],'mae_db':result['mae_db']}))
