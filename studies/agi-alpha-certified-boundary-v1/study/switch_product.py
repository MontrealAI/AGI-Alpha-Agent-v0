import itertools,json,time
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

root=Path(__file__).resolve().parent
def adjacent(a,b):
 d=np.abs(a[:,None,:]-b[None,:,:]);return np.all((d<=1)|(d==6),axis=2)
def decode(ids):
 return np.array([[(v//(7**k))%7 for k in range(4,-1,-1)] for v in ids],dtype=np.int16)
def transform(r):
 x=np.c_[2-r[:,1],r[:,3],r[:,0],2-r[:,2],r[:,4]]%7
 mask=np.all(x==[2,4,6,3,5],axis=1)
 if mask.any():x[mask]=[1,5,6,3,5]
 return x
def solve(rs,qs,x):
 m=len(rs);k=len(x);total=2*m*k;rr=adjacent(rs,x);qq=adjacent(qs,x)
 if np.any(rr&qq):return None
 edgesa=[];edgesb=[]
 def forbid(u,a,v,b):
  edgesa.extend([2*u+a,2*v+b]);edgesb.extend([2*v+1-b,2*u+1-a])
 near=[[[int(v) for v in np.flatnonzero(z[i])] for z in (rr,qq)] for i in range(m)]
 for i in range(m):
  for j in range(m):
   for a in (0,1):
    for b in (0,1):
     for y in near[i][a]:
      for xx in near[j][b]:forbid(i*k+xx,a,m*k+j*k+y,b)
 qc=adjacent(qs,qs)
 for i in range(m):
  for j in range(i):
   if qc[i,j]:
    for z in range(k):
     forbid(i*k+z,1,j*k+z,1);forbid(m*k+i*k+z,1,m*k+j*k+z,1)
 graph=coo_matrix((np.ones(len(edgesa)),(edgesa,edgesb)),shape=(2*total,2*total)).tocsr()
 _,labels=connected_components(graph,directed=True,connection='strong')
 if np.any(labels[::2]==labels[1::2]):return None
 values=(labels[1::2]<labels[::2]).astype(np.int8)
 for flip in (False,True):
  val=1-values if flip else values
  if all(not (val[u//2]==u%2) or (val[v//2]==v%2) for u,v in zip(edgesa,edgesb)):
   return val.reshape((2,m,k))
 raise AssertionError('SCC assignment invalid')
variants=json.loads((root/'variants.json').read_text());base=np.loadtxt(root/'R367.txt',dtype=np.int16);fixed=transform(base)
assert len({tuple(v) for v in fixed})==367
assert not np.any(np.triu(adjacent(fixed,fixed),1))
start=time.monotonic();attempts=[];best=134753
for vi,v in enumerate(variants):
 if len(set(v['owners']))<9:continue
 r=decode(v['code']);qs=decode(v['alternatives']);rs=decode(v['owners'])
 for xi,x in enumerate((fixed,transform(r))):
  if len({tuple(t) for t in x})!=367 or np.any(np.triu(adjacent(x,x),1)):continue
  eligible=~np.any(adjacent(rs,x)&adjacent(qs,x),axis=1)
  indices=list(np.flatnonzero(eligible));byowner={}
  for i in indices:byowner.setdefault(v['owners'][i],[]).append(int(i))
  if len(byowner)<9:continue
  for selection in itertools.product(*byowner.values()):
   for m in range(len(selection),8,-1):
    for ss in itertools.combinations(selection,m):
     ss=list(ss);a=solve(rs[ss],qs[ss],x)
     attempts.append({'variant':vi,'X':xi,'switches':m,'satisfiable':a is not None})
     if a is not None and 367**2+m*m>best:
      best=367**2+m*m
      out={'q':7,'dimension':10,'size':best,'R':r.tolist(),'r':rs[ss].tolist(),'q_replacements':qs[ss].tolist(),'X':x.tolist(),'assignments':a.tolist(),'variant':vi,'X_type':xi,'origin':'new exploratory search; independent verification required'}
      (root/'product_candidate.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('FOUND',best,vi,xi,m,flush=True)
   if time.monotonic()-start>120:break
  if time.monotonic()-start>120:break
 if time.monotonic()-start>120:break
out={'best_size':best,'elapsed_seconds':time.monotonic()-start,'attempts':attempts,'scope':'Only fixed/published-transform X and eligible one-exchange variants; no global optimum inferred.'}
(root/'switch_product_result.json').write_text(json.dumps(out,indent=2)+'\n');print({'best_size':best,'attempts':len(attempts),'seconds':out['elapsed_seconds']})
