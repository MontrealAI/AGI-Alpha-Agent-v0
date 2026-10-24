from collections import deque
from itertools import combinations
from numbers import Integral
from time import process_time_ns

class InvalidCase(ValueError):
    pass

def validate_case(case):
    nodes = case['nodes']
    if not isinstance(nodes, list) or any(not isinstance(x, str) or not x for x in nodes) or len(nodes) != len(set(nodes)):
        raise InvalidCase('nodes must be unique nonempty strings')
    known = set(nodes)
    apps = case['applications']
    if len(apps) != len(set(apps)) or not set(apps) <= known or len(apps) > 10:
        raise InvalidCase('applications must be at most ten unique known nodes')
    changed = case['changed']
    if any(x not in known for x in changed):
        raise InvalidCase('changed identifier is absent from the graph')
    for edge in case['edges']:
        if len(edge) != 2 or any(x not in known for x in edge):
            raise InvalidCase('edge must connect two known nodes')
    for query in case.get('queries', [changed]):
        if any(x not in known for x in query):
            raise InvalidCase('batch query identifier is absent from the graph')
    tests = case['tests']
    ids = [x['id'] for x in tests]
    if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
        raise InvalidCase('test identifiers must be unique nonempty strings')
    if len(tests) > 12:
        raise InvalidCase('independent exact checker supports at most twelve tests')
    for test in tests:
        if not set(test['covers']) <= set(apps):
            raise InvalidCase('test coverage must contain only application nodes')
        if isinstance(test['cost'], bool) or not isinstance(test['cost'], Integral) or test['cost'] < 0:
            raise InvalidCase('cost must be a nonnegative integer in declared test-cost units')

def impact_bfs(case):
    adjacency = {node: set() for node in case['nodes']}
    for dependency, dependent in case['edges']:
        adjacency[dependency].add(dependent)
    seen = set(case['changed'])
    frontier = deque(sorted(seen))
    edge_visits = 0
    while frontier:
        node = frontier.popleft()
        for dependent in sorted(adjacency[node]):
            edge_visits += 1
            if dependent not in seen:
                seen.add(dependent)
                frontier.append(dependent)
    return sorted(seen.intersection(case['applications'])), {'edge_visits': edge_visits, 'visited_nodes': len(seen)}

def minimum_cover(affected, tests):
    affected = set(affected)
    if not affected:
        return {'feasible': True, 'selected': [], 'cost': 0}, {'subsets_examined': 1}
    ordered = sorted(tests, key=lambda t: t['id'])
    if not affected.issubset(set().union(*(set(t['covers']) for t in ordered)) if ordered else set()):
        return {'feasible': False, 'selected': [], 'cost': None}, {'subsets_examined': 0}
    best = None
    examined = 0
    for cardinality in range(1, len(ordered) + 1):
        for selection in combinations(ordered, cardinality):
            examined += 1
            cost = sum(t['cost'] for t in selection)
            ids = tuple(t['id'] for t in selection)
            if best is not None and (cost, ids) >= best:
                continue
            covered = set().union(*(set(t['covers']) for t in selection))
            if affected.issubset(covered):
                best = (cost, ids)
    return {'feasible': True, 'selected': list(best[1]), 'cost': best[0]}, {'subsets_examined': examined}

def efficient_cover_table(case, diagnostics=None):
    validate_case(case)
    apps = case['applications']
    positions = {name:bit for bit,name in enumerate(apps)}
    tests = sorted(case['tests'],key=lambda test:test['id'])
    test_masks = [sum(1<<positions[name] for name in set(test['covers'])) for test in tests]
    size = 1<<len(tests)
    covers,costs,identifiers = [0]*size,[0]*size,[()]*size
    exact = {0:(0,())}
    for subset in range(1,size):
        low = subset&-subset
        index = low.bit_length()-1
        previous = subset^low
        covers[subset] = covers[previous]|test_masks[index]
        costs[subset] = costs[previous]+tests[index]['cost']
        identifiers[subset] = tuple(sorted(identifiers[previous]+(tests[index]['id'],)))
        option = (costs[subset],identifiers[subset])
        if covers[subset] not in exact or option<exact[covers[subset]]:
            exact[covers[subset]] = option
    result = {}
    comparisons = 0
    for wanted in range(1<<len(apps)):
        options = []
        for covered,option in exact.items():
            comparisons += 1
            if covered&wanted==wanted:
                options.append(option)
        if options:
            cost,selected = min(options)
            result[wanted] = {'feasible':True,'selected':list(selected),'cost':cost}
        else:
            result[wanted] = {'feasible':False,'selected':[],'cost':None}
    if diagnostics is not None:
        diagnostics.update(subsets_enumerated=size,distinct_exact_coverage_masks=len(exact),cover_comparisons=comparisons)
    return result

def solve(case):
    validate_case(case)
    affected, graph_work = impact_bfs(case)
    plan, plan_work = minimum_cover(affected, case['tests'])
    return {'affected': affected, **plan, 'diagnostics': {**graph_work, **plan_work}}

def solve_batch(case):
    validate_case(case)
    return [solve({**case, 'changed': query}) for query in case.get('queries', [case['changed']])]

def qualify(case, output):
    reference = solve(case)
    differences = {}
    for field in ['affected', 'feasible', 'selected', 'cost']:
        if output.get(field) != reference[field]:
            differences[field] = {'expected': reference[field], 'actual': output.get(field)}
    return {'qualified': not differences, 'differences': differences, 'reference': reference}

def choose_strategy(case, available=('walk','memo','scc','warshall','reverse'), memory_limit_bytes=None):
    started = process_time_ns()
    n = len(case['nodes'])
    m = len(set(tuple(edge) for edge in case['edges']))
    queries = case.get('queries', [case['changed']])
    nonempty = [set(query) for query in queries if query]
    q = len(nonempty)
    calls = sum(len(query) for query in nonempty)
    unique = len(set().union(*nonempty)) if nonempty else 0
    apps = len(case['applications'])
    words = max(1, (apps + 63) // 64)
    graph_words = max(1, (n + 63) // 64)
    base = max(1, n + m)
    row_bytes = 64 + 8 * words
    union_cost = calls * words
    estimates = {
        'walk': {'work': q * base, 'memory_bytes': 0},
        'memo': {'work': unique * base + union_cost + unique * 8, 'memory_bytes': unique * (row_bytes + 72)},
        'scc': {'work': 3 * base + (n + m) * words + union_cost, 'memory_bytes': n * (row_bytes + 16) + 256},
        'warshall': {'work': n * n * (1 + graph_words) + union_cost, 'memory_bytes': n * (row_bytes + 16) + 256},
        'reverse': {'work': apps * base + union_cost, 'memory_bytes': n * (row_bytes + 16) + 256}
    }
    eligible = [x for x in available if x in estimates]
    priority = {'walk':0,'memo':1,'reverse':2,'scc':3,'warshall':4}
    selected = min(eligible, key=lambda x:(estimates[x]['work'],priority[x])) if eligible else None
    reason = 'minimum declared graph-operation estimate among available strategies; actual canonical bytes are checked by the common wrapper, with charged fallback on cap failure' if selected else 'no supported strategy is available'
    return {'strategy':selected,'reason':reason,'estimates':estimates,'inputs':{'nodes':n,'edges':m,'nonempty_queries':q,'changed_identifiers':calls,'unique_changed_identifiers':unique,'app_mask_words':words,'graph_mask_words':graph_words,'applications':apps},'memory_scope':'planning estimate only, not an eligibility filter; wrapper enforces actual canonical serialized artifact byte cap and charged fallback','requested_memory_limit_bytes':memory_limit_bytes,'decision_cpu_ns':process_time_ns()-started}

def verify_certificate(case, certificate, rows):
    started = process_time_ns()
    counts = {'graph_edges':0,'certificate_vertex_visits':0,'certificate_edge_visits':0,'component_mask_unions':0,'rows_checked':0}
    def result(ok, reason):
        return {'qualified':ok,'reason':reason,'diagnostics':counts,'verification_cpu_ns':process_time_ns()-started}
    try:
        validate_case(case)
        nodes = case['nodes']
        n = len(nodes)
        if not isinstance(certificate, dict):
            return result(False,'certificate must be an object')
        components = certificate.get('components')
        order = certificate.get('order')
        masks = certificate.get('masks')
        if not isinstance(components,list) or not isinstance(order,list) or not isinstance(masks,list):
            return result(False,'components, order and masks must be lists')
        k = len(components)
        integer = lambda value: isinstance(value,int) and not isinstance(value,bool)
        if len(order)!=k or any(not integer(x) or not 0<=x<k for x in order) or len(set(order))!=k:
            return result(False,'component order must be an exhaustive permutation')
        bit_limit = (1<<len(case['applications']))-1
        if len(masks)!=k or any(not integer(x) or not 0<=x<=bit_limit for x in masks):
            return result(False,'component masks have invalid dimensions or application bits')
        if not isinstance(rows,list) or len(rows)!=n or any(not integer(x) or not 0<=x<=bit_limit for x in rows):
            return result(False,'rows have invalid dimensions or application bits')
        membership = [-1]*n
        for component_id, members in enumerate(components):
            if not isinstance(members,list) or not members:
                return result(False,'component must be a nonempty list')
            for vertex in members:
                if not integer(vertex) or not 0<=vertex<n or membership[vertex]!=-1:
                    return result(False,'component partition is out of range or duplicated')
                membership[vertex] = component_id
        if any(x<0 for x in membership):
            return result(False,'component partition omits graph nodes')
        index = {name:i for i,name in enumerate(nodes)}
        outgoing = [set() for _ in nodes]
        incoming = [set() for _ in nodes]
        for dependency, dependent in case['edges']:
            u,v = index[dependency],index[dependent]
            outgoing[u].add(v)
            incoming[v].add(u)
        counts['graph_edges'] = sum(map(len,outgoing))
        for component_id, members in enumerate(components):
            for adjacency in [outgoing,incoming]:
                reached = {members[0]}
                frontier = [members[0]]
                while frontier:
                    vertex = frontier.pop()
                    counts['certificate_vertex_visits'] += 1
                    for other in adjacency[vertex]:
                        counts['certificate_edge_visits'] += 1
                        if membership[other]==component_id and other not in reached:
                            reached.add(other)
                            frontier.append(other)
                if len(reached)!=len(members):
                    return result(False,'claimed component is not strongly connected')
        position = {component_id:i for i,component_id in enumerate(order)}
        component_edges = [set() for _ in components]
        for u, dependents in enumerate(outgoing):
            for v in dependents:
                counts['certificate_edge_visits'] += 1
                a,b = membership[u],membership[v]
                if a!=b:
                    if position[a]>=position[b]:
                        return result(False,'intercomponent edge violates topological order')
                    component_edges[a].add(b)
        expected = [0]*k
        for bit,name in enumerate(case['applications']):
            expected[membership[index[name]]] |= 1<<bit
        for component_id in reversed(order):
            for dependent in component_edges[component_id]:
                counts['component_mask_unions'] += 1
                expected[component_id] |= expected[dependent]
            if expected[component_id]!=masks[component_id]:
                return result(False,'component mask violates exact reachability recurrence')
        for vertex, component_id in enumerate(membership):
            counts['rows_checked'] += 1
            if rows[vertex]!=masks[component_id]:
                return result(False,'node row differs from its component mask')
        return result(True,'partition, strong connectivity, topological edges, mask recurrence and every node row verified')
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        return result(False,'malformed certificate or graph: '+str(exc))

def verify_reverse_certificate(case, certificate, rows):
    started = process_time_ns()
    counts = {'graph_edges':0,'witness_cells_checked':0,'closed_edges_checked':0}
    def result(ok, reason):
        return {'qualified':ok,'reason':reason,'diagnostics':counts,'verification_cpu_ns':process_time_ns()-started}
    try:
        validate_case(case)
        nodes = case['nodes']
        n = len(nodes)
        apps = case['applications']
        integer = lambda value: isinstance(value,int) and not isinstance(value,bool)
        bit_limit = (1<<len(apps))-1
        if not isinstance(rows,list) or len(rows)!=n or any(not integer(x) or not 0<=x<=bit_limit for x in rows):
            return result(False,'rows have invalid dimensions or application bits')
        if not isinstance(certificate,dict) or certificate.get('type')!='reverse_witness':
            return result(False,'certificate must have reverse_witness type')
        successors,ranks = certificate.get('next'),certificate.get('ranks')
        if not isinstance(successors,list) or not isinstance(ranks,list) or len(successors)!=len(apps) or len(ranks)!=len(apps):
            return result(False,'witness matrices have invalid application dimensions')
        for nxt, rank in zip(successors,ranks):
            if not isinstance(nxt,list) or not isinstance(rank,list) or len(nxt)!=n or len(rank)!=n:
                return result(False,'witness matrices have invalid node dimensions')
            if any(not integer(x) or not -1<=x<n for x in nxt) or any(not integer(x) or x < -1 for x in rank):
                return result(False,'witness matrices contain invalid integers')
        index = {name:i for i,name in enumerate(nodes)}
        outgoing = [set() for _ in nodes]
        for dependency, dependent in case['edges']:
            outgoing[index[dependency]].add(index[dependent])
        counts['graph_edges'] = sum(map(len,outgoing))
        for bit, app in enumerate(apps):
            root,mask = index[app],1<<bit
            nxt,rank = successors[bit],ranks[bit]
            if rows[root]&mask==0:
                return result(False,'application root does not own its bit')
            for u in range(n):
                counts['witness_cells_checked'] += 1
                if rows[u]&mask==0:
                    if nxt[u]!=-1 or rank[u]!=-1:
                        return result(False,'unset bit must have absent witness and rank')
                elif u==root:
                    if nxt[u]!=u or rank[u]!=0:
                        return result(False,'application root witness must point to itself at rank zero')
                else:
                    v=nxt[u]
                    if v<0 or v not in outgoing[u] or rows[v]&mask==0 or not rank[u]>rank[v]>=0:
                        return result(False,'set bit lacks a valid strictly descending path witness')
        for u, dependents in enumerate(outgoing):
            for v in dependents:
                counts['closed_edges_checked'] += 1
                if rows[v]&~rows[u]:
                    return result(False,'reachable application masks are not closed over graph edges')
        return result(True,'root ownership, strictly descending path witnesses, unset cells and graph-edge closure verified')
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        return result(False,'malformed reverse certificate or graph: '+str(exc))

if __name__ == '__main__':
    import json, sys
    case = json.load(sys.stdin)
    json.dump(solve(case), sys.stdout, sort_keys=True)
    sys.stdout.write('\n')
