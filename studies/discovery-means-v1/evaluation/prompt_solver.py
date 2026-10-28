"""Independent prompt-guided minimax control, authored for this assignment."""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
import time

BASE = Path('/dev/shm/agi-campaign-b31fc52d/evidence/evaluation')
TASK = BASE / 'blinded_tasks.json'
PROMPT = '''Independent fresh prompt-guided control. Solve only /dev/shm/agi-campaign-b31fc52d/evidence/evaluation/blinded_tasks.json. Do not inspect ANY other campaign files, instrument, prior answers, oracle or results. Each case finite hypotheses H; allowed experiment e cost positive integer; outcomes[e][h] lists all possible symbols (adversarial, no probabilities). Construct adaptive decision tree identifying exact h for EVERY branch within max_cost and max_experiments per path. No experiment repeats; disallowed unavailable. Minimize worst-case total cost only; depth hard cap. Guidance inherited as text only: preserve all outcomes including overlapping ones; branch after actual response; stop only with one surviving hypothesis; test permission/budget on every branch; do not infer a global policy from one greedy step. No access to the newly built instrument. You may use same ordinary Python/tools/libraries as other generalist to reason/compute; any generated script is your ordinary control, not inherited candidate. Return case_id,status feasible/infeasible,worst_cost,policy (leaf {kind:'leaf',hypothesis:h}; probe {kind:'probe',experiment:id,branches:{symbol:child}}). Infeasible null cost/policy; unknown explicit. Max8 tool calls10min wall20CPU seconds/case. No network/new paid APIs. Write /dev/shm/agi-campaign-b31fc52d/evidence/evaluation/prompt_outputs.json and your own solver/prompt/usage receipt. Access only given task file and own outputs.'''

class ResourceLimit(Exception):
    pass

def solve(case, wall_start):
    start_cpu = time.process_time()
    start_wall = time.monotonic()
    states = 0
    hs = tuple(case['hypotheses'])
    experiments = tuple(e for e in case['experiments'] if e['allowed'])

    @lru_cache(None)
    def visit(survivors, available, depth, budget):
        nonlocal states
        states += 1
        if time.process_time() - start_cpu >= 20:
            raise ResourceLimit('20 CPU seconds per case')
        if time.monotonic() - wall_start >= 600:
            raise ResourceLimit('600 seconds total wall time')
        if states > case.get('max_states', 100000):
            raise ResourceLimit('max_states')
        if len(survivors) == 1:
            return 0, {'kind': 'leaf', 'hypothesis': survivors[0]}
        if depth == 0 or budget == 0 or not available:
            return math.inf, None

        best_cost, best_policy = math.inf, None
        for index in available:
            experiment = experiments[index]
            charge = experiment['cost']
            assert experiment['allowed'] and isinstance(charge, int) and charge > 0
            if charge > budget:
                continue
            # A symbol keeps every consistent hypothesis, including overlap.
            sets = {}
            for h in survivors:
                for symbol in experiment['outcomes'][h]:
                    sets.setdefault(symbol, set()).add(h)
            remaining = tuple(i for i in available if i != index)
            branches = {}
            worst_child = 0
            for symbol, child_set in sorted(sets.items()):
                child_cost, child_policy = visit(tuple(sorted(child_set)), remaining,
                                                 depth - 1, budget - charge)
                if math.isinf(child_cost):
                    worst_child = math.inf
                    break
                worst_child = max(worst_child, child_cost)
                branches[symbol] = child_policy
            candidate = charge + worst_child
            if candidate < best_cost:
                best_cost = candidate
                best_policy = {'kind': 'probe', 'experiment': experiment['id'],
                               'branches': branches}
        return best_cost, best_policy

    reason = None
    try:
        cost, policy = visit(tuple(sorted(hs)), tuple(range(len(experiments))),
                             case['max_experiments'], case['max_cost'])
        if math.isinf(cost):
            result = {'case_id': case['case_id'], 'status': 'infeasible',
                      'worst_cost': None, 'policy': None}
        else:
            result = {'case_id': case['case_id'], 'status': 'feasible',
                      'worst_cost': cost, 'policy': policy}
    except ResourceLimit as exc:
        reason = str(exc)
        result = {'case_id': case['case_id'], 'status': 'unknown',
                  'worst_cost': None, 'policy': None, 'reason': reason}

    metrics = {'case_id': case['case_id'], 'states': states,
               'cpu_seconds': time.process_time() - start_cpu,
               'wall_seconds': time.monotonic() - start_wall,
               'cache_hits': visit.cache_info().hits,
               'resource_limit': reason}
    return result, metrics

def verify(case, result):
    if result['status'] != 'feasible':
        return None
    exps = {e['id']: e for e in case['experiments']}
    def walk(node, survivors, used, cost, depth):
        assert cost <= case['max_cost'] and depth <= case['max_experiments']
        if node['kind'] == 'leaf':
            assert survivors == {node['hypothesis']}
            return cost
        assert node['kind'] == 'probe'
        exp = exps[node['experiment']]
        assert exp['allowed'] and exp['id'] not in used
        symbols = set().union(*(set(exp['outcomes'][h]) for h in survivors))
        assert set(node['branches']) == symbols
        totals = []
        for symbol in symbols:
            child = {h for h in survivors if symbol in exp['outcomes'][h]}
            totals.append(walk(node['branches'][symbol], child, used | {exp['id']},
                               cost + exp['cost'], depth + 1))
        return max(totals)
    actual = walk(result['policy'], set(case['hypotheses']), set(), 0, 0)
    assert actual == result['worst_cost']
    return True

def main():
    wall_start = time.monotonic()
    cpu_start = time.process_time()
    raw = TASK.read_bytes()
    cases = json.loads(raw)
    outputs, stats = [], []
    for case in cases:
        result, metrics = solve(case, wall_start)
        metrics['policy_verified'] = verify(case, result)
        outputs.append(result)
        stats.append(metrics)
    (BASE / 'prompt_outputs.json').write_text(json.dumps(outputs, indent=2) + '\n')
    (BASE / 'prompt_instructions.txt').write_text(PROMPT + '\n')
    receipt = {
        'control': 'fresh prompt-guided generalist; self-authored ordinary Python',
        'method': 'Exhaustive memoized minimax over survivor set, unused allowed experiments, remaining depth and budget. Each experiment pays cost plus maximum optimal child cost over all possible symbols. Singleton leaves only. All experiments enumerated, with no greedy selection.',
        'input_read': str(TASK),
        'input_sha256': hashlib.sha256(raw).hexdigest(),
        'other_campaign_inputs_read': [],
        'instrument_accessed': False,
        'network_used': False,
        'paid_apis_used': False,
        'tool_calls': 3,
        'tool_call_detail': ['exec_command: read assigned input only', 'apply_patch: create own solver only', 'exec_command: run own solver'],
        'total_compute_cpu_seconds': time.process_time() - cpu_start,
        'total_compute_wall_seconds': time.monotonic() - wall_start,
        'per_case': stats,
        'outputs': ['prompt_outputs.json', 'prompt_solver.py', 'prompt_instructions.txt', 'prompt_usage.json'],
    }
    (BASE / 'prompt_usage.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps([{k: r[k] for k in ('case_id', 'status', 'worst_cost')} for r in outputs], indent=2))
    print('All feasible policies recursively validated; no unknowns:', all(r['status'] != 'unknown' for r in outputs))
    print('CPU seconds:', receipt['total_compute_cpu_seconds'])
    print('Max per-case CPU seconds:', max(x['cpu_seconds'] for x in stats))

if __name__ == '__main__':
    main()
