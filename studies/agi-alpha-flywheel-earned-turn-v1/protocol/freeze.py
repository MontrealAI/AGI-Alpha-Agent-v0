import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
paths=[]
for folder in ['companion','runtime/vendor']:
 paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ['.py','.mjs'] and '__pycache__' not in p.parts)
for name in ['runtime/custody.py','runtime/workbench_client.py','runtime/workbench_bridge.mjs','runtime/process_recovery.py','runtime/verify_process_recovery.py','review/checker.py','review/independent_results.py','protocol/CONFIRMATORY_PROTOCOL.json','protocol/ENVIRONMENT.json','requirements.txt','protocol/DEVELOPMENT_CHARTER.json','protocol/freeze.py','development/CALIBRATION.json']:
 p=ROOT/name
 if not p.exists():raise SystemExit('MISSING:'+name)
 paths.append(p)
lock=json.loads((ROOT/'browser/BROWSER_EXECUTION_LOCK.json').read_text())
paths.extend(ROOT/p for p in lock['execution_manifest'])
files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
payload={'schema':'earned-turn-freeze/v1','files':files,'protocol_sha256':files['protocol/CONFIRMATORY_PROTOCOL.json']};sha=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
out={**payload,'freeze_sha256':sha,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'prior_study_preserved':True}
target=ROOT/'protocol/FREEZE.json'
if target.exists():
 old=json.loads(target.read_text())
 if old['freeze_sha256']!=sha:raise SystemExit('FROZEN_SOURCE_CHANGED')
 print(json.dumps({'verified_files':len(files),'freeze_sha256':sha}))
else:target.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
