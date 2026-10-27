import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import linprog
from fractions import Fraction
import time,json
cpu=time.process_time()
for degree in [4,6,8,10,12]:
 # use shifted even Chebyshev polynomials, endpoint zero basis
 from numpy.polynomial import Chebyshev,Polynomial
 bases=[]
 for i in range(degree):
  p=Chebyshev.basis(2*i,domain=[0,1]).convert(kind=Polynomial)*Polynomial([0,4,-4])
  bases.append(p)
 integ=np.array([p.integ()(1)-p.integ()(0) for p in bases])
 rows=[];params=[]
 for k in range(2,31):
  for d in np.linspace(1/(k+1),1/(k-1),220):
   maxoff=min(.5-(k-1)*d/2,(k+1)*d/2-.5)
   for z in np.linspace(0,1,21):
    a=.5-(k-1)*d/2+z*maxoff
    x=a+np.arange(k)*d
    rows.append([d*sum(p(x)) for p in bases]);params.append((k,float(d),float(a)))
 r=linprog(-integ,A_ub=rows,b_ub=np.ones(len(rows)),bounds=[(None,None)]*degree,options={'threads':1})
 p=sum((b*x for b,x in zip(bases,r.x)),Polynomial([0]))
 out={'degree':degree,'integral':-r.fun,'coeffs':p.coef.tolist(),'cheb_coeffs':r.x.tolist(),'cpu':time.process_time()-cpu}
 print(json.dumps(out),flush=True)
 with open(f'poly_{degree}.json','w') as f:json.dump(out,f)
