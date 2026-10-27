import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.study import *
p=ROOT/'development/campaign3';p.mkdir(exist_ok=False);out=[];start=time.perf_counter()
for k,(seed,regime) in enumerate(zip([27101,27102,27103,27104],REGIMES)):
 for arm in ARMS[k:]+ARMS[:k]:
  s=run_stream(seed,regime,arm,p/f'{k:02}-{arm}');out.append(s);print(json.dumps({x:s[x] for x in ['arm','qualified','offered','total_cpu_ms','successor_constructed']}),flush=True)
(p/'summaries.json').write_text(json.dumps(out,indent=2)+'\n');(p/'execution.json').write_text(json.dumps({'wall_seconds':time.perf_counter()-start,'full_development_campaign':3})+'\n')
