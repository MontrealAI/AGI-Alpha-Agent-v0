#!/usr/bin/env python3
"""Preserve interrupted bytes; recover complete ordered records, never outcomes."""
from pathlib import Path
import gzip,hashlib,json,sys,zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from economy import policy_grid
from freeze_study import verify
verify(ROOT/'protocol/source-freeze.json')
p=json.loads((ROOT/'protocol.json').read_text()); exp=p['experiment']
expected=[(pol['id'],scenario,profile,seed,'network-alpha') for pol in policy_grid(p) for profile in exp['trainingProfiles'] for scenario in exp['trainingScenarios'] for seed in exp['trainingSeeds']]
out=ROOT/'results/primary'; src=out/'training-worlds.jsonl.gz'; original=out/'training-interrupted-original.jsonl.gz'
if original.exists() or (out/'recovery-manifest.json').exists():raise SystemExit('Refuse repeated recovery')
src.rename(original)
sha=hashlib.sha256(original.read_bytes()).hexdigest()
if sha!='e02b51ab0af0d5c68c9d3f20d7ea25af6dd2de52f7374837e215a0f6a8c68c41':raise SystemExit('Interrupted source changed')
dec=zlib.decompressobj(31);pending=b'';n=0;rows=[]
def record(line,target):
 global n
 if not line.endswith(b'\n'):raise ValueError('Unfinished line')
 world=json.loads(line);row=world['summary']
 identity=tuple(row[k] for k in ('policyId','scenario','profile','seed','arm'))
 if identity!=expected[n]:raise ValueError('Not an exact prescribed prefix')
 rows.append({'index':n,'identity':identity,'bytes':len(line),'sha256':hashlib.sha256(line).hexdigest()})
 target.write(line);n+=1
with original.open('rb') as source,gzip.open(src,'wb',compresslevel=3) as target:
 for block in iter(lambda:source.read(65536),b''):
  pending+=dec.decompress(block)
  while b'\n' in pending:
   line,pending=pending.split(b'\n',1);record(line+b'\n',target)
 pending+=dec.flush()
 while b'\n' in pending:
  line,pending=pending.split(b'\n',1);record(line+b'\n',target)
(out/'interrupted-unfinished-tail.bin').write_bytes(pending)
(out/'recovered-record-hashes.json').write_text(json.dumps(rows,indent=2)+'\n')
check=0
with gzip.open(src,'rt') as f:
 for line in f:json.loads(line);check+=1
if check!=n:raise ValueError('Recovered gzip verification mismatch')
manifest={'schema':'explicit-storage-prefix-recovery/v1','originalSHA256':sha,'originalBytes':original.stat().st_size,'originalGzipEOFPresent':dec.eof,'recoveredCompleteRecords':n,'recoveredGzipSHA256':hashlib.sha256(src.read_bytes()).hexdigest(),'unfinishedTailBytes':len(pending),'unfinishedTailSHA256':hashlib.sha256(pending).hexdigest(),'recordHashLedger':'recovered-record-hashes.json','originalsUnchangedAtOriginalWorkspace':True,'economicOutcomesUsedForRecovery':False,'uncompletedComputationCostUSD':None}
(out/'recovery-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
failure={'status':'STORAGE_INTERRUPTION_PRESERVED','message':'Explicit storage-capacity interruption; original bytes preserved; recovered complete ordered records only.','sessionExitCode':130,'historiesWritten':n,'trainingCompleted':n,'confirmationCompleted':0,'wallSeconds':959.81,'wallSecondsBasis':'Lower bound from last observed progress1280; interruption and recovery add unknown original CPU/complete cost','originalCompleteResearchCostUSD':None}
(out/'failure.json').write_text(json.dumps(failure,indent=2)+'\n')
print(json.dumps(manifest))
