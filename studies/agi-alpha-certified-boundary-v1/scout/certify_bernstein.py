import json,math,time,sys
from fractions import Fraction
from functools import reduce

N=21;M=20
C=lambda n,k: math.comb(n,k) if 0<=k<=n else 0
LS=math.lcm(*(C(N,i) for i in range(N+1)))
LV=math.lcm(*(C(M,i) for i in range(M+1)))
TS=[[C(i,p)*(LS//C(N,p)) if p<=i else 0 for p in range(N+1)] for i in range(N+1)]
TV=[[C(j,q)*(LV//C(M,q)) if q<=j else 0 for q in range(M+1)] for j in range(M+1)]

def coefficients():
    data=json.load(open('scout/revised_polynomial.json'))
    cs=list(map(Fraction,data['coefficients']));den=math.lcm(*(v.denominator for v in cs))
    ts=[[1],[0,1]]
    for i in range(2,21):
        a=[0]*(i+1)
        for j,x in enumerate(ts[-1]): a[j+1]+=2*x
        for j,x in enumerate(ts[-2]): a[j]-=x
        ts.append(a)
    q=[0]*21
    for j,c in enumerate(cs):
        scale=c.numerator*(den//c.denominator)
        for i,x in enumerate(ts[2*j]):q[i]+=scale*x
    return q,den

Q,DEN=coefficients()

def patch(k,side):
    A=[[0]*(M+1) for _ in range(N+1)]
    b=k+1 if side==0 else k-1;R=k*b
    moments={r:sum((2*j-k+1)**r for j in range(k)) for r in range(0,21,2)}
    for l in range(0,21,2):
        for r in range(0,l+1,2):
            p=l-r
            factor=Q[l]*C(l,r)*moments[r]*R**(20-l)*b**p
            if side==0:
                for h in range(r+2): A[p+h][p]+=factor*C(r+1,h)*k**(r+1-h)
            else:
                for t in range(p+1):
                    for h in range(r+2):A[t+h][p]+=factor*C(p,t)*(-1)**t*C(r+1,h)*b**(r+1-h)
    mid=[[sum(TS[i][p]*A[p][q] for p in range(i+1)) for q in range(M+1)] for i in range(N+1)]
    den=DEN*R**21*LS*LV
    B=[[den-sum(mid[i][q]*TV[j][q] for q in range(j+1)) for j in range(M+1)] for i in range(N+1)]
    return B

def split(B,axis):
    if axis==1:
        t=list(map(list,zip(*B)));l,r=split(t,0)
        return list(map(list,zip(*l))),list(map(list,zip(*r)))
    n=len(B)-1;m=len(B[0]);L=[[0]*m for _ in range(n+1)];R=[[0]*m for _ in range(n+1)]
    for j in range(m):
        a=[row[j] for row in B]
        for level in range(n+1):
            L[level][j]=a[0]<<(n-level);R[n-level][j]=a[-1]<<(n-level)
            a=[a[i]+a[i+1] for i in range(len(a)-1)]
    return L,R

def certify(B,budget=200000):
    stack=[(B,0)];nodes=0;leaves=0;depthmax=0
    while stack:
        b,depth=stack.pop();nodes+=1;depthmax=max(depthmax,depth)
        if min(map(min,b))>=0:leaves+=1;continue
        if max(map(max,b))<0:return {'ok':False,'reason':'negative_box','nodes':nodes,'depth':depth}
        if nodes>=budget or depth>=50:return {'ok':False,'reason':'budget','nodes':nodes,'depth':depth}
        left,right=split(b,depth%2);stack.append((left,depth+1));stack.append((right,depth+1))
    return {'ok':True,'nodes':nodes,'leaves':leaves,'depth':depthmax}

if __name__=='__main__':
    ks=list(map(int,sys.argv[1:])) or list(range(2,41));out=[]
    for k in ks:
        for side in [0,1]:
            start=time.time();ans=certify(patch(k,side));ans.update(k=k,side=side,seconds=time.time()-start);out.append(ans);print(json.dumps(ans),flush=True)
            open('scout/bernstein_results.json','w').write(json.dumps(out,indent=2))
            if not ans['ok']:sys.exit(1)
