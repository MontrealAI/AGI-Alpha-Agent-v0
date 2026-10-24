# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import json
import platform
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter_ns, process_time_ns

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'independent'))
import reference

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def source_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def world_digest(case):
    return digest({k: case[k] for k in ['nodes', 'edges', 'applications']})

def policy_digest(version='coverage-v1'):
    return digest({'semantics': 'exact-reachability-in-supplied-graph', 'policy': version,
                   'authority': 'local-research-only', 'transactions': False})

def environment_digest():
    return digest({'implementation': platform.python_implementation(), 'python': list(sys.version_info[:2]),
        'kernel_sha256': source_digest(), 'checker_sha256': hashlib.sha256(Path(reference.__file__).read_bytes()).hexdigest(),
        'integer_arithmetic': 'arbitrary-precision'})

@dataclass
class Meter:
    counters: dict = field(default_factory=lambda: {'edge_reads': 0, 'node_visits': 0, 'bit_operations': 0,
        'constructions': 0, 'failed_constructions': 0, 'verifier_edge_visits': 0, 'verifier_node_visits': 0,
        'cover_transitions': 0, 'witness_cells_checked': 0, 'closed_edges_checked': 0})
    phases: dict = field(default_factory=dict)
    decisions: list = field(default_factory=list)
    def call(self, name, fn, *args, **kwargs):
        cpu, wall = process_time_ns(), perf_counter_ns()
        try:
            return fn(*args, **kwargs)
        finally:
            old = self.phases.setdefault(name, {'cpu_ns': 0, 'wall_ns': 0, 'calls': 0})
            old['cpu_ns'] += process_time_ns() - cpu
            old['wall_ns'] += perf_counter_ns() - wall
            old['calls'] += 1

class Graph:
    def __init__(self, case):
        reference.validate_case(case)
        if any(test['cost'] <= 0 for test in case['tests']):
            raise reference.InvalidCase('this experimental policy requires strictly positive test costs')
        self.case, self.nodes = case, case['nodes']
        self.n = len(self.nodes)
        self.index = {x: i for i, x in enumerate(self.nodes)}
        self.adj, self.rev = [set() for _ in self.nodes], [set() for _ in self.nodes]
        for a, b in case['edges']:
            u, v = self.index[a], self.index[b]
            self.adj[u].add(v)
            self.rev[v].add(u)
        self.adj, self.rev = [tuple(sorted(x)) for x in self.adj], [tuple(sorted(x)) for x in self.rev]
        self.apps = [self.index[x] for x in case['applications']]
        self.local = [0] * self.n
        for bit, node in enumerate(self.apps):
            self.local[node] |= 1 << bit
        self.m = sum(map(len, self.adj))

def walk(graph, sources, meter):
    seen, mask = set(sources), 0
    stack = list(sorted(seen))
    while stack:
        u = stack.pop()
        meter.counters['node_visits'] += 1
        mask |= graph.local[u]
        meter.counters['bit_operations'] += 1
        for v in graph.adj[u]:
            meter.counters['edge_reads'] += 1
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return mask

def scc_index(graph, meter):
    seen, order = set(), []
    for root in range(graph.n):
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, 0)]
        while stack:
            u, pos = stack[-1]
            if pos == len(graph.adj[u]):
                order.append(u)
                stack.pop()
                meter.counters['node_visits'] += 1
                continue
            v = graph.adj[u][pos]
            stack[-1] = (u, pos + 1)
            meter.counters['edge_reads'] += 1
            if v not in seen:
                seen.add(v)
                stack.append((v, 0))
    member, components = [-1] * graph.n, []
    for root in reversed(order):
        if member[root] >= 0:
            continue
        cid, group, stack = len(components), [], [root]
        member[root] = cid
        while stack:
            u = stack.pop()
            group.append(u)
            meter.counters['node_visits'] += 1
            for v in graph.rev[u]:
                meter.counters['edge_reads'] += 1
                if member[v] < 0:
                    member[v] = cid
                    stack.append(v)
        components.append(sorted(group))
    edges, indegree, masks = [set() for _ in components], [0]*len(components), [0]*len(components)
    for u in range(graph.n):
        masks[member[u]] |= graph.local[u]
        for v in graph.adj[u]:
            meter.counters['edge_reads'] += 1
            a, b = member[u], member[v]
            if a != b and b not in edges[a]:
                edges[a].add(b)
                indegree[b] += 1
    frontier, topological = deque(i for i, n in enumerate(indegree) if n == 0), []
    while frontier:
        u = frontier.popleft()
        topological.append(u)
        for v in sorted(edges[u]):
            indegree[v] -= 1
            if indegree[v] == 0:
                frontier.append(v)
    for u in reversed(topological):
        for v in sorted(edges[u]):
            masks[u] |= masks[v]
            meter.counters['bit_operations'] += 1
    return [masks[member[u]] for u in range(graph.n)], {
        'type': 'scc', 'components': components, 'order': topological, 'masks': masks}

def reverse_index(graph, meter):
    rows, nexts, ranks = [0]*graph.n, [], []
    for bit, app in enumerate(graph.apps):
        nxt, rank = [-1]*graph.n, [-1]*graph.n
        nxt[app], rank[app] = app, 0
        queue = deque([app])
        while queue:
            u = queue.popleft()
            rows[u] |= 1 << bit
            meter.counters['node_visits'] += 1
            meter.counters['bit_operations'] += 1
            for v in graph.rev[u]:
                meter.counters['edge_reads'] += 1
                if rank[v] < 0:
                    rank[v], nxt[v] = rank[u]+1, u
                    queue.append(v)
        nexts.append(nxt)
        ranks.append(rank)
    return rows, {'type': 'reverse_witness', 'next': nexts, 'ranks': ranks}

def warshall_index(graph, meter):
    rows = [(1 << u) | sum(1 << v for v in graph.adj[u] if v != u) for u in range(graph.n)]
    for k in range(graph.n):
        bit = 1 << k
        for u in range(graph.n):
            meter.counters['bit_operations'] += 1
            if rows[u] & bit:
                rows[u] |= rows[k]
                meter.counters['bit_operations'] += 1
    impact = [sum(1 << b for b, app in enumerate(graph.apps) if row & (1 << app)) for row in rows]
    _, certificate = reverse_index(graph, meter)
    return impact, certificate

def choose_bloom(case, available, memory_limit_bytes):
    n, m, apps = len(case['nodes']), len(case['edges']), len(case['applications'])
    queries = case.get('queries', [case['changed']])
    sources, q = set(x for q in queries for x in q), sum(bool(x) for x in queries)
    base = max(1, n+m)
    estimates = {'walk': q*base, 'memo': len(sources)*base+len(sources)*16,
        'scc': 5*base+n*2, 'reverse': apps*base+n*apps, 'warshall': n*n*3}
    eligible = [s for s in available if s in estimates]
    if not eligible:
        raise ValueError('no available operator')
    proposed = min(eligible, key=lambda s: (estimates[s], s))
    conventional = min((s for s in ['walk','memo','reverse'] if s in eligible),
                       key=lambda s: (estimates[s], s), default=proposed)
    selected = proposed
    if proposed in ['scc','warshall'] and estimates[proposed] > .80*estimates[conventional]:
        selected = conventional
    return {'strategy': selected, 'proposed': proposed,
        'reason': 'specialize only with at least 20% declared graph-work headroom; otherwise conventional fallback',
        'estimates': estimates, 'memory_scope': 'actual serialized payload checked after construction',
        'requested_memory_limit_bytes': memory_limit_bytes}

def build_operator(case, method, meter, available=None, payload_cap=1048576, policy='coverage-v1'):
    if available is None:
        available = ['walk','memo','scc','warshall','reverse']
    graph = meter.call('parse', Graph, case)
    if method == 'bloom':
        decision = meter.call('selection', choose_bloom, case, available, payload_cap)
    elif method == 'expert':
        decision = meter.call('selection', reference.choose_strategy, case, tuple(available), payload_cap)
    elif method in ['reverse','walk']:
        choice = next((s for s in (['reverse','memo','walk'] if method == 'reverse' else ['walk']) if s in available),None)
        if choice is None:
            raise ValueError('no legal conventional fallback available')
        decision = {'strategy': choice, 'reason': 'conventional reverse-per-application index with legal fallback'}
    else:
        raise ValueError('unknown method')
    meter.decisions.append(decision)
    preferred = decision['strategy']
    attempts = [preferred]+[s for s in ['memo','walk'] if s in available and s != preferred]
    for strategy in attempts:
        meter.counters['constructions'] += 1
        def construct():
            if strategy == 'scc':
                return scc_index(graph, meter)
            if strategy == 'reverse':
                return reverse_index(graph, meter)
            if strategy == 'warshall':
                return warshall_index(graph, meter)
            if strategy == 'memo':
                rows = [None]*graph.n
                for name in sorted(set(x for q in case.get('queries',[case['changed']]) for x in q)):
                    i = graph.index[name]
                    rows[i] = walk(graph, [i], meter)
                return rows, {'type': 'partial_bfs'}
            return [], {'type': 'direct_program'}
        rows, cert = meter.call('construction', construct)
        artifact = {'schema': 'bloom-impact-operator/v1', 'strategy': strategy,
            'world_sha256': world_digest(case), 'policy_sha256': policy_digest(policy),
            'environment_sha256': environment_digest(), 'kernel_sha256': source_digest(),
            'applications': case['applications'], 'rows': rows, 'certificate': cert,
            'authority': 'none', 'claim': 'exact only relative to supplied dependency graph'}
        encoded = meter.call('serialization', canonical, artifact)
        if len(encoded) <= payload_cap:
            meter.decisions.append({'event': 'constructed', 'strategy': strategy, 'payload_bytes': len(encoded)})
            return artifact
        meter.counters['failed_constructions'] += 1
        meter.decisions.append({'event': 'payload_rejected', 'strategy': strategy, 'payload_bytes': len(encoded),
            'cap_bytes': payload_cap, 'disposition': 'charged fallback'})
    raise ValueError('no operator fits serialized payload cap')

def verify_operator(case, artifact, meter, policy='coverage-v1'):
    if artifact.get('schema') != 'bloom-impact-operator/v1':
        return {'qualified': False, 'reason': 'unknown operator schema'}
    for key, expected in [('world_sha256',world_digest(case)), ('policy_sha256',policy_digest(policy)),
                          ('environment_sha256',environment_digest()), ('kernel_sha256',source_digest())]:
        if artifact.get(key) != expected:
            return {'qualified': False, 'reason': key+' changed; prior acceptance invalid'}
    if artifact.get('authority') != 'none' or artifact.get('applications') != case['applications']:
        return {'qualified': False, 'reason': 'invalid authority or application binding'}
    graph = Graph(case)
    cert, rows = artifact.get('certificate', {}), artifact.get('rows')
    typ = cert.get('type')
    expected_type = {'scc':'scc','reverse':'reverse_witness','warshall':'reverse_witness',
                     'memo':'partial_bfs','walk':'direct_program'}.get(artifact.get('strategy'))
    if typ != expected_type:
        return {'qualified':False,'reason':'strategy and certificate type disagree'}
    if typ == 'scc':
        result = reference.verify_certificate(case, cert, rows)
    elif typ == 'reverse_witness':
        result = reference.verify_reverse_certificate(case, cert, rows)
    elif typ == 'partial_bfs':
        if not isinstance(rows,list) or len(rows) != graph.n:
            return {'qualified':False,'reason':'partial row dimensions invalid'}
        for i, mask in enumerate(rows):
            if mask is None:
                continue
            if not isinstance(mask,int) or isinstance(mask,bool) or not 0 <= mask < (1 << len(graph.apps)):
                return {'qualified':False,'reason':'partial row invalid'}
            expected, counts = reference.impact_bfs({**case,'changed':[graph.nodes[i]]})
            meter.counters['verifier_edge_visits'] += counts['edge_visits']
            meter.counters['verifier_node_visits'] += counts['visited_nodes']
            wanted = sum(1 << b for b, name in enumerate(case['applications']) if name in expected)
            if mask != wanted:
                return {'qualified':False,'reason':'partial row differs from independent BFS'}
        result = {'qualified':True,'reason':'every supplied partial row independently replayed'}
    elif typ == 'direct_program' and rows == [] and artifact.get('strategy') == 'walk':
        result = {'qualified':True,'reason':'bound direct interpreter; every output gets fresh BFS verification'}
    else:
        result = {'qualified':False,'reason':'unsupported certificate'}
    counts = result.get('diagnostics',{})
    meter.counters['verifier_edge_visits'] += counts.get('certificate_edge_visits',0)
    meter.counters['verifier_node_visits'] += counts.get('certificate_vertex_visits',0)
    meter.counters['witness_cells_checked'] += counts.get('witness_cells_checked',0)
    meter.counters['closed_edges_checked'] += counts.get('closed_edges_checked',0)
    return {k:v for k,v in result.items() if k != 'verification_cpu_ns'}

def impact_batch(case, artifact, meter):
    graph, rows, outputs = Graph(case), artifact['rows'], []
    for changed in case.get('queries',[case['changed']]):
        sources = [graph.index[x] for x in changed]
        if not rows:
            mask = walk(graph,sources,meter)
        else:
            mask = 0
            for source in sources:
                value = walk(graph,[source],meter) if rows[source] is None else rows[source]
                mask |= value
                meter.counters['bit_operations'] += 1
        outputs.append({'affected':sorted(case['applications'][b] for b in range(len(graph.apps)) if mask & (1 << b)),
                        'mask':mask})
    return outputs

def coverage_table(case, meter):
    app_index = {name:b for b,name in enumerate(case['applications'])}
    states = {0:(0,())}
    for test in sorted(case['tests'],key=lambda t:t['id']):
        covered = sum(1 << app_index[a] for a in set(test['covers']))
        following = dict(states)
        for oldmask,(cost,ids) in states.items():
            meter.counters['cover_transitions'] += 1
            newmask = oldmask | covered
            candidate = (cost+test['cost'],tuple(sorted(ids+(test['id'],))))
            if newmask not in following or candidate < following[newmask]:
                following[newmask] = candidate
        states = following
    result = {}
    for wanted in range(1 << len(app_index)):
        if wanted == 0:
            result[wanted] = {'feasible':True,'selected':[],'cost':0}
            continue
        choices = [value for mask,value in states.items() if mask & wanted == wanted]
        if choices:
            cost,ids = min(choices)
            result[wanted] = {'feasible':True,'selected':list(ids),'cost':cost}
        else:
            result[wanted] = {'feasible':False,'selected':[],'cost':None}
    return result

def independent_cover_table(case):
    if hasattr(reference, 'efficient_cover_table'):
        return reference.efficient_cover_table(case)
    result = {}
    for mask in range(1 << len(case['applications'])):
        affected = [name for bit,name in enumerate(case['applications']) if mask & (1 << bit)]
        result[mask] = reference.minimum_cover(affected,case['tests'])[0]
    return result

def execute_successor(case, artifact, meter, audit_cover=True):
    impact = meter.call('impact_execution',impact_batch,case,artifact,meter)
    plans = meter.call('successor_construction',coverage_table,case,meter)
    if audit_cover:
        expected_plans = meter.call('result_checking',independent_cover_table,case)
        if plans != expected_plans:
            raise AssertionError('successor optimum differs from independent subset enumeration')
    answer = []
    for row,changed in zip(impact,case.get('queries',[case['changed']])):
        if artifact['certificate']['type'] in ['direct_program','partial_bfs']:
            expected,counts = meter.call('result_checking',reference.impact_bfs,{**case,'changed':changed})
            meter.counters['verifier_edge_visits'] += counts['edge_visits']
            meter.counters['verifier_node_visits'] += counts['visited_nodes']
            if row['affected'] != expected:
                raise AssertionError('fresh output differs from independent BFS')
        answer.append({'affected':row['affected'],**plans[row['mask']]})
    return answer

def mutated_case(case, treatment):
    current = copy.deepcopy(case)
    if treatment == 'graph_change':
        source = current['nodes'][0]
        for app in current['applications']:
            if [source,app] not in current['edges']:
                current['edges'].append([source,app])
        current['edges'].sort()
        current['queries'][0],current['changed'] = [source],[source]
    elif treatment == 'missing_edge':
        current['edges'] = [edge for edge in current['edges'] if edge[1] != current['applications'][-1]]
        current['queries'][0] = [current['nodes'][0]]
        current['changed'] = current['queries'][0]
    elif treatment == 'malformed_input':
        current['edges'].append(['__absent_node__',current['nodes'][0]])
    elif treatment == 'infeasible_cover':
        forbidden = current['applications'][-1]
        for test in current['tests']:
            test['covers'] = [x for x in test['covers'] if x != forbidden]
        current['queries'][0],current['changed'] = [forbidden],[forbidden]
    elif treatment == 'policy_change':
        current['tests'] = [test for test in current['tests'] if test['id'] != 't00']
    return current

def run_trial(case, method, treatment='stable', verification=True, audit_cover=True, replacement=None):
    meter = Meter()
    started_cpu,started_wall = process_time_ns(),perf_counter_ns()
    current = mutated_case(case,treatment)
    policy = 'coverage-v2' if treatment == 'policy_change' else 'coverage-v1'
    allowed = treatment != 'authority_revoked'
    cap = 2048 if treatment == 'scarce_storage' else 1048576
    available = ['walk','memo'] if treatment in ['component_outage','withheld_outage'] else ['walk','memo','scc','warshall','reverse']
    record = {'method':method,'treatment':treatment,'verification':verification,
        'case_sha256':digest(case),'world_sha256':world_digest(case),'status':'NOT_STARTED',
        'allowed':allowed,'inputs_complete':treatment != 'missing_edge','detector_acquisitions':0}
    try:
        predecessor = build_operator(case,method,meter,payload_cap=cap)
        qualification = meter.call('producer_qualification',verify_operator,case,predecessor,meter)
        if not qualification['qualified']:
            raise AssertionError('new predecessor failed qualification: '+qualification['reason'])
        produced_sha = digest(predecessor)
        producer_end = process_time_ns()
        receiver_cpu,receiver_wall = process_time_ns(),perf_counter_ns()
        exported = meter.call('export',canonical,predecessor)
        artifact = meter.call('restore',json.loads,exported)
        record['producer_artifact_sha256'],record['producer_strategy'] = produced_sha,predecessor['strategy']
        record['current_world_sha256'],record['restored_active_proofs'],record['restored_active_grants'] = world_digest(current),[],[]
        if not allowed:
            record.update(status='REFUSED_AUTHORITY',artifact_accepted=False,qualified=False,outputs=[],
                receiver_cpu_ns=process_time_ns()-receiver_cpu,receiver_wall_ns=perf_counter_ns()-receiver_wall,
                producer_cpu_ns=producer_end-started_cpu)
            return record,None,meter
        meter.call('input_validation',reference.validate_case,current)
        if treatment in ['withheld','withheld_outage']:
            artifact = None
        if treatment == 'replacement':
            if replacement is None:
                raise ValueError('replacement treatment requires separately accounted conventional artifact')
            artifact = meter.call('replacement_restore',json.loads,meter.call('replacement_export',canonical,replacement))
        if treatment == 'tampered_artifact':
            if artifact['rows']:
                target = next((i for i,v in enumerate(artifact['rows']) if v is not None),None)
                if target is not None:
                    artifact['rows'][target] ^= 1
            else:
                artifact['rows'] = [0]*len(case['nodes'])
                artifact['certificate'] = {'type':'partial_bfs'}
            record['tampered_rehashed_sha256'] = digest(artifact)
        if artifact is None:
            acceptance = {'qualified':False,'reason':'predecessor artifact deliberately withheld'}
        elif verification:
            acceptance = meter.call('receiver_revalidation',verify_operator,current,artifact,meter,policy)
        else:
            acceptance = {'qualified':True,'reason':'UNSAFE diagnostic: verification deliberately disabled'}
        record['artifact_accepted'],record['artifact_verdict'] = bool(acceptance['qualified']),acceptance
        if not acceptance['qualified']:
            artifact = build_operator(current,method,meter,available=available,payload_cap=cap,policy=policy)
            rebuilt = meter.call('receiver_revalidation',verify_operator,current,artifact,meter,policy)
            if not rebuilt['qualified']:
                raise AssertionError('rebuilt operator failed qualification')
            record['fallback'] = 'RECONSTRUCTED_AND_REQUALIFIED'
        else:
            record['fallback'] = 'NONE'
        outputs = execute_successor(current,artifact,meter,audit_cover=audit_cover)
        record.update(status='COMPLETED',qualified=True,outputs=outputs,
            consumed_artifact_sha256=digest(artifact),operator_strategy=artifact['strategy'],
            artifact_bytes=len(canonical(artifact)),successor_depends_on='impact output from consumed artifact',
            receiver_cpu_ns=process_time_ns()-receiver_cpu,receiver_wall_ns=perf_counter_ns()-receiver_wall,
            producer_cpu_ns=producer_end-started_cpu)
        return record,artifact,meter
    except reference.InvalidCase as exc:
        record.update(status='REFUSED_INPUT',qualified=False,artifact_accepted=False,outputs=[],error=str(exc))
        return record,None,meter
    except Exception as exc:
        record.update(status='FAILED',qualified=False,outputs=[],error=type(exc).__name__+': '+str(exc))
        return record,None,meter
    finally:
        record['total_cpu_ns'],record['total_wall_ns'] = process_time_ns()-started_cpu,perf_counter_ns()-started_wall
        record['counters'],record['phases'],record['decisions'] = dict(meter.counters),copy.deepcopy(meter.phases),copy.deepcopy(meter.decisions)

def deterministic_record(record):
    result = copy.deepcopy(record)
    for key in list(result):
        if key.endswith('_ns') or key == 'phases':
            result.pop(key)
    for decision in result.get('decisions',[]):
        decision.pop('decision_cpu_ns',None)
    return result
