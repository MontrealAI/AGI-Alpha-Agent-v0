#!/usr/bin/env python3
"""Reporting-only commercial-core extraction from frozen v2 evidence.

Reads the retained confirmation ledgers inside an evidence ZIP. Does not import
or execute simulator code, change policy, or run new seeds. The useful-receipts
filter and additional planning buffer are postconfirmation reporting metrics.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import zipfile
from audit_outputs import Checks, EXPECTED_PROTOCOL, ci, read_json, sha


def money(x):return round(float(x)*100)


def descriptives(values):
    return {'count':len(values),'mean':statistics.fmean(values) if values else None,
            'median':statistics.median(values) if values else None,
            'min':min(values) if values else None,'max':max(values) if values else None}


def calculate(study, archive):
    results=study/'results';checks=Checks()
    manifest=read_json(results/'protocol_freeze.json')
    checks.eq('frozen_protocol',sha(results/'protocol_freeze.json'),EXPECTED_PROTOCOL,'protocol')
    for name,digest in manifest['source_hashes'].items():
        checks.eq('frozen_source_unchanged',sha(study/name),digest,name)
    policies=read_json(results/'selected_policies.json')['policies']
    rows=[json.loads(x) for x in (results/'confirmation_runs.jsonl').read_text().splitlines()]
    beta={(r['scenario'],r['seed']):r for r in rows if r['arm']=='beta'}
    audit=read_json(results/'output_audit.json')
    audit_index={(r['scenario'],r['seed']):r for r in audit['ledger_reconciliation'] if r['arm']=='beta'}
    references=read_json(study/'sources/workload_catalog.json')['human_reference_USD']
    member='results/confirmation_ledgers.jsonl.gz'
    expected_archive_member=audit['consumed_result_manifest']['confirmation_ledgers.jsonl.gz']
    parsed={};pooled=defaultdict(lambda:defaultdict(list));ledger_rows=0
    with zipfile.ZipFile(archive) as z:
        info=z.getinfo(member)
        checks.eq('archived_ledger_size',info.file_size,expected_archive_member['bytes'],member)
        h=hashlib.sha256()
        with z.open(member) as compressed:
            for block in iter(lambda:compressed.read(1024*1024),b''):h.update(block)
        checks.eq('archived_ledger_hash',h.hexdigest(),expected_archive_member['sha256'],member)
        with z.open(member) as compressed, gzip.GzipFile(fileobj=compressed) as decompressed:
            for line in io.TextIOWrapper(decompressed,encoding='utf-8'):
                ledger_rows+=1
                arm=re.search(r'"arm"\s*:\s*"([^"]+)"',line[:200])
                if arm is None:raise ValueError('Missing ledger identity header')
                if arm.group(1)!='beta':continue
                full=json.loads(line);ident=(full['scenario'],full['seed']);r=beta[ident]
                checks.check('unique_beta_ledger',ident not in parsed,list(ident))
                scenario=manifest['scenarios'][ident[0]];policy=policies[ident[0]]
                outcomes={o['job']:o for o in full['outcomes']}
                useful=sum(bool(o['useful']) for o in outcomes.values())
                checks.eq('useful_outcomes',useful,r['stats'].get('accepted_useful',0),list(ident))
                useful_receipts=all_receipts=excluded_receipts=0
                useful_receipt_count=receipt_count=0
                for t in full['ledger']:
                    if t['kind']!='collection':continue
                    receipt_count+=1;amount=t['amount_cents'];all_receipts+=amount
                    job=int(t['key']);o=outcomes.get(job)
                    checks.check('receipt_has_completed_job',o is not None,[*ident,job])
                    pooled[ident[0]]['collected_receipt_amounts'].append(amount/100)
                    if o and o['useful']:
                        useful_receipts+=amount;useful_receipt_count+=1
                        pooled[ident[0]]['useful_receipt_amounts'].append(amount/100)
                    else:excluded_receipts+=amount
                checks.eq('collections_reconcile',all_receipts,money(r['collections']),list(ident))
                checks.eq('receipt_filter_partition',useful_receipts+excluded_receipts,all_receipts,list(ident))
                for o in outcomes.values():
                    human=references[o['depth']-1]*scenario['human_price_factor']
                    pooled[ident[0]]['completed_job_human_references'].append(human)
                    pooled[ident[0]]['completed_job_quotes'].append(o['price'])
                    pooled[ident[0]]['completed_job_quote_ratios'].append(o['price']/human)
                    if o['useful']:
                        pooled[ident[0]]['useful_job_human_references'].append(human)
                        pooled[ident[0]]['useful_job_quotes'].append(o['price'])
                        pooled[ident[0]]['useful_job_quote_ratios'].append(o['price']/human)
                a=audit_index[ident]
                unexpensed_closing=money(r['closing_obligations'])-a['unpaid_accrued_cents']
                checks.check('nonnegative_unexpensed_closing',unexpensed_closing>=0,list(ident))
                filtered=(useful_receipts-money(r['expenses'])-unexpensed_closing)/100
                checks.near('filtered_surplus_identity',filtered,r['profit']-excluded_receipts/100,list(ident))
                checks.check('filtered_surplus_no_greater_than_profit',filtered<=r['profit']+.005,list(ident))
                floor=policy['reserve_weeks']*(105+30*scenario['validator_slots']+40*scenario['agents']+35)
                above=max(0,r['available_cash']-r['seed_capital'])
                buffered=max(0,min(r['profit'],r['available_cash']-r['seed_capital'])-floor)
                ww=full['weekly'];terminal_protected=ww[-1]['committed']
                checks.near('available_cash_reconciles',r['available_cash'],
                            max(0,r['cash']-terminal_protected-a['unpaid_accrued_cents']/100),list(ident),tolerance=.005)
                checks.eq('Beta_has_no_retention_cost',money(r['cost_books']['retention']),0,list(ident))
                checks.eq('Beta_has_no_separate_rd_cost',money(r['cost_books']['investment']),0,list(ident))
                values={
                    'accepted_useful':useful,'useful_throughput_per_104_week':useful/scenario['weeks'],
                    'useful_throughput_per_120_week':useful/(scenario['weeks']+scenario['runoff']),
                    'orders':r['stats'].get('orders',0),'completed_jobs':len(outcomes),
                    'collected_jobs':receipt_count,'useful_collected_jobs':useful_receipt_count,
                    'false_passes':r['stats'].get('false_passes',0),'late':r['stats'].get('late',0),
                    'collections':r['collections'],'useful_collections_only':useful_receipts/100,
                    'excluded_nonuseful_collections':excluded_receipts/100,
                    'A_job_cost':r['cost_books']['job'],'common_cost':r['cost_books']['common'],
                    'all_expenses':r['expenses'],'closing_obligations':r['closing_obligations'],
                    'closing_unexpensed_obligations':unexpensed_closing/100,
                    'closing_accrued_unpaid_cost':a['unpaid_accrued_cents']/100,
                    'profit':r['profit'],'useful_collections_only_surplus':filtered,
                    'available_cash':r['available_cash'],'cash':r['cash'],
                    'spendable_cash_above_initial_seed':above,
                    'operating_planning_floor':floor,
                    'available_after_seed_and_operating_floor':buffered,
                    'min_cash':r['min_cash'],'min_available_cash':min(w['available'] for w in ww),
                    'peak_protected_cash':max(w['committed'] for w in ww),
                    'terminal_protected_cash':terminal_protected,
                    'peak_simultaneous_active_jobs':max(w['jobs'] for w in ww),
                    'peak_cash_draw_from_initial_seed':max(0,r['seed_capital']-r['min_cash']),
                    'max_weekly_input_m':r['max_input_m'],'max_weekly_output_m':r['max_output_m'],
                    'cash_shortfall':int(bool(r['stats'].get('cash_shortfall')))}
                parsed[ident]=values
    expected={(s,n) for s in manifest['scenarios'] for n in manifest['confirmation_seeds']}
    checks.eq('all_192_Beta_ledgers',sorted(parsed),sorted(expected),'ledgers')
    checks.eq('complete_archive_row_count',ledger_rows,768,'ledgers')
    scenarios={}
    for name,scenario in manifest['scenarios'].items():
        worlds=[parsed[name,n] for n in manifest['confirmation_seeds']]
        metrics={k:ci([w[k] for w in worlds]) for k in worlds[0]}
        b=[r for (s,n),r in beta.items() if s==name]
        order_count=sum(r['stats'].get('orders',0) for r in b)
        order_ratio=sum(r['mean_price_ratio']*r['stats'].get('orders',0) for r in b)/order_count
        count_useful=sum(w['accepted_useful'] for w in worlds)
        count_useful_collected=sum(w['useful_collected_jobs'] for w in worlds)
        complete=sum(w['all_expenses']+w['closing_unexpensed_obligations'] for w in worlds)
        sample=read_json(results/'samples'/f'{name}-beta.json')
        orders=[e for e in sample['events'] if e['kind']=='order']
        scenarios[name]={
            'n_worlds':len(worlds),'arm':'beta','metrics':metrics,
            'pricing':{'selected_policy':policies[name],
                'selection_basis':'32-policy network family, selected before confirmation; applied unchanged to Beta, not independently optimized for Beta',
                'experimental_retention_enabled':False,'optional_new_rd_enabled':False,
                'order_weighted_human_price_ratio':order_ratio,'order_count_across_worlds':order_count,
                'completed_job_quotes':{'basis':'All completed-job outcomes in the 64 Beta worlds; quotes were offered for jobs, not necessarily collected',
                    'quoted_price_USD':descriptives(pooled[name]['completed_job_quotes']),
                    'human_reference_USD':descriptives(pooled[name]['completed_job_human_references']),
                    'human_reference_basis':'Derived from recorded depth and frozen rate/hour rule; not measured human-only effort',
                    'quoted_price_to_reference_ratio':descriptives(pooled[name]['completed_job_quote_ratios'])},
                'useful_delivered_job_quotes':{'basis':'All useful, on-time completed-job outcomes in the 64 Beta worlds; recorded quoted selling prices, not necessarily collected',
                    'quoted_price_USD':descriptives(pooled[name]['useful_job_quotes']),
                    'human_reference_USD':descriptives(pooled[name]['useful_job_human_references']),
                    'human_reference_basis':'Derived from recorded depth and frozen rate/hour rule; not measured human-only effort',
                    'quoted_price_to_reference_ratio':descriptives(pooled[name]['useful_job_quote_ratios'])},
                'representative_order_events':{'seed':770001,'basis':'Directly recorded order events in the first prespecified Beta sample only',
                    'quoted_price_USD':descriptives([o['price'] for o in orders]),
                    'human_reference_USD':descriptives([o['human_reference'] for o in orders])},
                'collection_receipt_amounts_USD':descriptives(pooled[name]['collected_receipt_amounts']),
                'useful_collection_receipt_amounts_USD':descriptives(pooled[name]['useful_receipt_amounts'])},
            'pooled_ratios':{
                'basis':'Sums over all64worlds divided by outcome counts; descriptive derived ratios, not matched-job margins or prices',
                'collected_USD_per_useful_outcome':sum(w['collections'] for w in worlds)/count_useful,
                'useful_collections_USD_per_useful_outcome':sum(w['useful_collections_only'] for w in worlds)/count_useful,
                'full_cost_USD_per_useful_outcome':complete/count_useful,
                'useful_collections_USD_per_useful_collected_job':sum(w['useful_collections_only'] for w in worlds)/count_useful_collected,
                'useful_receipt_only_surplus_USD_per_useful_outcome':sum(w['useful_collections_only_surplus'] for w in worlds)/count_useful},
            'capacity_and_capital':{
                'initial_seed_USD':scenario['seed_capital'],'historical_setup_USD':scenario['setup_cost'],
                'selling_weeks':scenario['weeks'],'runoff_weeks':scenario['runoff'],
                'agents':scenario['agents'],'validator_slots':scenario['validator_slots'],
                'weekly_input_quota_M':scenario['quota_input_m'],'weekly_output_quota_M':scenario['quota_output_m'],
                'policy_reserve_weeks':policies[name]['reserve_weeks'],
                'reporting_operating_floor_USD':metrics['operating_planning_floor']['mean'],
                'collection_delay_weeks':scenario['collection_delay'],
                'minimum_required_seed':'Not identified; minimum path cash and peak draw are outcomes, not counterfactual seed requirements'},
            'world_values':[{'seed':seed,**parsed[name,seed]} for seed in manifest['confirmation_seeds']]}
    stress=read_json(results/'sensitivity.json')
    capital_tests=[]
    for case,seed in [('seed-10000-retain',10000),('seed-25000-retain',25000),('central-reference-retain',60000)]:
        r=next(x for x in stress if x['case']==case and x['arm']=='beta')
        capital_tests.append({'case':case,'seed_USD':seed,'n_worlds':r['profit']['n'],
                              'profit':r['profit'],'cash_shortfall':r['cash_shortfall'],
                              'scope':'Central stress priors at frozen central price; not all-scenario minimum-capital validation'})
    return {'schema':'beyond-beta.commercial-core-report/1','source_kind':'reporting-only-derived-simulation-results',
        'created_utc':datetime.now(timezone.utc).isoformat(),'reporting_amendment_date':'2026-10-27',
        'reporting_priority':'Commercial Beta profitability is primary; optional retained Alpha is a secondary incremental decision',
        'scientific_protocol_changed':False,'new_economic_seeds_run':False,
        'protocol_sha256':EXPECTED_PROTOCOL,'analysis_source_sha256':sha(Path(__file__)),
        'checks':checks.result(),'scenarios':scenarios,'seed_sensitivity':capital_tests,
        'definitions':{
            'useful_outcome':'Simulated delivered, on-time, truly correct outcome; latent model truth, not empirical provider or customer quality validation',
            'useful_collections_only_surplus':'Collections joined to useful outcomes minus ALL accrued enterprise expenses and all unexpensed closing obligations; all costs of false passes, failures and refunds remain',
            'spendable_cash_above_initial_seed':'max(0,reported available_cash-initial seed); cash above original seed before an additional operating planning floor, not profit or fully unreserved investment funds',
            'available_after_seed_and_operating_floor':'max(0,min(profit,available_cash-initial_seed)-reserve_weeks*(105+30*validators+40*agents+35)); reporting-only buffer, not another expense',
            'throughput':'Useful outcomes divided by fixed104selling weeks or full120week horizon; not annualized observed production or claimed steady-state capacity',
            'Monte_Carlo_intervals':'Pointwise normal95% world-level intervals conditional on frozen assumptions; no empirical market confidence or multiple-comparison correction'},
        'source_reference':{'human_scope_USD':references,'source':'sources/calibration.json and sources/workload_catalog.json',
            'limitations':['Observed professional-service rates with assumed team hours, not observed matched project quotations or verified human-only effort.',
                           'Frontier model task quality, fully automated acceptance, demand and buyer trust are scenario assumptions without empirical quality-floor validation.',
                           'Prices were selected on the network policy family and tested on Beta, not independently optimized for Beta.',
                           'The useful-receipt filter is a reporting sensitivity over retained outcomes, not a new scientific freeze or live customer measurement.',
                           'Pooled ratios mix scopes, failures and common costs; they are not matched job margins.']},
        'input_manifest':{
            'evidence_zip':{'filename':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive)},
            'ledger_member':{'name':member,**expected_archive_member},
            **{name:{'bytes':(results/name).stat().st_size,'sha256':sha(results/name)} for name in
               ['protocol_freeze.json','selected_policies.json','confirmation_runs.jsonl','output_audit.json','sensitivity.json']}}}


def table(report):
    out=['# Commercial core — reporting-only table, 27 October 2026','',
      'Means over 64 independent Beta worlds per scenario. All outcomes and USD amounts are modeled. The frozen scientific protocol and policy selection are unchanged.','',
      '| Scenario | Useful outcomes | Useful per selling week (104 weeks) | Useful per full-horizon week (120 weeks) | Collections USD | A job costs USD | Common costs USD | Closing obligations USD | Profit USD | Useful-receipts-only surplus USD | Available cash above initial seed USD | After additional operating floor USD |',
      '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    cols=['accepted_useful','useful_throughput_per_104_week','useful_throughput_per_120_week','collections','A_job_cost','common_cost','closing_obligations','profit','useful_collections_only_surplus','spendable_cash_above_initial_seed','available_after_seed_and_operating_floor']
    for name in ['conservative','central','favorable']:
        m=report['scenarios'][name]['metrics'];out.append('| '+name+' | '+' | '.join(f'{m[k]["mean"]:,.2f}' for k in cols)+' |')
    out+=['','The useful-receipts-only surplus retains only collections tied to useful on-time outcomes while charging all enterprise expenses and unexpensed closing liabilities. It is a postconfirmation reporting metric.','',
          'Cash above original seed is max(0,available_cash−seed). The additional planning buffer is max(0,min(profit,available_cash−seed)−operating floor). The operating floor is USD2,640 in each primary Beta scenario and is not another expense.','',
          'Prices were selected on the network policy family then applied unchanged to Beta. The report does not claim independently optimized Beta pricing or an empirically validated quality floor.','',
          'Pooled cost/collection-per-useful-outcome ratios in commercial_core.json are derived portfolio ratios, not matched job margins. Exact price observations distinguish all completed-job quotes, useful-delivered-job quotes, and representative recorded order events.','']
    return '\n'.join(out)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--evidence-zip',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--table',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists() or args.table.exists():raise FileExistsError('Refusing to overwrite retained commercial reporting outputs')
    report=calculate(args.study_root,args.evidence_zip)
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    args.table.write_text(table(report))
    print(json.dumps({'out':str(args.out),'passed':report['checks']['passed'],'checks':report['checks']['check_count'],
                      'failures':report['checks']['failure_count'],'Beta_worlds':sum(v['n_worlds'] for v in report['scenarios'].values())}))
    if not report['checks']['passed']:raise SystemExit(2)


if __name__=='__main__':main()
