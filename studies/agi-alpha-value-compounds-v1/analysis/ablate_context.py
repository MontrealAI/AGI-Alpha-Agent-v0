# SPDX-License-Identifier: Apache-2.0
"""Disclosed development ablation, not unseen confirmation or a cheaper equal outcome."""
from pathlib import Path
import sys,json,time
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from pipeline import load_mission,assess,encoded
item,before,after,consumers=load_mission('httpx-development');rows=[]
for arm in ['retained','conventional']:
 r=assess(before,after,repository=item['repository'],before_ref=item['before_ref'],after_ref=item['after_ref'],consumer_files=[],arm=arm,cache_dir=None)
 rows.append({'arm':arm,'ablation':'consumer-code-omitted','status':r['status'],'summary':r['summary'],'meter':r['meter'],'consumer_findings':len(r['consumer_assessment']['findings']),'candidate_findings':len(r['consumer_assessment']['syntactic_candidate_findings']),'losses':sum(x['status']=='call_loss' for m in r['reports'] for x in m['functions'])})
result={'schema':'context-ablation/v1','role':'postconfirmation diagnostic on exposed historical development inputs','rows':rows,'complete_outcome':'FAIL: no supplied consumer code means the historical exact app-forwarding call cannot be identified. Lower resource use cannot be priced as an equal accepted customer service.','runtime_model_calls':0,'money_usd':None}
p=R/'results/ablations/context-omitted.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encoded(result)+b'\n');print(json.dumps(result,indent=2))
