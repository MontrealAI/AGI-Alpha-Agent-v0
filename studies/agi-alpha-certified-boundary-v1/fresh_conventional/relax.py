import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
import time,json
for n in [50,75,100,150,200,300,500]:
 t=time.monotonic();cpu=time.process_time(); rr=[];cc=[];c=[]
 for m in range(1,n):
  for a in range(1,min(m,n-m)+1):
   v=range(a,n+1,m);j=len(c);c.append(1/m)
   rr.extend([x-1 for x in v]+[n+m-1]);cc.extend([j]*(len(v)+1))
 A=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(2*n-1,len(c))).tocsc()
 r=linprog(c,A_ub=A[n:],b_ub=np.ones(n-1),A_eq=A[:n],b_eq=np.ones(n),bounds=(0,1),method='highs',options={'threads':1,'time_limit':12})
 d={'n':n,'lp':r.fun,'cpu':time.process_time()-cpu,'wall':time.monotonic()-t,'status':r.status}
 print(json.dumps(d),flush=True)
