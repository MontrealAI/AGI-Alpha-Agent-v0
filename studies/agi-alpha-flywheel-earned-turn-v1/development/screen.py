import json,time,hashlib
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import splu,cg
from scipy.sparse.csgraph import dijkstra
ROOT=Path(__file__).resolve().parents[1]
def timed(fn):
    c,w=time.process_time_ns(),time.perf_counter_ns(); value=fn()
    return value,(time.process_time_ns()-c)/1e6,(time.perf_counter_ns()-w)/1e6
def network(side,rng):
    n=side*side; edges=[]
    for u in range(n):
        if u%side+1<side: edges.append((u,u+1,float(rng.uniform(.5,2))))
        if u+side<n: edges.append((u,u+side,float(rng.uniform(.5,2))))
    row=[]; col=[]; val=[]; diag=np.full(n,.1)
    for u,v,w in edges:
        row.extend([u,v]); col.extend([v,u]); val.extend([-w,-w]); diag[u]+=w; diag[v]+=w
    A=coo_matrix((val,(row,col)),shape=(n,n)).tocsc()+diags(diag)
    G=coo_matrix(([-v for v in val],(row,col)),shape=(n,n)).tocsr()
    return A,G,edges
def schedule(dur,deps,order,workers=3):
    finish=[0]*len(dur); slots=[0]*workers
    for j in order:
        ready=max([finish[d] for d in deps[j]]+[0]); k=min(range(workers),key=lambda k:max(slots[k],ready))
        finish[j]=max(slots[k],ready)+dur[j]; slots[k]=finish[j]
    return max(finish),finish
def main():
    rows=[]; started=time.process_time_ns()
    for seed in [27001,27002,27003,27004]:
        for side,njobs in [(24,12),(40,18)]:
            rng=np.random.default_rng(seed+side); A,G,edges=network(side,rng); n=A.shape[0]; rhs=rng.normal(size=(n,12)); candidates={}
            for name,fn in [('direct',lambda:np.column_stack([splu(A).solve(rhs[:,j]) for j in range(12)])),('cached_factor',lambda:splu(A).solve(rhs)),('cg',lambda:np.column_stack([cg(A,rhs[:,j],rtol=1e-11,atol=0,maxiter=4000)[0] for j in range(12)]))]:
                x,c,w=timed(fn); residual=float(np.max(np.abs(A@x-rhs)))
                candidates[name]={'cpu_ms':c,'wall_ms':w,'residual':residual,'valid':residual<1e-8}
            rows.append({'domain':'network','seed':seed,'size':n,'candidates':candidates})
            destinations=rng.integers(0,n,size=12); source=int(rng.integers(0,n)); x,c,w=timed(lambda:np.array([dijkstra(G,indices=source)[d] for d in destinations])); tree,c2,w2=timed(lambda:dijkstra(G,indices=source)); y=tree[destinations]
            rows.append({'domain':'routes','seed':seed,'size':n,'valid':bool(np.allclose(x,y)),'direct_cpu_ms':c,'reuse_cpu_ms':c2,'direct_wall_ms':w,'reuse_wall_ms':w2,'scope':'fixed source; ordinary cached tree equally enabled'})
            deps=[[i-1] if i and rng.random()<.4 else [] for i in range(njobs)]; dur=rng.integers(1,10,size=(12,njobs)).tolist(); order=list(range(njobs)); x,c,w=timed(lambda:[schedule(d,deps,order) for d in dur]); y,c2,w2=timed(lambda:[schedule(d,deps,tuple(order)) for d in dur])
            rows.append({'domain':'scheduling','seed':seed,'size':njobs,'valid':x==y,'direct_cpu_ms':c,'reuse_cpu_ms':c2,'note':'topological dispatch screen only; prior native specialist remains stronger reference; not a scheduling superiority claim'})
    out={'charter_sha256':hashlib.sha256((ROOT/'protocol/DEVELOPMENT_CHARTER.json').read_bytes()).hexdigest(),'screen_cpu_ms':(time.process_time_ns()-started)/1e6,'rows':rows,'selection':'grounded sparse network analysis','reason':'A low-rank successor can execute retained factor solves on a changed operator derived from the actual accepted preceding response. Route changes invalidate a tree; priority caching supplies negligible construction benefit. The numerical domain has native direct/CG and equally enabled reuse. Development selection only.'}
    (ROOT/'development/SCREEN_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
