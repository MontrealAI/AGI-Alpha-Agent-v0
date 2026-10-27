import itertools,json,math,time,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix,csc_matrix

ROOT=Path(__file__).resolve().parent
Q=15;D=3;N=Q**D
def encode(v):return int(v[0]*Q*Q+v[1]*Q+v[2])
POINTS=np.array(list(itertools.product(range(Q),repeat=D)),dtype=np.int16)
NEIGHBORS=np.array([[encode((v+o)%Q) for o in np.array(list(itertools.product((-1,0,1),repeat=D)))] for v in POINTS],dtype=np.int32)
CUBES=np.array([[encode((v+o)%Q) for o in np.array(list(itertools.product((0,1),repeat=D)))] for v in POINTS],dtype=np.int32)
rows=np.repeat(np.arange(N),8);cols=CUBES.ravel();vals=np.ones(len(cols))
A=coo_matrix((vals,(rows,cols)),shape=(N,N)).tocsc()
def verify(ids):
    ids=list(map(int,ids));seen=set(ids)
    return len(ids)==len(seen) and all(0<=x<N for x in ids) and all(len(seen.intersection(NEIGHBORS[x]))==1 for x in ids)
def global_run(seconds):
    r=[];c=[];dat=[]
    for d in range(D):
        for k in range(Q):
            selected=np.where((POINTS[:,d]==k)|(POINTS[:,d]==((k+1)%Q)))[0]
            r.extend([len(r)//450]*len(selected));c.extend(selected);dat.extend([1]*len(selected))
    from scipy.sparse import vstack
    AA=vstack([A,coo_matrix((dat,(r,c)),shape=(D*Q,N)).tocsc()]).tocsc()
    ub=np.r_[np.ones(N),np.full(D*Q,52.)]
    t=time.time();res=milp(-np.ones(N),integrality=np.ones(N),bounds=Bounds(0,1),constraints=LinearConstraint(AA,-np.inf,ub),options={'time_limit':seconds,'mip_rel_gap':0})
    ids=np.flatnonzero(res.x>.5).tolist() if res.x is not None else []
    out={'stage':'global','seconds':time.time()-t,'status':int(res.status),'message':res.message,'size':len(ids),'valid':verify(ids),'dual_bound':float(res.mip_dual_bound) if hasattr(res,'mip_dual_bound') and res.mip_dual_bound is not None else None,'gap':float(res.mip_gap) if hasattr(res,'mip_gap') and res.mip_gap is not None else None,'points':POINTS[ids].tolist()}
    (ROOT/'global_milp.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='points'}),flush=True)

def local_run(seconds,seed):
    rng=np.random.default_rng(seed);data=json.loads((ROOT/'c15_3_published383.json').read_text());initial=set(map(encode,data['points']));selected=set(initial);best=set(initial);start=time.time();records=[];i=0
    assert verify(selected)
    while time.time()-start<seconds:
        i+=1
        if i%8==0:selected=set(best)
        center=POINTS[int(rng.choice(list(selected)))];delta=np.abs(POINTS-center);distance=np.minimum(delta,Q-delta)
        mode=i%4
        if mode==0:
            region=set(np.where(np.max(distance,axis=1)<=int(rng.integers(2,5)))[0])
            removed=selected&region
        elif mode==1:
            dim=int(rng.integers(3));width=int(rng.integers(2,5));removed={v for v in selected if distance[v,dim]<=width}
        elif mode==2:
            removed=set(map(int,rng.choice(list(selected),size=int(rng.integers(15,75)),replace=False)))
        else:
            removed=set(sorted(selected,key=lambda v:sum(distance[v]))[:int(rng.integers(30,130))])
        fixed=selected-removed;blocked=np.zeros(N,dtype=bool)
        if fixed:blocked[NEIGHBORS[list(fixed)].ravel()]=True
        available=np.where(~blocked)[0];AA=A[:,available];useful=np.diff(AA.tocsr().indptr)>1;AA=AA[useful].tocsc()
        cost=-np.ones(len(available))
        cost+=rng.random(len(available))*1e-5
        remaining=max(.05,min(1.2,seconds-(time.time()-start)));t=time.time()
        res=milp(cost,integrality=np.ones(len(available)),bounds=Bounds(0,1),constraints=LinearConstraint(AA,-np.inf,np.ones(AA.shape[0])),options={'time_limit':remaining,'mip_rel_gap':0})
        candidate=fixed|set(map(int,available[res.x>.5])) if res.x is not None else set()
        valid=verify(candidate) if candidate else False
        if valid and len(candidate)>=len(selected):selected=candidate
        if valid and len(candidate)>len(best):
            best=set(candidate);(ROOT/f'c15_3_best_seed{seed}.json').write_text(json.dumps({'q':Q,'dimension':D,'points':POINTS[sorted(best)].tolist(),'seed':seed,'iteration':i,'seconds':time.time()-start},indent=2));print('IMPROVEMENT',len(best),'iteration',i,flush=True)
        rec={'i':i,'mode':mode,'removed':len(removed),'available':len(available),'seconds':time.time()-t,'status':int(res.status),'candidate':len(candidate),'valid':valid,'current':len(selected),'best':len(best)};records.append(rec)
        if i%20==0:print(seed,i,'best',len(best),'current',len(selected),'time',round(time.time()-start,2),flush=True)
        if len(best)>=384:break
    out={'seed':seed,'seconds':time.time()-start,'iterations':i,'initial_size':len(initial),'best_size':len(best),'valid':verify(best),'records':records,'best_points':POINTS[sorted(best)].tolist()}
    (ROOT/f'local_search_seed{seed}.json').write_text(json.dumps(out,indent=2));print('FINAL',seed,'best',len(best),'iterations',i,flush=True)

if __name__=='__main__':
    if sys.argv[1]=='global':global_run(float(sys.argv[2]))
    else:local_run(float(sys.argv[2]),int(sys.argv[3]))
