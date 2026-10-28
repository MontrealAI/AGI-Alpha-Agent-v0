#!/usr/bin/env python3
"""Fresh exact generalist solver: exhaustive finite-horizon robust minimax DP.

V(S,A,d)=0 for singleton S; infinity for |S|>1,d=0. Otherwise
V(S,A,d)=min_{e in A} [cost(e)+max_{o possible in S}V(S_e,o,A-e,d-1)].
S_e,o={h in S:o in outcomes[e][h]}. The recursion enumerates every root
choice and every possible adversarial observation, so induction on d proves
optimality. No budget is needed in the state: testing the global optimum
against the budget is equivalent to existence of a feasible policy.
"""
import functools
import hashlib
import json
import math
from pathlib import Path
import time

BASE=Path('/dev/shm/agi-campaign-b31fc52d/evidence/evaluation')
TASK_PATH=BASE/'blinded_tasks.json'
OUTPUT_PATH=BASE/'generalist_outputs.json'
RECEIPT_PATH=BASE/'generalist_usage_receipt.json'
PROMPT_PATH=BASE/'generalist_prompt.txt'
CPU_LIMIT_SECONDS=20.0

class LimitReached(Exception):
    pass

def solve(case):
    start_cpu=time.process_time()
    start_wall=time.monotonic()
    hypotheses=tuple(case['hypotheses'])
    experiments=tuple(e for e in case['experiments'] if e['allowed'])
    state_count=0
    choices={}
    transition_masks=[]
    for experiment in experiments:
        masks={}
        for index,hypothesis in enumerate(hypotheses):
            symbols=experiment['outcomes'][hypothesis]
            assert symbols, 'An experiment must have a possible outcome.'
            for symbol in symbols:
                masks[symbol]=masks.get(symbol,0)|(1<<index)
        transition_masks.append(masks)
    @functools.lru_cache(None)
    def value(candidates,available,depth):
        nonlocal state_count
        state_count+=1
        if time.process_time()-start_cpu>CPU_LIMIT_SECONDS:
            raise LimitReached('20 CPU seconds per case')
        if state_count>case.get('max_states',math.inf):
            raise LimitReached('case max_states')
        if candidates.bit_count()==1:
            return 0
        if depth==0 or available==0:
            return math.inf
        best=math.inf
        best_choice=None
        for experiment_index,experiment in enumerate(experiments):
            bit=1<<experiment_index
            if not available&bit:
                continue
            worst_child=0
            for symbol,symbol_mask in transition_masks[experiment_index].items():
                next_candidates=candidates&symbol_mask
                if next_candidates:
                    child=value(next_candidates,available^bit,depth-1)
                    worst_child=max(worst_child,child)
            candidate_cost=experiment['cost']+worst_child
            if candidate_cost<best:
                best=candidate_cost
                best_choice=experiment_index
        if best_choice is not None:
            choices[(candidates,available,depth)]=best_choice
        return best
    def construct(candidates,available,depth):
        if candidates.bit_count()==1:
            return {'kind':'leaf','hypothesis':hypotheses[candidates.bit_length()-1]}
        experiment_index=choices[(candidates,available,depth)]
        return {'kind':'probe','experiment':experiments[experiment_index]['id'],
                'branches':{symbol:construct(candidates&mask,available^(1<<experiment_index),depth-1)
                            for symbol,mask in transition_masks[experiment_index].items() if candidates&mask}}
    row={'case_id':case['case_id'],'status':None,'worst_cost':None,'policy':None}
    receipt={'case_id':case['case_id'],'algorithm':'exhaustive robust minimax DP'}
    try:
        all_candidates=(1<<len(hypotheses))-1
        all_available=(1<<len(experiments))-1
        optimum=value(all_candidates,all_available,case['max_experiments'])
        if optimum<=case['max_cost']:
            row.update(status='feasible',worst_cost=optimum,
                       policy=construct(all_candidates,all_available,case['max_experiments']))
        else:
            row['status']='infeasible'
        receipt['depth_constrained_optimum']=None if math.isinf(optimum) else optimum
        receipt['finite_depth_policy_exists']=not math.isinf(optimum)
        receipt['exact']=True
    except LimitReached as exc:
        row['status']='unknown'
        receipt.update(exact=False,limit_reason=str(exc))
    receipt.update(states_evaluated=state_count,cache_hits=value.cache_info().hits,
                   cpu_seconds=time.process_time()-start_cpu,wall_seconds=time.monotonic()-start_wall)
    return row,receipt

def validate_policy(case,row):
    """Independent policy replay using explicit hypothesis sets, no DP table."""
    if row['status']!='feasible':
        assert row['worst_cost'] is None and row['policy'] is None
        return None
    experiment_by_id={e['id']:e for e in case['experiments']}
    def visit(node,possible,used,cost,depth):
        assert cost<=case['max_cost'] and depth<=case['max_experiments']
        if node['kind']=='leaf':
            assert possible=={node['hypothesis']}
            return cost
        assert node['kind']=='probe'
        experiment_id=node['experiment']
        assert experiment_id not in used
        experiment=experiment_by_id[experiment_id]
        assert experiment['allowed']
        possible_observations=set().union(*(set(experiment['outcomes'][h]) for h in possible))
        assert set(node['branches'])==possible_observations
        return max(visit(node['branches'][symbol],
                         {h for h in possible if symbol in experiment['outcomes'][h]},
                         used|{experiment_id},cost+experiment['cost'],depth+1)
                   for symbol in possible_observations)
    actual=visit(row['policy'],set(case['hypotheses']),set(),0,0)
    assert actual==row['worst_cost']
    return actual

def main():
    wall_start=time.monotonic()
    cpu_start=time.process_time()
    tasks_bytes=TASK_PATH.read_bytes()
    cases=json.loads(tasks_bytes)
    rows=[]
    receipts=[]
    for case in cases:
        row,receipt=solve(case)
        receipt['policy_replay_worst_cost']=validate_policy(case,row)
        receipt['policy_validation']='passed' if row['status']=='feasible' else 'not_applicable'
        rows.append(row)
        receipts.append(receipt)
    OUTPUT_PATH.write_text(json.dumps(rows,indent=2)+'\n')
    receipt={
        'control':'fresh hosted generalist; research comparison only',
        'input_path':str(TASK_PATH),
        'input_sha256':hashlib.sha256(tasks_bytes).hexdigest(),
        'solver_path':str(Path(__file__)),
        'solver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'prompt_path':str(PROMPT_PATH),
        'prompt_sha256':hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest(),
        'output_path':str(OUTPUT_PATH),
        'output_sha256':hashlib.sha256(OUTPUT_PATH.read_bytes()).hexdigest(),
        'access_statement':'Read only blinded_tasks.json and own solver/prompt/output paths; no instrument, oracle, other campaign files, prior answers, network, or paid APIs accessed.',
        'dependencies':'Python standard library only',
        'algorithm_proof':'Induction on remaining depth: each possible root experiment is enumerated; every possible observation is evaluated; adversarial branches use maximum, root choices use minimum. Used experiments are removed. Singleton states are exact-identification leaves. Compare globally minimum worst-case cost to max_cost.',
        'resource_limits':{'tool_call_limit':8,'cpu_seconds_per_case':20,'wall_seconds':600},
        'tool_calls_used':2,
        'tool_call_accounting':'Two functions.exec invocations, each making one exec_command: input read; write solver/prompt then run. Collaboration message excluded.',
        'model_token_usage':'not exposed to subagent',
        'total_solver_cpu_seconds':time.process_time()-cpu_start,
        'total_solver_wall_seconds':time.monotonic()-wall_start,
        'cases':receipts,
    }
    RECEIPT_PATH.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'outputs':str(OUTPUT_PATH),'receipt':str(RECEIPT_PATH),'results':[{k:r[k] for k in ('case_id','status','worst_cost')} for r in rows],'total_solver_cpu_seconds':receipt['total_solver_cpu_seconds'],'total_states':sum(r['states_evaluated'] for r in receipts)},indent=2))
if __name__=='__main__':
    main()
