import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.study import *
p=ROOT/'development/campaign3-remainder';p.mkdir(exist_ok=False);out=[]
for arm in ['parent_rebuilt','equivalent','native_refactor','no_reinvestment','flywheel','conventional_reuse','direct_specialist']:
 s=run_stream(27104,REGIMES[3],arm,p/arm);out.append(s);print(json.dumps({k:s[k] for k in ['arm','qualified','offered','total_cpu_ms','successor_constructed']}),flush=True)
(p/'summaries.json').write_text(json.dumps({'scope':'Complete originally declared maintenance stratum after its first retained overrun; not a new domain, algorithm or tuning campaign','summaries':out},indent=2)+'\n')
