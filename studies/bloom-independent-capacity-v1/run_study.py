# SPDX-License-Identifier: Apache-2.0
import argparse
import gzip
import hashlib
import json
import os
import platform
import random
import resource
import sys
from pathlib import Path
from time import perf_counter_ns,process_time_ns
from core import Meter,build_operator,canonical,deterministic_record,digest,mutated_case,reference,run_trial,verify_operator
from generate import make_case

ROOT = Path(__file__).resolve().parent
SPLITS = {'development':list(range(101,113)), 'confirmation':list(range(20001,20049)),
          'reproduction':list(range(30001,30025))}
METHODS = ['bloom','expert','reverse']
STRESS = ['graph_change','tampered_artifact','policy_change','authority_revoked','scarce_storage',
          'component_outage','withheld_outage','missing_edge','malformed_input','infeasible_cover']

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(canonical(value)+b'\n')

def check_freeze():
    freeze_path = ROOT/'protocol'/'FREEZE.json'
    if not freeze_path.exists():
        raise RuntimeError('confirmatory execution requires a persisted pre-run FREEZE.json')
    freeze = json.loads(freeze_path.read_text())
    for item in freeze['files']:
        data = (ROOT/item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise RuntimeError('frozen source changed: '+item['path'])
    return hashlib.sha256(freeze_path.read_bytes()).hexdigest()

def expected_outputs(case):
    reference.validate_case(case)
    cache,result = {},[]
    for changed in case.get('queries',[case['changed']]):
        affected,_ = reference.impact_bfs({**case,'changed':changed})
        key = tuple(affected)
        if key not in cache:
            cache[key] = reference.minimum_cover(affected,case['tests'])[0]
        result.append({'affected':affected,**cache[key]})
    return result

def audit_record(case,record,oracle):
    treatment = record['treatment']
    if treatment == 'authority_revoked':
        return {'correct':record['status']=='REFUSED_AUTHORITY','kind':'boundary','expected':'REFUSED_AUTHORITY'}
    if treatment == 'malformed_input':
        return {'correct':record['status']=='REFUSED_INPUT','kind':'boundary','expected':'REFUSED_INPUT'}
    expected = oracle[treatment if treatment in ['graph_change','missing_edge','policy_change','infeasible_cover'] else 'stable']
    correct = record['status']=='COMPLETED' and record['outputs']==expected
    result = {'correct':correct,'kind':'out_of_scope' if treatment=='missing_edge' else 'eligible',
              'expected_output_sha256':digest(expected),'actual_output_sha256':digest(record.get('outputs',[]))}
    if treatment == 'missing_edge':
        full = oracle['stable']
        pairs = list(zip(record.get('outputs',[]),full))
        result['false_safe_queries_against_complete_graph'] = sum(bool(set(w['affected'])-set(a['affected'])) for a,w in pairs)
        result['queries_against_complete_graph'] = len(full)
        result['challenge_design'] = 'deliberately remove all incoming edges to last app; source0 originally has direct edge'
    return result

def run_campaign(split,output,seeds=None):
    output = Path(output).resolve()
    if output.exists():
        raise RuntimeError('output directory already exists; preserve it and choose a new name')
    freeze_sha = None if split == 'development' else check_freeze()
    output.mkdir(parents=True)
    chosen = SPLITS[split] if seeds is None else seeds
    if any(s not in SPLITS[split] for s in chosen):
        raise ValueError('seed outside split')
    begin_cpu,begin_wall = process_time_ns(),perf_counter_ns()
    budget_ns = 1200*10**9
    prior_cpu_ns = 0
    prior_receipts = []
    for base in [ROOT/'development',ROOT/'results']:
        if not base.exists():
            continue
        for receipt in base.rglob('campaign.json'):
            value = json.loads(receipt.read_text())
            prior_cpu_ns += value.get('campaign_cpu_ns',0)
            prior_receipts.append({'path':str(receipt.relative_to(ROOT)),'cpu_ns':value.get('campaign_cpu_ns',0)})
    if prior_cpu_ns >= budget_ns:
        raise RuntimeError('cumulative measured scientific CPU budget exhausted')
    counts = {'trials':0,'worlds':0,'external_audit_cpu_ns':0,'replacement_cpu_ns':0,'failures':0,
              'detector_acquisitions':0,'actual_cash_revenue':0,'new_paid_resource_charges':0}
    deterministic_sha = hashlib.sha256()
    raw_path = output/'records.jsonl.gz'
    cases_manifest,artifacts_manifest = [],[]
    with raw_path.open('wb') as stream, gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as raw:
        for seed in chosen:
            case = make_case(seed)
            write_json(output/'cases'/f'{seed}.json',case)
            cases_manifest.append({'seed':seed,'sha256':digest(case),'topology':case['topology'],
                                   'nodes':len(case['nodes']),'queries':len(case['queries'])})
            oracle_begin = process_time_ns()
            oracle = {t:expected_outputs(mutated_case(case,t)) for t in ['stable','graph_change','missing_edge','policy_change','infeasible_cover']}
            counts['external_audit_cpu_ns'] += process_time_ns()-oracle_begin
            replacement_meter = Meter()
            replace_start = process_time_ns()
            replacement = build_operator(case,'expert',replacement_meter)
            replace_check = verify_operator(case,replacement,replacement_meter)
            replace_cpu = process_time_ns()-replace_start
            if not replace_check['qualified']:
                raise RuntimeError('conventional replacement failed qualification')
            counts['replacement_cpu_ns'] += replace_cpu
            write_json(output/'replacements'/f'{seed}.json',{'artifact':replacement,'qualification':replace_check,
                       'cpu_ns':replace_cpu,'counters':replacement_meter.counters,'phases':replacement_meter.phases})
            jobs = [(m,t,r,True) for m in METHODS for t in ['stable','withheld'] for r in range(3)]
            jobs += [(m,t,0,True) for m in METHODS for t in STRESS+['replacement']]
            jobs += [('walk','stable',0,True),('bloom','tampered_artifact',0,False)]
            random.Random(seed+918273).shuffle(jobs)
            for order,(method,treatment,rep,verified) in enumerate(jobs):
                if prior_cpu_ns+process_time_ns()-begin_cpu > budget_ns:
                    raise RuntimeError('predeclared CPU budget exhausted; partial records retained')
                record,artifact,meter = run_trial(case,method,treatment,verification=verified,replacement=replacement)
                record.update(seed=seed,split=split,topology=case['topology'],nodes=len(case['nodes']),
                              query_count=len(case['queries']),replicate=rep,run_order=order,
                              freeze_sha256=freeze_sha)
                if treatment == 'replacement':
                    record['replacement_receipt'] = f'replacements/{seed}.json'
                    record['replacement_attributable_cpu_ns'] = replace_cpu
                    record['attribution_note'] = 'one actual measured replacement creation reused across counterfactual arms; not added repeatedly to actual research ledger'
                audit_start = process_time_ns()
                record['external_audit'] = audit_record(case,record,oracle)
                counts['external_audit_cpu_ns'] += process_time_ns()-audit_start
                if not record['external_audit']['correct'] and verified:
                    counts['failures'] += 1
                deterministic = deterministic_record(record)
                deterministic.pop('replacement_attributable_cpu_ns',None)
                deterministic_sha.update(canonical(deterministic)+b'\n')
                raw.write(canonical(record)+b'\n')
                counts['trials'] += 1
                if artifact is not None and rep == 0 and treatment in ['stable','graph_change','tampered_artifact'] and verified:
                    name = f'{seed}-{method}-{treatment}.json'
                    write_json(output/'operators'/name,artifact)
                    artifacts_manifest.append({'path':'operators/'+name,'sha256':digest(artifact),'bytes':len(canonical(artifact))})
                if counts['trials'] % 100 == 0:
                    raw.flush()
                    print(json.dumps({'split':split,'trials':counts['trials'],'last_seed':seed,
                                      'cpu_seconds':round((process_time_ns()-begin_cpu)/1e9,3)}),flush=True)
            counts['worlds'] += 1
    elapsed_cpu,elapsed_wall = process_time_ns()-begin_cpu,perf_counter_ns()-begin_wall
    total_bytes = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if total_bytes > 256*1024**2:
        raise RuntimeError('predeclared evidence storage budget exceeded')
    ledger = {'split':split,'freeze_sha256':freeze_sha,'counts':counts,'campaign_cpu_ns':elapsed_cpu,
        'campaign_wall_ns':elapsed_wall,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'output_bytes_before_manifest':total_bytes,'deterministic_records_sha256':deterministic_sha.hexdigest(),
        'records_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),'python':sys.version,
        'platform':platform.platform(),'cpu_count':os.cpu_count(),'case_manifest':cases_manifest,
        'operator_manifest':artifacts_manifest,'host_scope':'one inherited Linux runtime; no isolated hardware claim',
        'unknown_costs':['human authoring','model/service authoring','hardware ownership','integration maintenance'],
        'research_budget':{'cpu_cap_ns':budget_ns,'prior_measured_campaign_cpu_ns':prior_cpu_ns,
                           'cumulative_measured_campaign_cpu_ns':prior_cpu_ns+elapsed_cpu,'prior_receipts':prior_receipts,
                           'scope':'completed measured scientific campaigns in study development/results; authoring and reporting compute separately reported, not a full monetary budget'},
        'cash_revenue':0,'firm_offers':0,'independently_supported_demand':0,'physical_detector_acquisitions':0}
    write_json(output/'campaign.json',ledger)
    print(json.dumps({'completed':split,'worlds':counts['worlds'],'trials':counts['trials'],'failures':counts['failures'],
                      'cpu_seconds':elapsed_cpu/1e9,'bytes':total_bytes,'deterministic_sha256':deterministic_sha.hexdigest()}),flush=True)
    return ledger

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--split',choices=list(SPLITS),required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--seeds',help='comma-separated development seeds only')
    a = p.parse_args()
    if a.seeds and a.split != 'development':
        p.error('custom seed subsets allowed only for development')
    run_campaign(a.split,a.output,None if not a.seeds else list(map(int,a.seeds.split(','))))
