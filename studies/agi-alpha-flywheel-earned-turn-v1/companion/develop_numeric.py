import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.numerical import *
from review.checker import check
from runtime.workbench_client import WorkbenchClient
rows=[]
with WorkbenchClient() as client:
 for seed in [27101,27102,27103,27104]:
  for side in [48,64]:
   t=make_task(seed,side);A=matrix(t);oid=operator_id(t);b=np.asarray(t['rhs'])
   fs={}
   for method in ['MMD_AT_PLUS_A','COLAMD']:
    f,build=measure(lambda:Factor(A,oid,method));x,solve=measure(lambda:f.solve(b));v,ck=measure(lambda:check(t,x.tolist()));fs[method]=f
    rows.append({'seed':seed,'side':side,'method':method,'build':build,'solve':solve,'check':ck,'valid':v['valid']})
   f=fs['MMD_AT_PLUS_A'];x=f.solve(b)
   for k in [2,32]:
    changes=choose_changes(t,x,k);u,build=measure(lambda:Update(f,t,changes,digest(x.tolist())));tt=change_task(t,changes);xx,solve=measure(lambda:u.solve(b));v,ck=measure(lambda:check(tt,xx.tolist()))
    rows.append({'seed':seed,'side':side,'method':f'woodbury-{k}','build':build,'solve':solve,'check':ck,'valid':v['valid']})
   diag=A.diagonal()
   for method,x0 in [('cg-cold',None),('cg-warm',x)]:
    fresh=with_load(t,seed+900);bb=np.asarray(fresh['rhs']);res,sm=measure(lambda:cg(A,bb,x0=x0,rtol=1e-11,atol=0,maxiter=4000,M=LinearOperator(A.shape,matvec=lambda v:v/diag)));v,ck=measure(lambda:check(fresh,res[0].tolist()))
    rows.append({'seed':seed,'side':side,'method':method,'solve':sm,'check':ck,'valid':v['valid']})
   start=time.process_time_ns();r=client.run(f'dev-{seed}-{side}','Numerical development only',{'task_digest':digest(t)},lambda inp:{'valid':True,'qualified':True,'summary':'Checked native response','checker':check(t,f.solve(b).tolist())},'0'*64)
   rows.append({'seed':seed,'side':side,'method':'workbench','python_cpu_ms':(time.process_time_ns()-start)/1e6,'node_cpu_ms':sum(r['node_cpu_us'].values())/1000 if isinstance(r['node_cpu_us'],dict) else r['node_cpu_us']/1000,'wall_ms':r['transport_wall_ms']})
Path('earned_turn/development/NUMERICAL_VARIANTS.json').write_text(json.dumps({'schema':'development-variants/v1','variants':6,'rows':rows},indent=2)+'\n')
print(json.dumps(rows[:7],indent=2))
