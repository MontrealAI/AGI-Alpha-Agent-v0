import json
import numpy as np
from numpy.polynomial.chebyshev import chebvander
from scipy.optimize import linprog

rows=[]
for k in range(2,41):
    for d in np.linspace(1/(k+1),1/(k-1),101):
        lo=max(0,1-k*d);hi=min(d,1-(k-1)*d)
        if hi<lo-1e-12: continue
        for a in np.linspace(lo,hi,9):
            z=2*(a+d*np.arange(k))-1
            rows.append(d*chebvander(z,20).sum(axis=0)[::2])
A=np.asarray(rows)
c=np.array([1/(1-(2*j)**2) for j in range(11)])
r=linprog(-c,A_ub=A,b_ub=np.ones(len(A)),bounds=[(None,None)]*11,method='highs')
out={'status':int(r.status),'message':r.message,'grid_only':True,'no_continuous_certificate':True}
if r.x is not None: out.update(integral=float(-r.fun),cheb_even_coefficients=r.x.tolist(),grid_max=float((A@r.x).max()))
print(json.dumps(out))
open('scout/polynomial_probe.json','w').write(json.dumps(out,indent=2))
