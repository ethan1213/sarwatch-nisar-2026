"""Interactive local Earthdata login. Credentials never enter the web application."""
import argparse
import json
import shutil
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--region',choices=['santiago','valparaiso'],required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    selection=json.loads((root/'catalog/chile_pairs.json').read_text(encoding='utf-8'))
    pairs=selection['regions'][args.region]['pairs']
    if not pairs:
        raise SystemExit('No hay pares candidatos para el punto seleccionado')
    scenes=pairs[0]['scenes']
    if any(not s['url_hdf5'] for s in scenes):
        raise SystemExit('CMR no entrega URLs HTTPS HDF5 para este par')
    target=root/'data_raw'/'chile'
    target.mkdir(parents=True,exist_ok=True)
    estimated=sum(s['estimated_mib'] for s in scenes)*1024*1024
    if shutil.disk_usage(target).free < estimated*1.3:
        raise SystemExit('Espacio insuficiente para el par y margen de procesamiento')
    import earthaccess
    auth=earthaccess.login(strategy='interactive',persist=False)
    if not auth.authenticated:
        raise SystemExit('Earthdata no autenticado; no se descargó el par')
    files=earthaccess.download([s['url_hdf5'] for s in scenes],local_path=str(target),threads=1)
    if len(files)!=len(scenes):
        raise SystemExit('Descarga incompleta. Revisar antes de procesar')
    print('Descarga terminada. Verificar integridad, grilla y calidad antes de publicar capas.')


if __name__=='__main__':
    main()
