import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
import time,json
cpu=time.process_time();start=time.monotonic()
for intervals in [20,40,80]:
 degree=intervals//2
 A=[]
 for k in range(2,26):
  ds=np.linspace(1/(k+1),1/(k-1),241)
  zs=np.linspace(0,1,31)
  d,z=np.meshgrid(ds,zs);d=d.ravel();z=z.ravel()
  off=np.minimum(.5-(k-1)*d/2,(k+1)*d/2-.5)
  a=.5-(k-1)*d/2+z*off
  x=a[:,None]+d[:,None]*np.arange(k)
  x=np.minimum(x,1-x)*intervals
  x=np.clip(x,0,degree)
  lo=np.floor(x).astype(int);frac=x-lo
  mat=np.zeros((len(d),degree+1))
  idx=np.repeat(np.arange(len(d)),k)
  np.add.at(mat,(idx,lo.ravel()),(1-frac).ravel())
  np.add.at(mat,(idx,np.minimum(lo+1,degree).ravel()),frac.ravel())
  A.append(d[:,None]*mat[:,1:])
 A=np.concatenate(A)
 # integral symmetric: all half-side internal knots coefficient2/H; middle1/H
 c=np.ones(degree)*2/intervals;c[-1]=1/intervals
 r=linprog(-c,A_ub=csr_matrix(A),b_ub=np.ones(len(A)),bounds=[(0,None)]*degree,options={'threads':1,'time_limit':20})
 out={'intervals':intervals,'integral':-r.fun,'half_values':[0]+r.x.tolist(),'cpu':time.process_time()-cpu,'wall':time.monotonic()-start,'status':r.status}
 print(json.dumps(out),flush=True)
 with open(f'tent_{intervals}.json','w') as f:json.dump(out,f)
