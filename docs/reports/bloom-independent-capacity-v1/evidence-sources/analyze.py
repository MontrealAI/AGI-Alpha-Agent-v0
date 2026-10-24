# SPDX-License-Identifier: Apache-2.0
import argparse
import collections
import gzip
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from core import canonical

METHODS = ['bloom','expert','reverse']
REPS,BOOTSTRAPS,ALPHA = 3,10000,.05/3

def expected_keys(seeds):
    stress = ['graph_change','tampered_artifact','policy_change','authority_revoked','scarce_storage',
              'component_outage','withheld_outage','missing_edge','malformed_input','infeasible_cover','replacement']
    rows = [(s,m,t,r,True) for s in seeds for m in METHODS for t in ['stable','withheld'] for r in range(3)]
    rows += [(s,m,t,0,True) for s in seeds for m in METHODS for t in stress]
    rows += [(s,'walk','stable',0,True) for s in seeds]
    rows += [(s,'bloom','tampered_artifact',0,False) for s in seeds]
    return collections.Counter(rows)

def load_records(directory):
    with gzip.open(Path(directory)/'records.jsonl.gz','rt') as f:
        return [json.loads(line) for line in f if line.strip()]

def quantile(values,p):
    ordered = sorted(values)
    position = (len(ordered)-1)*p
    lo = int(position)
    hi = min(lo+1,len(ordered)-1)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(position-lo)

def ratio_interval(numerators,denominators,seed):
    logs = [math.log(a/b) for a,b in zip(numerators,denominators)]
    rng,n = random.Random(seed),len(logs)
    simulations = [sum(logs[rng.randrange(n)] for _ in range(n))/n for _ in range(BOOTSTRAPS)]
    return {'geometric_mean_ratio':math.exp(statistics.mean(logs)),
            'ci_lower':math.exp(quantile(simulations,ALPHA/2)),
            'ci_upper':math.exp(quantile(simulations,1-ALPHA/2)),
            'interval_level':1-ALPHA,'family_size':3,'bootstrap_replicates':BOOTSTRAPS,
            'independent_graph_worlds':n,'coverage':'nominal percentile-bootstrap; not finite-sample guaranteed'}

def wilson(success,total):
    if total == 0:
        return [None,None]
    z,p = 1.959963984540054,success/total
    den = 1+z*z/total
    center = (p+z*z/(2*total))/den
    half = z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [center-half,center+half]

def analyze(directory,output=None):
    directory = Path(directory)
    records = load_records(directory)
    ledger = json.loads((directory/'campaign.json').read_text())
    expected_seeds = (list(range(20001,20049)) if ledger['split']=='confirmation' else
        list(range(30001,30025)) if ledger['split']=='reproduction' else [r['seed'] for r in ledger['case_manifest']])
    observed = collections.Counter((r['seed'],r['method'],r['treatment'],r['replicate'],r['verification']) for r in records)
    integrity = {'expected_worlds':len(expected_seeds),'observed_worlds':len(set(r['seed'] for r in records)),
        'expected_trials':sum(expected_keys(expected_seeds).values()),'observed_trials':len(records),
        'exact_key_multiset':observed==expected_keys(expected_seeds),
        'ledger_matches':ledger['counts']['trials']==len(records) and ledger['counts']['worlds']==len(expected_seeds),
        'raw_digest_matches':hashlib.sha256((directory/'records.jsonl.gz').read_bytes()).hexdigest()==ledger['records_sha256']}
    if not all(integrity[k] for k in ['exact_key_multiset','ledger_matches','raw_digest_matches']):
        result = {'study':'BLOOM∞','split':ledger['split'],'worlds':integrity['observed_worlds'],'integrity':integrity,
                  'gates':{g:'INCOMPLETE_EVIDENCE' for g in ['G1','G2','G3','G4','G5']}}
        (Path(output) if output else directory/'analysis.json').write_bytes(canonical(result)+b'\n')
        return result
    methods = {}
    for method in METHODS:
        selected = [r for r in records if r['method']==method and r['verification']]
        groups = {}
        for treatment in sorted(set(r['treatment'] for r in selected)):
            rows = [r for r in selected if r['treatment']==treatment]
            groups[treatment] = {'trials':len(rows),'completed':sum(r['status']=='COMPLETED' for r in rows),
                'correct_resolution':sum(r['external_audit']['correct'] for r in rows),
                'artifact_accepted':sum(r.get('artifact_accepted',False) for r in rows),
                'reconstructed':sum(r.get('fallback')=='RECONSTRUCTED_AND_REQUALIFIED' for r in rows),
                'mean_total_cpu_ms':statistics.mean(r['total_cpu_ns'] for r in rows)/1e6,
                'mean_total_wall_ms':statistics.mean(r['total_wall_ns'] for r in rows)/1e6,
                'false_safe_queries':sum(r['external_audit'].get('false_safe_queries_against_complete_graph',0) for r in rows),
                'full_graph_queries':sum(r['external_audit'].get('queries_against_complete_graph',0) for r in rows)}
        stable = [r for r in selected if r['treatment']=='stable' and r['replicate']==0]
        methods[method] = {'contexts':groups,'stable_operator_choices':dict(collections.Counter(r.get('operator_strategy','FAILED') for r in stable)),
            'median_artifact_bytes':statistics.median(r.get('artifact_bytes',0) for r in stable),
            'failed_constructions_all_contexts':sum(r['counters']['failed_constructions'] for r in selected)}
    seeds = sorted(set(r['seed'] for r in records))
    primary,receiver,valid = {},{},True
    for method in METHODS:
        primary[method],receiver[method] = [],{}
        for seed in seeds:
            stable = [r for r in records if r['seed']==seed and r['method']==method and r['treatment']=='stable' and r['verification']]
            if len(stable)!=REPS or any(not r['external_audit']['correct'] or r['status']!='COMPLETED' for r in stable):
                valid = False
            primary[method].append(statistics.median(r['total_cpu_ns'] for r in stable))
        for treatment in ['stable','withheld']:
            receiver[method][treatment] = [statistics.median(r.get('receiver_cpu_ns',r['total_cpu_ns']) for r in records
                if r['seed']==seed and r['method']==method and r['treatment']==treatment and r['verification']) for seed in seeds]
    contrasts = {}
    for i,comparator in enumerate(['expert','reverse']):
        value = ratio_interval(primary['bloom'],primary[comparator],81320+i)
        value.update(comparator=comparator,practical_threshold=.90,
                     pass_threshold=bool(valid and value['ci_upper']<.90))
        contrasts[comparator] = value
    dependence = ratio_interval(receiver['bloom']['stable'],receiver['bloom']['withheld'],81322)
    dependence.update(practical_threshold=.80,pass_threshold=bool(valid and dependence['ci_upper']<.80),
                      interpretation='paired controlled receiver effect; predecessor cost reported separately')
    eligible = [r for r in records if r['verification'] and r['method'] in METHODS and r['external_audit']['kind']=='eligible']
    boundary = [r for r in records if r['verification'] and r['method'] in METHODS and r['external_audit']['kind']=='boundary']
    good_worlds = sum(all(r['external_audit']['correct'] and r['status']=='COMPLETED' for r in eligible if r['seed']==s) for s in seeds)
    quality_pass = all(r['external_audit']['correct'] and r['status']=='COMPLETED' for r in eligible) and all(r['external_audit']['correct'] for r in boundary)
    must_reject = [r for r in eligible if r['treatment'] in ['tampered_artifact','graph_change','policy_change','withheld','withheld_outage']]
    replacements = [r for r in eligible if r['treatment']=='replacement']
    boundaries = {'stale_or_withheld_trials':len(must_reject),
        'correct_rejections':sum(r.get('artifact_accepted') is False for r in must_reject),
        'replacement_trials':len(replacements),
        'replacement_accepted':sum(r.get('artifact_accepted') is True and r.get('fallback')=='NONE' for r in replacements)}
    boundary_pass = boundaries['stale_or_withheld_trials']==boundaries['correct_rejections'] and boundaries['replacement_trials']==boundaries['replacement_accepted']
    quality_pass = quality_pass and boundary_pass
    unsafe = [r for r in records if not r['verification']]
    ablation = [r for r in records if r['method']=='walk']
    stable_means = {m:statistics.mean(primary[m])/1e9 for m in METHODS}
    conventional = min(['expert','reverse'],key=lambda m:stable_means[m])
    saved_cpu = stable_means[conventional]-stable_means['bloom']
    sensitivities = []
    for price in [.02,.10,1.00]:
        variable = {m:stable_means[m]*price/3600 for m in METHODS}
        for hours in [0,1,8,40,160]:
            fee = hours*100
            delta = variable[conventional]-variable['bloom']
            sensitivities.append({'modeled_cpu_dollars_per_core_hour':price,'unknown_extra_engineering_hours_scenario':hours,
                'assumed_engineer_dollars_per_hour':100,'extra_fixed_cost_scenario':fee,
                'variable_cost_per_world_dollars':variable,'incremental_cpu_cost_saving_per_world_dollars':delta,
                'uses_to_recover_extra_fixed_cost':math.ceil(fee/delta) if delta>0 else None,
                'classification':'conditional assumptions; no observed prices, demand or revenues'})
    result = {'study':'BLOOM∞: verified capacity, conditional value','split':ledger['split'],
        'freeze_sha256':ledger['freeze_sha256'],'worlds':len(seeds),'trials':len(records),
        'primary_stratum':'stable, authorized, complete graph; median of3cold logical replicates/world',
        'integrity':integrity,'methods':methods,'primary_cpu_ns_by_world':primary,'primary_cpu_unit':'nanoseconds',
        'primary_mean_cpu_seconds':stable_means,'competitive_contrasts':contrasts,'artifact_dependence':dependence,
        'quality':{'eligible_trials':len(eligible),'completed_and_correct':sum(r['external_audit']['correct'] and r['status']=='COMPLETED' for r in eligible),
            'boundary_trials':len(boundary),'correct_boundary_refusals':sum(r['external_audit']['correct'] for r in boundary),
            'artifact_boundaries':boundaries,
            'worlds_all_eligible_correct':good_worlds,'world_level_wilson95':wilson(good_worlds,len(seeds))},
        'unsafe_receiver_proof_ablation':{'trials':len(unsafe),'incorrect_or_failed':sum(not r['external_audit']['correct'] for r in unsafe),
            'false_acceptances':sum(r.get('artifact_accepted',False) and not r['external_audit']['correct'] for r in unsafe)},
        'no_construction_ablation':{'trials':len(ablation),'correct':sum(r['external_audit']['correct'] for r in ablation),
            'mean_total_cpu_ms':statistics.mean(r['total_cpu_ns'] for r in ablation)/1e6},
        'economics':{'actual_cash_revenue':0,'firm_offers':0,'external_customer_acceptance':0,
            'proven_commerce':False,'full_monetary_cost_complete':False,'detector_acquisitions':0,
            'best_tested_conventional_mean':conventional,'incremental_cpu_seconds_saved_per_world':saved_cpu,
            'sensitivity':sensitivities,'unknown_costs':ledger['unknown_costs']},
        'gates':{'G1':'PENDING_INDEPENDENT_REPLAY','G2':'PASS' if quality_pass else 'FAIL',
            'G3':'PASS' if all(x['pass_threshold'] for x in contrasts.values()) and quality_pass else 'FAIL',
            'G4':'PASS' if dependence['pass_threshold'] and quality_pass else 'FAIL',
            'G5':'INCOMPLETE_COSTS_AND_DEMAND'},
        'campaign_resources':{k:ledger[k] for k in ['campaign_cpu_ns','campaign_wall_ns','peak_rss_kib','output_bytes_before_manifest','counts','records_sha256','deterministic_records_sha256']}}
    target = Path(output) if output else directory/'analysis.json'
    target.write_bytes(canonical(result)+b'\n')
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('directory')
    p.add_argument('--output')
    a = p.parse_args()
    r = analyze(a.directory,a.output)
    print(json.dumps({'split':r['split'],'worlds':r['worlds'],'gates':r['gates'],
                      'competitive':r.get('competitive_contrasts'),'dependence':r.get('artifact_dependence')},indent=2))
