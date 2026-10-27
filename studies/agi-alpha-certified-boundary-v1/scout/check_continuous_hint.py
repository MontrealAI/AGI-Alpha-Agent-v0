import json
import numpy as np
from numpy.polynomial.chebyshev import chebval
from scipy.optimize import minimize
r=json.load(open('scout/polynomial_probe.json'));c=np.zeros(21);c[::2]=r['cheb_even_coefficients'];out=[]
for k in range(2,41):
    for side in [0,1]:
        def fun(z):
            s,v=z
            if side==0: d=1/(k+1)+s/(k*(k+1));u=v*s/k
            else: d=1/k+s/(k*(k-1));u=v*(1-s)/k
            return -d*chebval(u+(2*np.arange(k)-k+1)*d,c).sum()
        best=min((minimize(fun,[s,v],bounds=[(0,1),(0,1)],method='Nelder-Mead',options={'xatol':1e-10,'fatol':1e-12}) for s in np.linspace(0,1,5) for v in np.linspace(0,1,5)),key=lambda x:x.fun)
        out.append({'k':k,'side':side,'max':float(-best.fun),'sv':best.x.tolist()})
print(json.dumps(sorted(out,key=lambda x:-x['max'])[:10]))
open('scout/continuous_hint.json','w').write(json.dumps(out,indent=2))
