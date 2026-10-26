#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Arithmetic reporting over the completed frozen extension; no simulation."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results-01'
completion = json.loads((OUT/'completion.json').read_text())
assert completion['completed'] and completion['pairedWorlds'] == 3072
source = json.loads((OUT/'summary.json').read_text())
scenarios = source['scenarios']
rows = [json.loads(line) for line in (OUT/'outcomes.jsonl').read_text().splitlines()]
brows = [r for r in rows if r['arm'] == 'B']

def counts(worlds, conditions):
    return {
        'configurations':len(conditions),'B_worlds':len(worlds),
        'first_asset_invested':sum(r['investmentWeek'] is not None for r in worlds),
        'first_asset_failed':sum(r['failedInvestment'] for r in worlds),
        'profitable_before_unknown_D':sum(r['profitCents']>0 and not r['insolvent'] and r['obligationsCents']==0 for r in worlds),
        'positive_B_minus_A_before_unknown_D':sum(r['causal']['B_minus_A_profitCents']>0 for r in worlds),
        'positive_terminal_funding_ceiling_before_unknown_D':sum(r['funding']['terminal']['fundingCeilingBeforeUnpricedDiscoveryCents']>0 for r in worlds),
        'positive_during_service_funding_ceiling_before_unknown_D':sum(r['funding']['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents']>0 for r in worlds),
        'actual_second_investments':sum(r['actualSecondInvestmentCents']!=0 for r in worlds),
        'insolvent':sum(r['insolvent'] for r in worlds),
        'positive_mean_B_profit_before_D_configurations':sum(s['arms']['B']['profitBeforeUnpricedDiscoveryCents']['mean']>0 for s in conditions),
        'positive_lower_MC_interval_B_profit_before_D_configurations':sum(s['arms']['B']['profitBeforeUnpricedDiscoveryCents']['meanInterval95'][0]>0 for s in conditions),
        'positive_mean_B_minus_A_before_D_configurations':sum(s['causalBeforeUnpricedDiscovery']['B_minus_A_profitCents']['mean']>0 for s in conditions),
        'positive_lower_MC_interval_B_minus_A_before_D_configurations':sum(s['causalBeforeUnpricedDiscovery']['B_minus_A_profitCents']['meanInterval95'][0]>0 for s in conditions),
    }

table=[]
for s in scenarios:
    c=s['config']
    row={'scenario':s['scenario'],'condition_type':'main' if s['scenario'].startswith('robust-main-') else 'adverse',
         'target_price_USD':c['initialPriceCents']/100,'integration_USD':c['integrationCents']/100,
         'arrival_probability':c['arrivalProbability'],'choice_model':c['choiceModel'],
         'cost_basis':c['investmentCostBasis'],'seed_count':len(source['seeds']),
         'funding':'SEED_INCLUSIVE_FIRST_DEPLOYMENT','unknown_incremental_discovery_cost_D':'UNKNOWN',
         'actual_second_investments':0}
    for arm in 'ABC':
        a=s['arms'][arm]
        for key in ['profitBeforeUnpricedDiscoveryCents','collectionsCents','finalCashCents',
                    'terminalFundingCeilingBeforeUnpricedDiscoveryCents','terminalFullCostRecoveryCeilingBeforeUnpricedDiscoveryCents',
                    'maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents','originalStrictTerminalEarnedCents']:
            row[f'{arm}_{key}_mean_USD']=a[key]['mean']/100
            row[f'{arm}_{key}_MC95_low_USD']=a[key]['meanInterval95'][0]/100
            row[f'{arm}_{key}_MC95_high_USD']=a[key]['meanInterval95'][1]/100
        row[f'{arm}_mean_accepted']=a['accepted']['mean']
        for key in ['investmentRate','failedInvestmentRate','insolvencyRate','positiveModeledProfitBeforeUnpricedDiscoveryRate',
                    'positiveTerminalFundingCeilingRate','positiveDuringServiceFundingCeilingRate','directRepaymentRate']:
            row[f'{arm}_{key}']=a[key]
    for key in ['B_minus_A_profitCents','C_minus_A_profitCents','B_minus_C_profitCents']:
        a=s['causalBeforeUnpricedDiscovery'][key]
        row[f'{key}_before_D_mean_USD']=a['mean']/100
        row[f'{key}_before_D_MC95_low_USD']=a['meanInterval95'][0]/100
        row[f'{key}_before_D_MC95_high_USD']=a['meanInterval95'][1]/100
    row['incremental_terminal_funding_ceiling_mean_USD']=s['incrementalTerminalFundingCeilingCents']['mean']/100
    row['B_C_exact_ties']=s['B_C_exact_ties']
    table.append(row)

def write_csv(path, records):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)

write_csv(OUT/'summary.csv',table)
write_csv(OUT/'main-threshold-table.csv',[r for r in table if r['condition_type']=='main'])
write_csv(OUT/'adverse-table.csv',[r for r in table if r['condition_type']=='adverse'])
selected={f'robust-main-i0-a0.5-logit-{basis}' for basis in ['full-history','adoption-only']}
representatives=[]
funding_rows=[]
post_asset_positive=0
with gzip.open(OUT/'complete-runs.jsonl.gz','rt') as f:
    for line in f:
        paired=json.loads(line)
        if paired['config']['id'] in selected and paired['seed']==3001:representatives.append(paired)
        for arm in 'ABC':
            run=paired['arms'][arm];funding=paired['successionAvailability']['fundingByArm'][arm]
            successes=[event for event in run['histories']['investments'] if event['success']]
            available=successes[0]['availableWeek'] if successes else None
            post=[r for r in funding['weekly'] if available is not None and available<=r['week']<run['config']['weeks']]
            maximum=max([0]+[r['fundingCeilingBeforeUnpricedDiscoveryCents'] for r in post])
            if arm=='B' and maximum>0:post_asset_positive+=1
            funding_rows.append({'scenario':paired['config']['id'],'seed':paired['seed'],'arm':arm,
                'first_investment_week':run['summary']['investmentWeek'],'successful_asset_available_week':available,
                'actual_asset_uses_in_simulation':run['summary']['assetUses'],
                'terminal_funding_ceiling_before_D_USD':funding['terminal']['fundingCeilingBeforeUnpricedDiscoveryCents']/100,
                'max_during_service_funding_ceiling_before_D_USD':funding['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents']/100,
                'max_after_successful_first_adoption_during_service_funding_ceiling_before_D_USD':maximum/100,
                'old_strict_terminal_USD':funding['terminal']['originalStrictEarnedAvailableCents']/100,
                'historical_opening_RD_excluded_from_generated_recovery_USD':funding['historicalRDCentsExcluded']/100,
                'unpriced_incremental_discovery_cost_D':'UNKNOWN','actual_second_investment_USD':0,
                'profit_before_unknown_D_USD':run['summary']['profitCents']/100,
                'B_minus_A_before_unknown_D_USD':paired['causal']['B_minus_A_profitCents']/100})

write_csv(OUT/'funding-availability-by-run.csv',funding_rows)
(OUT/'predeclared-representative-histories.json').write_text(json.dumps({
    'selection':'Pre-outcome selection: USD20 target, integration0, arrival0.5, logit, both cost bases, seed3001.',
    'costBoundary':'BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY','unpricedDiscoveryCostD':None,
    'pairedWorlds':representatives},indent=2)+'\n')
findings={'schema':'agi-alpha-deployment-robustness-descriptive-findings/v1',
    'sourceSummarySHA256':hashlib.sha256((OUT/'summary.json').read_bytes()).hexdigest(),
    'costBoundary':'BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY','unpricedIncrementalDiscoveryCostD':None,
    'qualification':'Scenario-grid counts are not market probabilities. Conditional mean intervals do not cover unidentified parameters or unknown incremental discovery cost D. G_after_search<=max(0,G_reported-D), with no assumed D=0 or empirical upper bound. No actual second asset or investment exists.',
    'all':counts(brows,scenarios),
    'byCostBasis':{basis:counts([r for r in brows if r['investmentCostBasis']==basis],
        [s for s in scenarios if s['config']['investmentCostBasis']==basis]) for basis in ['full-history','adoption-only']},
    'byConditionType':{kind:counts([r for r in brows if r['scenario'].startswith(prefix)],
        [s for s in scenarios if s['scenario'].startswith(prefix)]) for kind,prefix in [('main','robust-main-'),('adverse','robust-stress-')]},
    'all_B_C_exact_ties':all(s['B_C_exact_ties'] for s in scenarios),
    'B_worlds_positive_funding_ceiling_during_service_after_successful_first_asset':post_asset_positive,
    'predeclaredReference':[r for r in table if r['scenario'] in selected],
    'positiveMeanProfitConditionsBeforeUnknownD':[r for r in table if r['B_profitBeforeUnpricedDiscoveryCents_mean_USD']>0]}
(OUT/'descriptive-findings.json').write_text(json.dumps(findings,indent=2)+'\n')
print(json.dumps({'all':findings['all'],'byCostBasis':findings['byCostBasis'],
                  'representatives':len(representatives),'postFirstAssetFundingPositive':post_asset_positive},indent=2))
