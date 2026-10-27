import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from fractions import Fraction
import time,json,sys,resource,platform

def run(n,seconds,minmod=1):
 t=time.monotonic(); cpu=time.process_time()
 columns=[]; rr=[];cc=[]
 for m in range(minmod,n):
  for a in range(1,min(m,n-m)+1):
   v=list(range(a,n+1,m));j=len(columns);columns.append((a,m,v))
   rr.extend([x-1 for x in v]+[n+m-1]);cc.extend([j]*(len(v)+1))
 A=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(2*n-1,len(columns))).tocsc()
 c=np.array([1/m for a,m,v in columns])
 lo=np.r_[np.ones(n),np.zeros(n-1)];hi=np.ones(2*n-1)
 res=milp(c,integrality=np.ones(len(c)),bounds=Bounds(0,1),constraints=LinearConstraint(A,lo,hi),options={'time_limit':seconds,'mip_rel_gap':0.,'threads':1})
 out={'n':n,'minmod':minmod,'time_limit':seconds,'wall':time.monotonic()-t,'cpu':time.process_time()-cpu,'status':res.status,'message':res.message,'bound':getattr(res,'mip_dual_bound',None),'nodes':getattr(res,'mip_node_count',None)}
 if res.x is not None:
  selected=[columns[j] for j in np.flatnonzero(res.x>.5)];occ=[0]*n
  for a,m,v in selected:
   assert v==list(range(a,n+1,m)) and len(v)>=2
   for x in v:occ[x-1]+=1
  assert all(v==1 for v in occ)
  assert len({m for a,m,v in selected})==len(selected)
  heft=sum((Fraction(1,m) for a,m,v in selected),Fraction())
  out.update(heft=str(heft),heft_float=float(heft),classes=selected)
 with open('results.jsonl','a') as f:f.write(json.dumps(out)+'\n')
 print(json.dumps(out),flush=True)

if __name__=='__main__':
 for arg in sys.argv[1:]:
  n,sec=arg.split(':');run(int(n),float(sec))
