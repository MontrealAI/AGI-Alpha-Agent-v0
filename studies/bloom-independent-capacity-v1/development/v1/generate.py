# SPDX-License-Identifier: Apache-2.0
import random

def make_case(seed):
    rng = random.Random(seed)
    offset = seed-20001 if 20001 <= seed <= 20048 else (seed-30001 if 30001 <= seed <= 30024 else seed-101)
    n = [48,72,96,128][(offset//3) % 4]
    kind = ['sparse_dag','layered_dag','hub','cyclic_modules'][(offset//12) % 4]
    nodes,edges = [f'p{i:04d}' for i in range(n)],set()
    if kind == 'sparse_dag':
        for u in range(n):
            for _ in range(rng.randint(1,4)):
                if u+1 < n:
                    edges.add((u,rng.randrange(u+1,n)))
    elif kind == 'layered_dag':
        width = max(6,n//6)
        for u in range(n):
            lo,hi = (u//width+1)*width,min(n,(u//width+2)*width)
            if lo < hi:
                for _ in range(3):
                    edges.add((u,rng.randrange(lo,hi)))
    elif kind == 'hub':
        hubs = rng.sample(range(n//3,2*n//3),4)
        for u in range(n//3):
            edges.add((u,rng.choice(hubs)))
        for hub in hubs:
            for v in rng.sample(range(2*n//3,n),max(3,n//9)):
                edges.add((hub,v))
        for _ in range(n):
            u,v = sorted(rng.sample(range(n),2))
            edges.add((u,v))
    else:
        for start in range(0,n,8):
            group = list(range(start,min(n,start+8)))
            for i,u in enumerate(group):
                edges.add((u,group[(i+1) % len(group)]))
                if start+8 < n and rng.random() < .5:
                    edges.add((u,rng.randrange(start+8,n)))
    apps = nodes[-6:]
    edges.add((0,n-1))
    q,pool = [8,32,96][offset % 3],rng.sample(range(n),max(4,n//4))
    queries = []
    for i in range(q):
        source_pool = pool if i % 3 else list(range(n))
        queries.append(sorted(nodes[x] for x in rng.sample(source_pool,rng.choice([1,1,2,3]))))
    queries[0] = [nodes[0]]
    tests = [{'id':f't{i:02d}','covers':[apps[i]],'cost':rng.randint(3,12)} for i in range(6)]
    for i in range(6,10):
        tests.append({'id':f't{i:02d}','covers':sorted(rng.sample(apps,rng.randint(2,5))),'cost':rng.randint(6,18)})
    return {'schema':'bloom-dependency-case/v1','id':f'world-{seed}','seed':seed,'topology':kind,
        'nodes':nodes,'edges':[[nodes[u],nodes[v]] for u,v in sorted(edges)],'applications':apps,
        'queries':queries,'changed':queries[0],'tests':tests,'coverage_cost_unit':'synthetic_test_duration',
        'real_regression_safety':'not_established'}
