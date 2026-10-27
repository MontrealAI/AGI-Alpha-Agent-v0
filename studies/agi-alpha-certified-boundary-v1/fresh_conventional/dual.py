import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
import json,time
for n in [50,100,200]:
 t=time.monotonic();cpu=time.process_time();rr=[];cc=[];c=[];cols=[]
 for m in range(1,n):
  for a in range(1,min(m,n-m)+1):
   v=range(a,n+1,m);j=len(c);c.append(1/m);cols.append((a,m))
   rr.extend([x-1 for x in v]+[n+m-1]);cc.extend([j]*(len(v)+1))
 A=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(2*n-1,len(c))).tocsc()
 for distinct in [False,True]:
  r=linprog(c,A_ub=A[n:] if distinct else None,b_ub=np.ones(n-1) if distinct else None,A_eq=A[:n],b_eq=np.ones(n),bounds=(0,None),options={'threads':1,'time_limit':12})
  print(json.dumps({'n':n,'distinct':distinct,'lp':r.fun,'cpu':time.process_time()-cpu,'wall':time.monotonic()-t,'min_y':float(min(r.eqlin.marginals)),'max_y':float(max(r.eqlin.marginals)),'active_mods':np.flatnonzero(r.ineqlin.marginals< -1e-9).tolist() if distinct else []}),flush=True)
  np.savez(f'dual_{n}_{distinct}.npz',y=r.eqlin.marginals,z=r.ineqlin.marginals,c=c,cols=cols)
