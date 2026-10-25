import sys,json,time,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.numerical import *
rows=[]
for seed in [27101,27102,27103,27104]:
 for side in [48,64]:
  t=make_task(seed,side);A=matrix(t);oid=operator_id(t);f=Factor(A,oid,'COLAMD');x=f.solve(t['rhs'])
  for rank in [2,32]:
   changes=choose_changes(t,x,rank);tt=change_task(t,changes);nid=operator_id(tt);AA=matrix(tt)
   for rep in range(3):
    u,build=measure(lambda:Update(f,t,changes,digest(x.tolist()),validated_ids=(oid,nid)))
    _,use=measure(lambda:u.solve(tt['rhs']));ff,nativebuild=measure(lambda:Factor(AA,nid,'COLAMD'));_,nativeuse=measure(lambda:ff.solve(tt['rhs']))
    rows.append({'seed':seed,'side':side,'rank':rank,'repetition':rep,'update_build_ms':build['cpu_ms'],'update_use_ms':use['cpu_ms'],'native_build_ms':nativebuild['cpu_ms'],'native_use_ms':nativeuse['cpu_ms']})
policy={}
for side in [48,64]:
 for rank in [2,32]:
  rr=[r for r in rows if r['side']==side and r['rank']==rank]
  policy[f'{side}:{rank}']={k:statistics.median(r[k] for r in rr) for k in ['update_build_ms','update_use_ms','native_build_ms','native_use_ms']}
result={'schema':'development-calibration/v1','rows':rows,'policy':policy,'authority':'Measured development CPU forecasts only; no confirmatory outcomes; conservative 1.20 multiplier on candidate costs; common verification/dispatch charged in actual experiment'}
Path('earned_turn/development/CALIBRATION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(policy,indent=2))
