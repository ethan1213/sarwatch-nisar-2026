"""Verify selected HDF5 bytes against official CMR metadata before processing."""
import hashlib
import json
from pathlib import Path
import h5py


def main():
    root=Path(__file__).resolve().parents[1]
    selection=json.loads((root/'catalog/chile_pairs.json').read_text(encoding='utf-8'))
    report=[]
    for scene in selection['regions']['santiago']['pairs'][0]['scenes']:
        metadata=json.loads((root/'catalog'/f"{scene['id']}.umm.json").read_text())
        name=scene['granulo']+'.h5'
        official=next(x for x in metadata['DataGranule']['ArchiveAndDistributionInformation'] if x['Name']==name)
        path=root/'data_raw'/'chile'/name
        if not path.is_file() or path.stat().st_size!=official['SizeInBytes']:
            raise ValueError(f'{scene["id"]}: archivo ausente o tamaño incompleto')
        md5,sha=hashlib.md5(),hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda:source.read(8*1024*1024),b''):
                md5.update(chunk)
                sha.update(chunk)
        if official['Checksum']['Algorithm']!='MD5' or md5.hexdigest()!=official['Checksum']['Value'].lower().zfill(32):
            raise ValueError(f'{scene["id"]}: checksum no coincide')
        with h5py.File(path) as source:
            g=source['/science/LSAR/GCOV/grids/frequencyA']
            grid={'epsg':int(g['projection'][()]),'shape':list(g['HHHH'].shape),'bounds_centers':[float(g['xCoordinates'][0]),float(g['yCoordinates'][-1]),float(g['xCoordinates'][-1]),float(g['yCoordinates'][0])]}
        report.append({**scene,'tamano_bytes':path.stat().st_size,'md5_calculado':md5.hexdigest(),'sha256':sha.hexdigest(),'grid':grid})
        print(scene['id'],'MD5 official verified',flush=True)
    (root/'catalog/chile_verified.json').write_text(json.dumps({'scenes':report,'status':'integridad verificada; cobertura y calidad espacial pendientes'},indent=2,ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':
    main()
