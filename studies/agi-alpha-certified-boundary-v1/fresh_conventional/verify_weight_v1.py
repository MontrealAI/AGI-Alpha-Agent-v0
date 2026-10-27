from fractions import Fraction as F
import json,time
W=[0,159,316,493,721,981,1240,1500,1658,1818,1858]
W=W+W[-2::-1];H=20;T=F(2003,2)
cpu=time.process_time();start=time.monotonic();overall=F(0);where=None;segments=0
for k in range(2,21):
 best=F(0);arg=None
 for j in range(k):
  for r in range(H+1):
   c=F(r,H)
   low=max(c/(j+1),(1-c)/(k-j))
   ups=[]
   if j:ups.append(c/j)
   if k-1-j:ups.append((1-c)/(k-1-j))
   high=min(ups)
   if low>high or high<=0:continue
   pts={low,high}
   for ell in range(k):
    if ell==j:continue
    for s in range(H+1):
     d=F(s-r,H*(ell-j))
     if low<d<high:pts.add(d)
   pts=sorted(pts)
   if len(pts)==1:pts=pts*2
   for l,u in zip(pts,pts[1:]):
    mid=(l+u)/2;A=0;B=0
    for ell in range(k):
     x=c+(ell-j)*mid
     assert 0<=x<=1
     i=min(int(x*H),H-1)
     diff=W[i+1]-W[i]
     A+=H*diff*(ell-j)
     B+=W[i]+(r-i)*diff
    evals=[(A*l*l+B*l,l),(A*u*u+B*u,u)]
    if A<0:
     ds=F(-B,2*A)
     if l<ds<u:evals.append((A*ds*ds+B*ds,ds))
    mx,ds=max(evals)
    if mx>best:best=mx;arg=(j,r,str(ds),A,B)
    segments+=1
 if best>overall:overall=best;where=(k,arg)
 print(json.dumps({'k':k,'maximum':str(best),'float':float(best),'arg':arg,'cpu':time.process_time()-cpu,'segments':segments}),flush=True)
 assert best<=T,(k,best,T)
slopes=[H*(b-a) for a,b in zip(W,W[1:])]
variation=abs(slopes[0])+abs(slopes[-1])+sum(abs(b-a) for a,b in zip(slopes,slopes[1:]))
integral=F(sum(W[1:-1]),H)
tail=integral+F(variation,8*20**2)
assert tail<T
out={'weight_values':W,'H':H,'scale':str(T),'integral':str(integral/T),'maximum':str(overall),'where':where,'derivative_variation':variation,'tail_k_ge_21_bound':str(tail),'cpu':time.process_time()-cpu,'wall':time.monotonic()-start,'segments':segments}
with open('weight_certificate.json','w') as f:json.dump(out,f,indent=2)
print(json.dumps(out),flush=True)
assert integral/T>F(49,50)
