"""Describe all frozen policy-diagnostic outcomes; never executes a new simulation."""
import collections, datetime, gzip, hashlib, json, pathlib, sys

root=pathlib.Path(__file__).resolve().parents[1]
results=root/'market/policy-diagnostic/results-01'
out=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else root/'review/policy-diagnostic-interpretation-metrics.json'
if out.exists(): raise SystemExit(f'Refusing to overwrite {out}; choose a new report path.')
summary=json.loads((results/'summary.json').read_text())
counts=collections.Counter();by_regime=collections.defaultdict(collections.Counter)
all_scenarios=[];positive_mean=[];selected=[]
def regime(c):
    return ('full' if c['investmentCostBasis']=='full-history' else 'adoption')+('-earned' if c['investmentFunding']=='operating-surplus' else '-seed')
for row in summary['scenarios']:
    r=regime(row['config']);b=row['arms']['B'];d=row['causal']['B_minus_A_profitCents']
    cc=by_regime[r];cc['configurations']+=1
    for label,condition in [('positive_mean_B_profit',b['profitCents']['mean']>0),('positive_mean_B_minus_A',d['mean']>0),('B_minus_A_normal_interval_above_zero',d['meanInterval95'][0]>0)]: cc[label]+=condition
    report={'scenario':row['scenario'],'regime':r,'mean_B_profit_cents':b['profitCents']['mean'],
        'B_profit_normal_interval_cents':b['profitCents']['meanInterval95'],
        'mean_B_minus_A_cents':d['mean'],'B_minus_A_normal_interval_cents':d['meanInterval95'],
        'B_investment_rate':b['investmentRate'],'B_profitable_solvent_rate':b['viableRate'],
        'B_direct_payback_rate':b['directRepaymentRate'],
        'B_offered_quote_range_cents':b['actualOfferedQuoteRange'],
        'mean_B_policy_minus_heuristic_cents':b['policyMinusHeuristicProfitCents']['mean']}
    all_scenarios.append(report)
    if b['profitCents']['mean']>0: positive_mean.append(report)
    if row['scenario'].startswith('policy-p2000-i0-a0.5-m10-logit-'): selected.append(report)

individuals=[];representative_histories=[]
with gzip.open(results/'complete-runs.jsonl.gz','rt') as f:
    for line in f:
        pair=json.loads(line);run=pair['arms']['B'];s=run['summary'];h=run['histories'];c=run['config'];r=regime(c)
        metrics={
            'B_worlds':1,'B_investments':len(h['investments']),
            'B_profitable_worlds':s['profitCents']>0,
            'B_positive_incremental_worlds':pair['causal']['B_minus_A_profitCents']>0,
            'B_profitable_and_positive_incremental_worlds':s['profitCents']>0 and pair['causal']['B_minus_A_profitCents']>0,
            'B_direct_payback_worlds':s['directCostPayback'],
            'B_direct_payback_but_negative_incremental_worlds':s['directCostPayback'] and pair['causal']['B_minus_A_profitCents']<0,
            'B_positive_earned_available_after_reserve_worlds':s['availableOperatingSurplusCents']>0,
            'B_earned_funded_investments':sum(i['funding']=='operating-surplus' for i in h['investments']),
            'B_seed_funded_investments':sum(i['funding']=='seed-funded' for i in h['investments']),
            'observed_customer_collections_cents':run['observedCustomerCollectionsCents']}
        for k,v in metrics.items(): counts[k]+=v;by_regime[r][k]+=v
        for i in h['investments']:
            individuals.append({'scenario':c['id'],'seed':run['seed'],'regime':r,'week':i['week'],
                'available_week':i['availableWeek'],'funding':i['funding'],
                'available_cash_at_investment_cents':i['availableCashCents'],
                'adoption_charge_cents':i['fullCostCents'],'asset_source_sha256':i['asset']['sha256'],
                'asset_uses':s['assetUses'],'profit_cents':s['profitCents'],
                'B_minus_A_cents':pair['causal']['B_minus_A_profitCents'],
                'direct_net_saving_cents':s['directNetSavingCents'],
                'direct_payback':s['directCostPayback'],
                'earned_available_after_reserve_cents':s['availableOperatingSurplusCents']})
        if c['id'].startswith('policy-p2000-i0-a0.5-m10-logit-') and run['seed']==2001:
            own=[j for j in h['jobs'] if j['provider']=='enterprise']
            bills=collections.Counter()
            for bill in h['bills']: bills[bill['category']]+=bill['amountCents']
            representative_histories.append({'scenario':c['id'],'seed':run['seed'],'config':c,
                'summary':s,'causal':pair['causal'],'investments':h['investments'],
                'accrued_bill_categories_cents':dict(bills),
                'accepted_before_asset':sum(j['accepted'] and not j['assetUsed'] for j in own),
                'accepted_after_asset':sum(j['accepted'] and bool(j['assetUsed']) for j in own),
                'first_week_positive_earned_available_after_reserve':next((x['week'] for x in h['balances'] if x['earnedAvailableCents']>0),None),
                'next_investment':run['nextInvestment']})

report={'schema':'agi-alpha-independent-policy-diagnostic-interpretation/v1',
    'executedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'POST_EXPLORATORY_REUSED_SEED_DIAGNOSTIC_NOT_CONFIRMATION',
    'source_summary_sha256':hashlib.sha256((results/'summary.json').read_bytes()).hexdigest(),
    'source_complete_runs_sha256':hashlib.sha256((results/'complete-runs.jsonl.gz').read_bytes()).hexdigest(),
    'counts':dict(counts),'by_regime':{k:dict(v) for k,v in by_regime.items()},
    'positive_mean_B_profit_configurations':positive_mean,
    'predeclared_representative_slice':selected,
    'predeclared_seed_2001_histories':representative_histories,
    'all_160_configurations':all_scenarios,'all_B_adoption_events':individuals,
    'interpretation':[
        'Grid fractions are descriptive, not probabilities of real market success.',
        'All normal intervals condition on assumed parameters, selected model and reused seeds; none validates real demand, human minutes, quality or complete engineering cost.',
        'Seed-funded adoption cannot establish financing from accumulated operating surplus. Full-history charges are assumed opening research costs; adoption-only excludes those costs.',
        'Positive direct avoided cost is not sufficient for positive B-minus-A enterprise value.',
        'B/C ties are imposed by symmetric modeled costs, policy and effects, not evidence of autonomous algorithmic advantage.',
        'No second productive asset was constructed, tested or financed; positive residual resources alone do not demonstrate a new capability cycle.',
        'Fixed targets of USD5 or USD10 can produce an initial USD14.33 actual offered price because the cost floor binds. Read actual quote and acceptance ranges.'
    ]}
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'output':str(out),'counts':report['counts'],'by_regime':report['by_regime']},indent=2))
