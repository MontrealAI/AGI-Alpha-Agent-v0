"""Describe every registered fresh-extension condition; execute no simulation."""
import collections,datetime,hashlib,json,math,pathlib,statistics,sys
root=pathlib.Path(__file__).resolve().parents[1]
results=root/'market/deployment-robustness/results-01'
out=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else root/'review/deployment-interpretation-metrics.json'
if out.exists(): raise SystemExit('Refusing to overwrite earlier interpretation receipt')
summary=json.loads((results/'summary.json').read_text())
config={r['scenario']:r['config'] for r in summary['scenarios']}
rows={};counts=collections.Counter();grouped=collections.defaultdict(collections.Counter)
for line in (results/'outcomes.jsonl').read_text().splitlines():
    r=json.loads(line)
    if r['arm']!='B': continue
    rows[(r['scenario'],r['seed'])]=r
    c=config[r['scenario']];basis=c['investmentCostBasis'];group=('main' if r['scenario'].startswith('robust-main') else 'stress')+'.'+basis
    f=r['funding'];t=f['terminal'];effect=r['causal']['B_minus_A_profitCents']
    metrics={'B_worlds':1,'B_adoptions':r['investmentWeek'] is not None,'B_failed_adoptions':r['failedInvestment'],
      'B_positive_profit_before_unpriced_discovery':r['profitCents']>0,
      'B_positive_incremental_value_before_unpriced_discovery':effect>0,
      'B_both_positive_before_unpriced_discovery':r['profitCents']>0 and effect>0,
      'B_direct_cost_payback':r['directCostPayback'],
      'B_direct_payback_but_negative_incremental_value':r['directCostPayback'] and effect<0,
      'B_positive_terminal_funding_ceiling':t['fundingCeilingBeforeUnpricedDiscoveryCents']>0,
      'B_positive_in_horizon_funding_ceiling':f['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents']>0,
      'B_positive_terminal_but_never_in_horizon_ceiling':t['fundingCeilingBeforeUnpricedDiscoveryCents']>0 and f['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents']==0,
      'B_positive_original_strict_terminal_earned':t['originalStrictEarnedAvailableCents']>0,
      'actual_second_investments_cents':r['actualSecondInvestmentCents'],'actual_revenue_cents':r['actualRevenueCents']}
    for k,v in metrics.items(): counts[k]+=v;grouped[group][k]+=v

def stats(values):
    mean=statistics.mean(values);sd=statistics.stdev(values)
    return {'n':len(values),'mean':mean,'meanNormalInterval95':[mean-1.96*sd/math.sqrt(len(values)),mean+1.96*sd/math.sqrt(len(values))],'minimum':min(values),'maximum':max(values)}
all_conditions=[];positive_conditions=[];adverse_comparisons=[]
for r in summary['scenarios']:
    c=r['config'];b=r['arms']['B'];d=r['causalBeforeUnpricedDiscovery']['B_minus_A_profitCents']
    report={'scenario':r['scenario'],'B_profit_before_D_cents':b['profitBeforeUnpricedDiscoveryCents'],
      'B_minus_A_before_differential_D_cents':d,'B_terminal_funding_ceiling_before_D_cents':b['terminalFundingCeilingBeforeUnpricedDiscoveryCents'],
      'B_maximum_in_horizon_funding_ceiling_before_D_cents':b['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents'],
      'B_adoption_rate':b['investmentRate'],'B_failed_adoption_rate':b['failedInvestmentRate'],
      'B_positive_profit_rate_before_D':b['positiveModeledProfitBeforeUnpricedDiscoveryRate'],
      'B_positive_in_horizon_funding_ceiling_rate_before_D':b['positiveDuringServiceFundingCeilingRate']}
    all_conditions.append(report)
    if b['profitBeforeUnpricedDiscoveryCents']['mean']>0: positive_conditions.append(report)
    if r['scenario'].startswith('robust-stress'):
        base=f"robust-main-i{c['integrationCents']}-a{c['arrivalProbability']:g}-{c['choiceModel']}-{c['investmentCostBasis']}"
        differences=[rows[(r['scenario'],s)]['profitCents']-rows[(base,s)]['profitCents'] for s in summary['seeds']]
        adverse_comparisons.append({'scenario':r['scenario'],'reference':base,'paired_B_profit_perturbation_minus_reference_before_D_cents':stats(differences)})
selected=[r for r in all_conditions if r['scenario'] in ('robust-main-i0-a0.5-logit-full-history','robust-main-i0-a0.5-logit-adoption-only')]
histories=[rows[(r['scenario'],3001)] for r in selected]
report={'schema':'agi-alpha-independent-fresh-deployment-interpretation/v1','executedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_summary_sha256':hashlib.sha256((results/'summary.json').read_bytes()).hexdigest(),
    'source_outcomes_sha256':hashlib.sha256((results/'outcomes.jsonl').read_bytes()).hexdigest(),
    'counts':dict(counts),'by_grid_and_cost_basis':{k:dict(v) for k,v in grouped.items()},
    'predeclared_reference_slice':selected,'predeclared_reference_seed_3001':histories,
    'all_128_conditions':all_conditions,'all_positive_mean_B_profit_conditions_before_D':positive_conditions,
    'all_80_paired_perturbation_comparisons':adverse_comparisons,
    'interpretation':[
      'All quantities are simulated conditional on declared human duration, utility, demand, quality and cost assumptions; exact-task external demand remains unidentified.',
      'G is a nonnegative funding ceiling before unknown discovery cost D, so mean G is not mean profit. Clipping negative available budgets at zero can make the mean ceiling exceed mean profit.',
      'Full-history research is charged once to cash/profit; its seed-paid origin is excluded only from prospective funding attribution. These are different questions.',
      'For attributed discovery cost D_arm, fixed-path arm profit decreases by D_arm and B-minus-A by D_B-D_A. Unknown differential costs do not automatically cancel.',
      'The fixed-target/model region was selected before these fresh seeds using earlier diagnostics. New stochastic seeds are conditional confirmation, not identification of the real economy.',
      'Named adverse corners are perturbations. Undercutting can be weaker than baseline adaptive markdowns; collection delays can alter competitor liquidity. A favorable realized intervention is not proof of monotonically harder conditions.',
      'No second asset qualified. No next purchase, construction effect, reinvestment revenue, autonomous superiority or self-acceleration was created.',
      'Grid counts are descriptive, not probabilities of real commercial success. Normal intervals are unadjusted across conditions and omit parameter/model uncertainty.'
    ]}
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'output':str(out),'counts':report['counts'],'by_grid_and_cost_basis':report['by_grid_and_cost_basis']},indent=2))
