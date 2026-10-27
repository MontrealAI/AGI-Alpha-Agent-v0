#!/usr/bin/env python3
"""Read-only independent paired analysis of frozen v2 stress/capacity results.
No simulator import and no economic seed execution. These are conditional stresses,
not an empirical sample of markets and not a replacement for primary confirmation.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
from audit_outputs import Checks, EXPECTED_PROTOCOL, ci, json_rows, read_json, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():raise FileExistsError('Refusing to overwrite retained sensitivity audit')
    root=args.results
    manifest=read_json(root/'protocol_freeze.json')
    selected=read_json(root/'selected_policies.json')['policies']['central']
    checks=Checks()
    checks.eq('frozen_protocol',sha(root/'protocol_freeze.json'),EXPECTED_PROTOCOL,'protocol')
    cases=dict(manifest['sensitivity_cases']);seeds=manifest['sensitivity_seeds']
    index={};groups=defaultdict(list)
    for r in json_rows(root/'sensitivity_runs.jsonl'):
        identity=(r['case'],r['arm'],r['seed'])
        checks.check('unique_stress_identity',identity not in index,list(identity))
        index[identity]=r;groups[identity[:2]].append(r)
        is_rd=r['case'].endswith('-optional-invest')
        expected={**selected,'name':selected['name']+('-optional-invest' if is_rd else '-retain'),
                  'invest':is_rd,'retain_skills':True}
        checks.eq('declared_conditional_policy',r['policy'],expected,list(identity))
    expected={(case+'-'+suffix,arm,seed) for case in cases for arm,suffix in
              [('beta','retain'),('network','retain'),('network','optional-invest')] for seed in seeds}
    checks.eq('complete_stress_set',sorted(index),sorted(expected),'stress')
    official={(r['case'],r['arm']):r for r in read_json(root/'sensitivity.json')}
    paired={};economic={}
    for case in cases:
        pairs={}
        for label,(ta,ts,ca,cs) in {
             'retention_network_minus_beta':('network','retain','beta','retain'),
             'optional_rd_minus_retention_only':('network','optional-invest','network','retain'),
             'network_with_optional_rd_minus_beta':('network','optional-invest','beta','retain')}.items():
            pairs[label]={}
            for metric in ('profit','accepted_useful'):
                ds=[]
                for seed in seeds:
                    t=index[case+'-'+ts,ta,seed];c=index[case+'-'+cs,ca,seed]
                    ds.append(t['profit']-c['profit'] if metric=='profit' else
                              t['stats'].get(metric,0)-c['stats'].get(metric,0))
                pairs[label][metric]=ci(ds)
        paired[case]=pairs
        economic[case]={}
        for arm,suffix in [('beta','retain'),('network','retain'),('network','optional-invest')]:
            rows=groups[case+'-'+suffix,arm]
            d={k:ci([r[k] for r in rows]) for k in ['profit','collections','expenses','retention_cost','investment_cost','retention_count','investment_count']}
            d['accepted_useful']=ci([r['stats'].get('accepted_useful',0) for r in rows])
            d['cash_shortfalls']=sum(bool(r['stats'].get('cash_shortfall')) for r in rows)
            d['n']=len(rows)
            for k in ['profit','accepted_useful','investment_count','retention_count']:
                for field in ['n','mean','lower','upper']:
                    checks.near('published_stress_summary',official[case+'-'+suffix,arm][k][field],d[k][field],[case,arm,suffix,k,field])
            economic[case][arm+'-'+suffix]=d
    capacity=read_json(root/'capacity_policy.json')
    menu=('central-reference','validators-1','validators-4','quota-quarter','compute-double','agents-double','scale-complete-double')
    capacity_replay={}
    for arm in ('beta','network'):
        train={case:statistics.fmean(index[case+'-retain',arm,s]['profit'] for s in seeds[:8]) for case in menu}
        winner=max((v,k) for k,v in train.items())[1]
        checks.eq('capacity_selection',capacity['choices'][arm]['selected'],winner,arm)
        gains=[index[winner+'-retain',arm,s]['profit']-index['central-reference-retain',arm,s]['profit'] for s in seeds[8:]]
        result={'selected':winner,'selection_means':train,'fresh_paired_profit':ci(gains),
                'fresh_mean_profit':ci([index[winner+'-retain',arm,s]['profit'] for s in seeds[8:]])}
        for field in ('n','mean','lower','upper'):
            checks.near('capacity_fresh_pair',capacity['choices'][arm]['paired_profit_gain'][field],result['fresh_paired_profit'][field],[arm,field])
        capacity_replay[arm]=result
    # Report a tested demand table, never interpolate an exact break-even market.
    demand=[]
    for case,changes in cases.items():
        if case.startswith('leads-'):
            demand.append({'leads_per_week':changes['leads_per_week'],'case':case,
                           'beta':economic[case]['beta-retain'],'network_retention':economic[case]['network-retain']})
    demand.sort(key=lambda x:x['leads_per_week'])
    report={'schema':'beyond-beta.postfreeze-stress-audit/1','source_kind':'independent-analysis-of-simulated-stresses',
      'created_utc':datetime.now(timezone.utc).isoformat(),'audit_source_sha256':sha(Path(__file__)),
      'checks':checks.result(),'cases':len(cases),'rows':len(index),'paired':paired,'economic':economic,
      'capacity_split_replay':capacity_replay,'tested_demand_table':demand,
      'positive_retention_profit_intervals':[k for k,v in paired.items() if v['retention_network_minus_beta']['profit']['lower']>0],
      'negative_retention_profit_intervals':[k for k,v in paired.items() if v['retention_network_minus_beta']['profit']['upper']<0],
      'positive_optional_rd_profit_intervals':[k for k,v in paired.items() if v['optional_rd_minus_retention_only']['profit']['lower']>0],
      'negative_optional_rd_profit_intervals':[k for k,v in paired.items() if v['optional_rd_minus_retention_only']['profit']['upper']<0],
      'consumed_result_manifest':{f:{'bytes':(root/f).stat().st_size,'sha256':sha(root/f)} for f in
        ['protocol_freeze.json','selected_policies.json','sensitivity_runs.jsonl','sensitivity.json','capacity_policy.json']},
      'limitations':['Every stress forces retention on; it is distinct from the selected central delivery-only primary policy.',
        'Intervals quantify conditional Monte Carlo variation across 16 worlds; the 57 cases are assumption tests, not independent empirical market discoveries.',
        'No multiplicity adjustment is applied; isolated positive intervals identify conditional modeled regions and do not rescue primary confirmation.',
        'Capacity selection uses eight worlds and testing eight different worlds from the same prespecified stress set; this is an initial menu, not globally optimal dynamic scaling.',
        'Sensitivity results retain aggregate financial fields, not full transaction ledgers; the complete ledger reconciliation audit covers the 768 primary runs.']}
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'report':str(args.out),'passed':checks.failed_count==0,'checks':sum(checks.counts.values()),'failures':checks.failed_count,'rows':len(index)}))
    if checks.failed_count:raise SystemExit(2)


if __name__=='__main__':main()
