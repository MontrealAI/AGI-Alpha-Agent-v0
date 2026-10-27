import json,time
import numpy as np
from numpy.polynomial.chebyshev import chebvander,chebval
from scipy.optimize import linprog,differential_evolution
rows=[]
for k in range(2,41):
    nd,nv=(501,151) if k==2 else ((151,31) if k<=5 else (81,11))
    for d in np.linspace(1/(k+1),1/(k-1),nd):
        lo=max(0,1-k*d);hi=min(d,1-(k-1)*d)
        if hi<lo-1e-12: continue
        a=np.linspace(lo,hi,nv)
        z=2*(a[:,None]+d*np.arange(k)[None,:])-1
        rows.extend(d*chebvander(z,20).sum(axis=1)[:,::2])
A=np.asarray(rows);c=np.array([1/(1-(2*j)**2) for j in range(11)]);history=[]
for it in range(8):
    t=time.time();r=linprog(-c,A_ub=A,b_ub=np.ones(len(A)),bounds=[(None,None)]*11,method='highs')
    if r.x is None: print(r.message,flush=True);break
    full=np.zeros(21);full[::2]=r.x;extra=[];worst=[]
    for k in range(2,16):
        for side in [0,1]:
            def coords(z):
                s,v=z
                if side==0: return 1/(k+1)+s/(k*(k+1)),v*s/k
                return 1/k+s/(k*(k-1)),v*(1-s)/k
            def fun(z):
                d,u=coords(z)
                return -d*chebval(u+(2*np.arange(k)-k+1)*d,full).sum()
            best=differential_evolution(fun,[(0,1),(0,1)],seed=731+it*50+k*2+side,tol=1e-10,popsize=10,maxiter=100,polish=True)
            if -best.fun>1+1e-10:
                d,u=coords(best.x);extra.append(d*chebvander(u+(2*np.arange(k)-k+1)*d,20).sum(axis=0)[::2])
            worst.append({'k':k,'side':side,'value':-best.fun,'sv':best.x.tolist()})
    e={'iteration':it,'integral':-r.fun,'coefficients':r.x.tolist(),'worst':sorted(worst,key=lambda x:-x['value'])[:3],'elapsed':time.time()-t}
    history.append(e);print(json.dumps(e),flush=True);open('scout/polynomial_cut.json','w').write(json.dumps(history,indent=2))
    if not extra: break
    A=np.vstack([A,np.asarray(extra)])
