import json, math, time
from pathlib import Path

def product(x,y):
    a,b,c,d=x; e,f,g,h=y
    return ((a-b)*(e-f)+c*f+b*g,d*f+b*h,c*g,d*h+(c-d)*(g-h))

def upper_hull(points):
    best={}
    for p in points:
        if p[1] not in best or p[0]>best[p[1]][0]: best[p[1]]=p
    hull=[]
    for b,p in sorted(best.items()):
        while len(hull)>=2:
            x,y=hull[-2],hull[-1]
            cross=(y[1]-x[1])*(p[0]-y[0])-(y[0]-x[0])*(p[1]-y[1])
            if cross>=0: hull.pop()
            else: break
        hull.append(p)
    return hull

def run(q,base,power,limit):
    states={1:[(*base,1)]}; provenance={'1':None}; best=(0,0,None);start=time.time()
    for n in range(2,limit+1):
        points=[]
        for k in range(1,n//2+1):
            for x in states[k]:
                for y in states[n-k]:
                    p=product(x[:4],y[:4]);points.append((*p,(x[4],y[4])))
        states[n]=upper_hull(points)
        v=max(states[n],key=lambda x:x[0]); bound=math.exp(math.log(v[0])/(n*power))
        if bound>best[0]:best=(bound,n,v)
        if n%10==0:print(q,n,len(points),len(states[n]),bound,'best',best[:2],round(time.time()-start,3),flush=True)
    out={'q':q,'base':base,'base_power':power,'limit':limit,'best_bound_float':best[0],'best_n':best[1],'best_profile':best[2][:4],'best_tree':best[2][4],'hull_sizes':{k:len(v) for k,v in states.items()},'seconds':time.time()-start}
    Path(f'challenge/channel_search/profile_hull_{q}.json').write_text(json.dumps(out,indent=2))

if __name__=='__main__':
    import sys
    q=int(sys.argv[1]) if len(sys.argv)>1 else 7
    configurations={7:((367,8,367,322),5),11:((148,3,148,142),3),13:((62530,1014,62530,60502),6),15:((2842,3,2842,2833),4)}
    run(q,*configurations[q],100)
