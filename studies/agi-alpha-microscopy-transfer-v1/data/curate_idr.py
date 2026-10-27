import argparse, concurrent.futures, datetime, hashlib, itertools, json, math, pathlib, sys, urllib.request
import numpy as np
from numcodecs import get_codec

HERE=pathlib.Path(__file__).resolve().parents[1]/'data'
DESTINATIONS={'development':'development/idr0062','holdout':'confirmation/idr0052'}
BASES={'development':'https://livingobjects.ebi.ac.uk/idr/zarr/v0.4/idr0062A/6001240.zarr','holdout':'https://livingobjects.ebi.ac.uk/idr/zarr/v0.4/idr0052A/5514375.zarr'}

def digest(b):return hashlib.sha256(b).hexdigest()
def download(job):
    base,relative,dest=job
    url=base+'/'+relative
    with urllib.request.urlopen(url,timeout=60) as response:
        b=response.read(); headers=dict(response.headers)
    p=dest/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    return {'url':url,'relative_path':relative,'size_bytes':len(b),'sha256':digest(b),'etag':headers.get('ETag'),'last_modified':headers.get('Last-Modified'),'acquired_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}

def main():
    a=argparse.ArgumentParser();a.add_argument('selection',choices=['development','holdout']);a.add_argument('--offline',action='store_true');opts=a.parse_args()
    name=opts.selection;dest=HERE/DESTINATIONS[name];dest.mkdir(parents=True,exist_ok=True);base=BASES[name]
    labels=['0'] if name=='development' else ['Cell','Chromosomes']
    records=[];arrays=[]
    meta=['.zattrs','labels/.zattrs']+[f'labels/{g}/.zattrs' for g in labels]+[f'labels/{g}/0/.zarray' for g in labels]
    if not opts.offline:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:records.extend(pool.map(download,[(base,rel,dest) for rel in meta]))
    for group in labels:
        rel='labels/'+group+'/0';m=json.loads((dest/rel/'.zarray').read_text());shape=m['shape'];chunks=m['chunks'];grid=[range(math.ceil(n/c)) for n,c in zip(shape,chunks)]
        if name=='holdout':grid[0]=range(1)
        coords=list(itertools.product(*grid))
        jobs=[(base,rel+'/'+m['dimension_separator'].join(map(str,c)),dest) for c in coords]
        if opts.offline:
            batch=[{'url':base+'/'+relative,'relative_path':relative,'size_bytes':(dest/relative).stat().st_size,'sha256':digest((dest/relative).read_bytes()),'retrieval':'offline reuse of preserved original bytes'} for _,relative,_ in jobs]
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:batch=list(pool.map(download,jobs))
        records.extend(batch);codec=get_codec(m['compressor'])
        outshape=shape.copy()
        if name=='holdout':outshape[0]=10
        output=np.full(outshape,m['fill_value'],dtype=m['dtype'])
        for coord,rec in zip(coords,batch):
            raw=codec.decode((dest/rec['relative_path']).read_bytes());chunk=np.frombuffer(raw,dtype=m['dtype']).reshape(chunks,order=m['order'])
            starts=[i*c for i,c in zip(coord,chunks)];ends=[min(s+c,n) for s,c,n in zip(starts,chunks,outshape)]
            target=tuple(slice(s,e) for s,e in zip(starts,ends));source=tuple(slice(0,e-s) for s,e in zip(starts,ends));output[target]=chunk[source]
        output=output[0] if name=='development' else output[7,0]
        fname='native_labels.npy' if name=='development' else group.lower()+'_t7_native.npy'
        np.save(dest/fname,output,allow_pickle=False)
        arrays.append({'file':fname,'sha256':digest((dest/fname).read_bytes()),'size_bytes':(dest/fname).stat().st_size,'shape':list(output.shape),'dtype':str(output.dtype),'source_group':rel,'selection':{'channel':0} if name=='development' else {'time_index':7,'channel':0},'semantic_status':'Published label partition; no biological correctness independently established.'})
    if opts.offline:
        for p in sorted(dest.rglob('.zattrs'))+sorted(dest.rglob('.zarray')):
            b=p.read_bytes();rel=p.relative_to(dest).as_posix();records.append({'url':base+'/'+rel,'relative_path':rel,'size_bytes':len(b),'sha256':digest(b),'retrieval':'offline reuse of preserved original metadata'})
    manifest={'selection':name,'source_base':base,'license':'CC BY 4.0','license_evidence':'https://idr.github.io/ome-ngff-samples/','native_format':'OME-Zarr 0.4, Zarr v2','decoder':'numcodecs==0.16.3, Blosc/lz4','selection_frozen_before_outcome_inspection':True,'time_index_preselected':7 if name=='holdout' else None,'records':records,'arrays':arrays,'downloaded_bytes':sum(r['size_bytes'] for r in records),'notes':['The holdout time-0 chunk block includes times 0 through 9, but only preselected time index 7 is exported.','No missing chunks are inferred; every requested native chunk must be retrieved successfully.','Coordinate sample centers are declared by OME conventions; any extent convention must be stated in the receiving measurement contract.']}
    (dest/('offline_replay_manifest.json' if opts.offline else 'manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'selection':name,'downloaded_bytes':manifest['downloaded_bytes'],'arrays':arrays}))

if __name__=='__main__':main()
