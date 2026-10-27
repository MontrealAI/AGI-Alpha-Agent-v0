import json,time,sys
from fractions import Fraction
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix

def solve(n,limit):
    cols=[];ri=[];ci=[];data=[]
    for m in range(1,n):
        for a in range(1,min(m,n-m)+1):
            pts=list(range(a,n+1,m))
            if len(pts)<2: continue
            j=len(cols);cols.append((a,m,pts))
            for p in pts: ri.append(p-1);ci.append(j);data.append(1.)
            ri.append(n+m-1);ci.append(j);data.append(1.)
    A=coo_matrix((data,(ri,ci)),shape=(2*n-1,len(cols))).tocsc()
    lb=np.r_[np.ones(n),np.zeros(n-1)];ub=np.ones(2*n-1)
    start=time.time()
    res=milp(np.array([1./m for a,m,p in cols]),integrality=np.ones(len(cols)),bounds=Bounds(0,1),constraints=LinearConstraint(A,lb,ub),options={'time_limit':limit,'mip_rel_gap':.0001})
    out={'n':n,'status':int(res.status),'message':str(res.message),'elapsed':time.time()-start,'variables':len(cols)}
    if res.x is not None:
        chosen=[cols[j] for j,x in enumerate(res.x) if x>.5]
        h=sum((Fraction(1,m) for a,m,p in chosen),Fraction())
        cnt=[0]*n
        for a,m,pts in chosen:
            for p in pts: cnt[p-1]+=1
        out.update(heft=str(h),heft_float=float(h),classes=[{'a':a,'m':m,'points':p} for a,m,p in chosen],valid=all(x==1 for x in cnt) and len(set(m for a,m,p in chosen))==len(chosen),bound=float(res.mip_dual_bound),gap=float(res.mip_gap))
    print(json.dumps(out),flush=True)
    open(f'scout/cover_{n}.json','w').write(json.dumps(out,indent=2))
    return out

if __name__=='__main__':
    for n in map(int,sys.argv[1:]):
        r=solve(n,20)
        if r.get('heft_float',2)<.98: break
