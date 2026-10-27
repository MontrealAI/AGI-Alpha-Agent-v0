import itertools,json,time
from pathlib import Path
import numpy as np
from switch_engine import adjacent,decode,solve

root=Path(__file__).resolve().parent
variants=json.loads((root/'variants.json').read_text())
xs=[]
for v in variants:
 r=decode(v['code']);xs.append(np.c_[2-r[:,1],r[:,3],r[:,0],2-r[:,2],r[:,4]]%7)
pool=np.unique(np.concatenate(xs),axis=0)
lookup={tuple(x):i for i,x in enumerate(pool)}
xmasks=[sum(1<<lookup[tuple(x)] for x in xx) for xx in xs]
start=time.monotonic();attempts=[];best=134753;eligible_counts={};tested=0
for vi,v in enumerate(variants):
 if len(set(v['owners']))<9:continue
 rs=decode(v['owners']);qs=decode(v['alternatives']);common=adjacent(rs,pool)&adjacent(qs,pool)
 masks=[sum(1<<int(j) for j in np.flatnonzero(c)) for c in common]
 for xi,xmask in enumerate(xmasks):
  inds=[i for i,mask in enumerate(masks) if not (mask&xmask)];byowner={}
  for i in inds:byowner.setdefault(v['owners'][i],[]).append(i)
  eligible_counts[len(byowner)]=eligible_counts.get(len(byowner),0)+1
  if len(byowner)<9:continue
  for selection in itertools.product(*byowner.values()):
   for m in range(len(selection),8,-1):
    for ss in itertools.combinations(selection,m):
     ss=list(ss);assignment=solve(rs[ss],qs[ss],xs[xi]);tested+=1
     attempts.append({'R':vi,'X':xi,'switches':m,'satisfiable':assignment is not None})
     if assignment is not None and 367**2+m*m>best:
      best=367**2+m*m;out={'modulus':7,'dimension':10,'size':best,'R':decode(v['code']).tolist(),'r':rs[ss].tolist(),'q_replacements':qs[ss].tolist(),'X':xs[xi].tolist(),'assignments':assignment.tolist(),'R_variant':vi,'X_variant':xi,'independent_verification':'PENDING'}
      (root/'expanded_product_candidate.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('FOUND',best,vi,xi,m,flush=True)
    if time.monotonic()-start>180:break
   if time.monotonic()-start>180:break
  if time.monotonic()-start>180:break
 if time.monotonic()-start>180:break
out={'best_size':best,'SAT_attempts':tested,'eligible_counts':eligible_counts,'elapsed_seconds':time.monotonic()-start,'complete':time.monotonic()-start<=180,'attempts':attempts,'scope':'Exact switch-product 2SAT over both one-exchange components and one fixed automorphism, not a global bound.'}
(root/'expanded_product_result.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='attempts'})
