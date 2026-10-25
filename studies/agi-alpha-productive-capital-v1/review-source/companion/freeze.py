# SPDX-License-Identifier: Apache-2.0
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
paths=[]
for folder in ['companion','vendor/alpha','data/sources']:
 paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths+=[ROOT/'data/source_manifest.json',ROOT/'protocol/experiment-PROTOCOL.md']
records=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(paths))]
result={'study_id':'agi-alpha-productive-capital-v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'confirmation_generated':False,'entries':records,'entries_sha256':hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
out=ROOT/'protocol/experiment-FREEZE.json'
if out.exists():raise SystemExit('FREEZE_ALREADY_EXISTS')
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'path':str(out),'files':len(records),'entries_sha256':result['entries_sha256'],'file_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'created_at_utc':result['created_at_utc']},indent=2))
