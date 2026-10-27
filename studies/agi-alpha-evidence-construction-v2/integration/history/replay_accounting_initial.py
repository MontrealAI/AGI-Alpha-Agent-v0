# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parents[1]/'agi-alpha-capability-opportunity-v1'/'integration'
spec=importlib.util.spec_from_file_location('preserved_accounting_bridge',PRIOR/'bridge.py')
if spec is None or spec.loader is None:
    raise RuntimeError('Missing bridge')
bridge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
paths=json.loads((ROOT.parent/'economics'/'results-v1'/'paths.json').read_text())
path=paths['E+success']
categories=['model','tools','compute','storage','network','human','acceptance','correction','overhead']
totals={b:{c:0 for c in categories} for b in 'ABC'}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

for entry in path['events']:
    event=entry['event']
    if event['kind']!='cost':
        continue
    activity=event['activity']
    tail=activity.rsplit(':',1)[-1]
    category=tail if tail in categories else 'human'
    if tail=='verification' or 'assessment' in activity:
        category='acceptance'
    elif tail=='correction' or 'correction' in activity:
        category='correction'
    elif 'upkeep' in activity:
        category='storage'
    totals[event['bucket']][category]+=event['amount_cents']*10000
commands=[]
for action,amount in [('capital',100000),('invoice',path['final']['recognized_revenue_cents'])]:
    commands.append({'action':action,'record':{'record_id':'conditional-'+action,'mission_id':'conditional-campaign',
        'amount_micro_usd':amount*10000,'evidence_digest':digest(['SIMULATED',action,amount])}})
for bucket in 'ABC':
    mission='conditional-'+bucket
    for category in categories:
        amount=totals[bucket][category]
        commands.append({'action':'charge','record':{'activity_id':mission+'-'+category,'mission_id':mission,
            'bucket':bucket,'category':category,'accrued_micro_usd':amount,'paid_micro_usd':amount,
            'basis':'attested','evidence_digest':digest([bucket,category,amount]),
            'note':'SIMULATED_SCENARIO amount; no provider invoice or live customer. Zero is explicit modeled absence.'}})
    commands.append({'action':{'A':'seal','B':'seal-retention','C':'seal-investment'}[bucket],
        'record':{'mission_id':mission,'categories':categories,'evidence_digest':digest([mission,'complete-modeled'])}})
commands.append({'action':'collection','record':{'record_id':'conditional-collected','mission_id':'conditional-campaign',
    'amount_micro_usd':path['final']['earned_collections_cents']*10000,'evidence_digest':digest(['SIMULATED',path['final']])}})
commands.append({'action':'reserve','record':path['final']['reserve_cents']*10000})
result=bridge.replay_native(commands,controls=True)
assert result['report']['costs']=={b:path['final']['costs_cents'][b]*10000 for b in 'ABC'}
assert result['report']['complete_cost_profit']==path['final']['collected_basis_profit_cents']*10000
unknown=[]
for category in categories:
    unknown.append({'action':'charge','record':{'activity_id':'actual-'+category,'mission_id':'actual-research',
        'bucket':'C','category':category,'accrued_micro_usd':None,'paid_micro_usd':0,'basis':'unknown',
        'evidence_digest':digest(['actual-provider-billing-unavailable',category]),
        'note':'Complete actual research cost is unknown; no zero-cost or actual profit claim.'}})
unknown.append({'action':'seal-investment','record':{'mission_id':'actual-research','categories':categories,
    'evidence_digest':digest('actual-complete-unknown-categories')}})
actual=bridge.replay_native(unknown)
(ROOT/'results'/'native-modeled-accounting.json').write_text(json.dumps(result,indent=2)+'\n')
(ROOT/'results'/'native-actual-unknown.json').write_text(json.dumps(actual,indent=2)+'\n')
print(json.dumps({'conditional_profit_micro_usd':result['report']['complete_cost_profit'],
    'conditional_costs':result['report']['costs'],'native_controls':result['controls'],
    'actual_report':actual['report']},indent=2))
