import itertools,json,time,hashlib
from pathlib import Path
from collections import deque
import numpy as np

root=Path(__file__).resolve().parent
r=np.loadtxt(root/'R367.txt',dtype=np.int16)
n=7**5
powers=7**np.arange(4,-1,-1)
offsets=np.array(list(itertools.product((-1,0,1),repeat=5)),dtype=np.int16)
vertices=np.array(list(itertools.product(range(7),repeat=5)),dtype=np.int16)
neighbors={}
def neighborhood(v):
 if v not in neighbors:neighbors[v]=((vertices[v]+offsets)%7)@powers
 return neighbors[v]
base=frozenset(map(int,r@powers))
counts=np.zeros(n,dtype=np.int16)
for v in base:counts[neighborhood(v)]+=1
q=deque([(base,counts)])
seen={tuple(sorted(base))};records=[];variants=[]
start=time.monotonic();maxswitch=0;hit=None
while q and len(seen)<5000 and time.monotonic()-start<60:
 state,c=q.popleft()
 zero=np.flatnonzero(c==0)
 if len(zero):hit=sorted(state|{int(zero[0])});break
 alternatives=[int(v) for v in np.flatnonzero(c==1) if int(v) not in state]
 variants.append({'code':sorted(state),'alternatives':alternatives,'owners':[int(next(w for w in neighborhood(v) if w in state)) for v in alternatives]})
 maxswitch=max(maxswitch,len(alternatives))
 records.append({'state_sha256':hashlib.sha256(','.join(map(str,sorted(state))).encode()).hexdigest(),'one_exchange_alternatives':len(alternatives)})
 for v in alternatives:
  old=next(w for w in neighborhood(v) if w in state)
  new=(state-{old})|{v};key=tuple(sorted(new))
  if key in seen:continue
  seen.add(key);nc=c.copy();nc[neighborhood(old)]-=1;nc[neighborhood(v)]+=1;q.append((new,nc))
out={'base_size':len(base),'visited_states':len(records),'discovered_states':len(seen),'remaining_queue':len(q),'component_exhausted':not q,'maximum_single_exchange_alternatives':maxswitch,'new_size':len(hit) if hit else None,'elapsed_seconds':time.monotonic()-start,'limit_seconds':60,'limit_states':5000,'states':records,'scope':'Exact one-exchange reachability only; no global optimality or inability of stronger methods follows.'}
(root/'reconfiguration_result.json').write_text(json.dumps(out,indent=2)+'\n')
(root/'variants.json').write_text(json.dumps(variants,separators=(',',':'))+'\n')
if hit:(root/'new_c7_code.json').write_text(json.dumps(vertices[hit].tolist())+'\n')
print({k:v for k,v in out.items() if k!='states'})
