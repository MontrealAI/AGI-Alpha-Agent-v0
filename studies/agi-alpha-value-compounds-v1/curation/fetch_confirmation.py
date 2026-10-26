# SPDX-License-Identifier: Apache-2.0
import argparse, concurrent.futures, hashlib, json, os, time, urllib.error, urllib.request
from pathlib import Path

def digest(data): return hashlib.sha256(data).hexdigest()
def git_blob(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True);p.add_argument('--expected-manifest-sha256',required=True);p.add_argument('--freeze',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 source=Path(a.manifest);raw=source.read_bytes();assert digest(raw)==a.expected_manifest_sha256,'metadata identity changed'
 freeze=Path(a.freeze);assert freeze.is_file(),'protocol freeze is required before source retrieval'
 manifest=json.loads(raw);output=Path(a.output);output.mkdir(parents=True,exist_ok=False)
 started=time.time();cpu=time.process_time();unique={}
 for snapshot in manifest['snapshots']:
  for row in snapshot['files']:
   if row['blob'] not in unique:unique[row['blob']]={'repo':snapshot['repo'],'commit':snapshot['commit'],**row}
 assert len(unique)<=1500 and sum(x['size'] for x in unique.values())<=30_000_000,'retrieval budget exceeded'
 cache=output/'blobs';cache.mkdir();events=[]
 def one(row):
  url=f"https://raw.githubusercontent.com/{row['repo']}/{row['commit']}/{row['path']}";t=time.time()
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'AGI-ALPHA-Value-Compounds-public-source-research'})
   with urllib.request.urlopen(request,timeout=40) as response:
    data=response.read(row['size']+1)
   assert len(data)==row['size'],'source byte length mismatch';assert git_blob(data)==row['blob'],'source Git blob mismatch'
   (cache/row['blob']).write_bytes(data)
   return {'url':url,'blob':row['blob'],'bytes':len(data),'sha256':digest(data),'elapsed_seconds':time.time()-t,'success':True}
  except Exception as error:return {'url':url,'blob':row['blob'],'elapsed_seconds':time.time()-t,'success':False,'error':type(error).__name__+': '+str(error)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  for event in pool.map(one,unique.values()):events.append(event)
 (output/'fetch-events.json').write_text(json.dumps(events,indent=2)+'\n')
 failed=[x for x in events if not x['success']]
 if failed:
  (output/'FAILED.json').write_text(json.dumps({'failures':len(failed),'events':failed},indent=2)+'\n')
  raise RuntimeError('source retrieval failed; original events preserved')
 by_blob={x['blob']:x for x in events};records=[]
 for snapshot in manifest['snapshots']:
  for row in snapshot['files']:
   relative=Path('snapshots')/snapshot['project']/snapshot['tag']/row['path'];path=output/relative;path.parent.mkdir(parents=True,exist_ok=True);data=(cache/row['blob']).read_bytes();path.write_bytes(data)
   records.append({'path':str(relative),'project':snapshot['project'],'tag':snapshot['tag'],'source_commit':snapshot['commit'],'source_path':row['path'],'blob':row['blob'],'sha256':digest(data),'bytes':len(data)})
 summary={'schema':'value-compounds-source-fetch/v1','manifest_sha256':digest(raw),'freeze_path':str(freeze),'freeze_sha256':digest(freeze.read_bytes()),'source_files':len(records),'distinct_blob_requests':len(events),'downloaded_body_bytes':sum(x['bytes'] for x in events),'stored_snapshot_bytes':sum(x['bytes'] for x in records),'wall_seconds':time.time()-started,'process_cpu_seconds':time.process_time()-cpu,'inference_tokens':None,'inference_usd':None,'source_executed':False,'outcomes_computed':False,'files':records}
 (output/'source-custody.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='files'}))
if __name__=='__main__':main()
