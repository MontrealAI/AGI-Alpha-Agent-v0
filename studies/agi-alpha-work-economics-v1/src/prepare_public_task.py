# SPDX-License-Identifier: Apache-2.0
import csv,io,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]

def main():
    target=BASE/'raw/public-task';target.mkdir(parents=True,exist_ok=False)
    data=[json.loads((BASE/'protocol'/name).read_text()) for name in ['public_inventory_c352bad0.json','public_inventory_f836f06e.json']]
    inp={}
    for side,d in zip(['left','right'],data):
        stream=io.StringIO(newline='');w=csv.writer(stream,lineterminator='\r\n');w.writerow(['path','git_blob_sha','bytes'])
        for e in d['entries']:w.writerow([e['path'],e['git_blob_sha'],e['bytes']])
        inp[side+'Csv']=stream.getvalue();inp[side+'Key']='path';(target/(side+'.csv')).write_bytes(inp[side+'Csv'].encode())
    (target/'input.json').write_text(json.dumps(inp,indent=2)+'\n')
    brief={'id':'public-release-inventory','context':'public-release','complexity':'natural','data_origin':'public GitHub source inventories',
        'objective':'Identify all changed, added or removed docs/assets files between c352bad0 (v1.42 release source) and f836f06e (current main) before release review.',
        'acceptance':'Exact path matching; preserve every differing Git blob and byte-size value with source rows; no assertion that a change is correct or deployed.',
        'employer_deadline_seconds':28800,'system_execution_cap_seconds':30,'scope':'Tracked source assets only; excludes untracked generated site outputs and live HTTP contents.',
        'source_commits':[d['source_commit'] for d in data]}
    (target/'brief.json').write_text(json.dumps(brief,indent=2)+'\n');print(json.dumps(brief))

if __name__=='__main__':main()
