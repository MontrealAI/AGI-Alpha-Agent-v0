"""Read-only audit of original and amended policy selection, not confirmation."""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def score(rows):
    x=sorted(r['discountedAccrualProfitCents'] for r in rows);tail=x[:max(1,math.ceil(len(x)*.1))]
    risk=sum(r['insolvent'] for r in rows)/len(rows)
    return {'scoreCents':sum(x)/len(x)+.25*sum(tail)/len(tail),'insolvencyRate':risk,'eligible':risk<=.05}
def winner(scored):
    pool=[x for x in scored if x['eligible']]
    if not pool:
        minimum=min(x['insolvencyRate'] for x in scored)
        pool=[x for x in scored if x['insolvencyRate']==minimum]
    return sorted(pool,key=lambda x:(-x['scoreCents'],x['insolvencyRate'],x['policyId']))[0]
def near(a,b):assert abs(a-b)<1e-7*max(1,abs(a),abs(b)),(a,b)
initial=read('protocol/initial_selected_policies.json')
training=read('results/training.json')
amendment=read('protocol/beta_symmetry_amendment.json')
extra=read('results/beta_symmetry_training.json')
selected=read('protocol/selected_policies.json')
assert sha('protocol/initial_selected_policies.json')==amendment['originalSelectionSHA256']
assert sha('results/training.json')==amendment['originalTrainingSHA256']
assert sha('protocol/beta_symmetry_amendment.json')==extra['amendmentSHA256']==selected['amendmentSHA256']
assert sha('results/beta_symmetry_training.json')==selected['expandedBetaTrainingSHA256']
assert selected['confirmationSeedsInspected']==0
policy_defs={p['id']:p for p in amendment['betaPolicies']}
all_groups=defaultdict(list)
for row in extra['rows']:all_groups[(row['scenario'],row['policy'])].append(row)
checks={}
for scenario,choices in selected['selected'].items():
    assert choices['network']['policy']==initial['selected'][scenario]['network']['policy'], 'Network was retuned after amendment'
    scored=[]
    for policy_id in policy_defs:
        rows=all_groups[(scenario,policy_id)]
        assert sorted(r['seed'] for r in rows)==amendment['trainingSeeds']
        scored.append({'policyId':policy_id,**score(rows)})
    best=winner(scored)
    assert choices['beta']['policy']['id']==best['policyId']
    near(choices['beta']['scoreCents'],best['scoreCents'])
    assert choices['beta']['insolvencyRate']==best['insolvencyRate']
    candidates=[]
    for kind in ['network','beta']:
        x=choices[kind]
        candidates.append({'policyId':x['policy']['id'],'scoreCents':x['scoreCents'],
                           'insolvencyRate':x['insolvencyRate'],'eligible':x['eligible']})
    assert choices['enterprise']['policy']['id']==winner(candidates)['policyId']
    checks[scenario]={
        'networkPolicyUnchanged':choices['network']['policy']['id'],
        'symmetricBetaWinner':choices['beta']['policy']['id'],
        'enterpriseWinner':choices['enterprise']['policy']['id'],
        'trainingRiskConstraintSatisfied':choices['beta']['constraintSatisfied'],
        'priceRatio':choices['enterprise']['policy']['priceRatio'],
        'scarcityCoefficient':choices['enterprise']['policy']['scarcity'],
        'reserveFactor':choices['enterprise']['policy']['reserveFactor'],
        'scientificConfirmationClaim':False,
    }
z=1.959963984540054
out={'schema':'beyond-beta-selection-audit/v1','passed':True,
     'selectedPoliciesSHA256':sha('protocol/selected_policies.json'),
     'amendmentSHA256':sha('protocol/beta_symmetry_amendment.json'),
     'originalPolicyHistories':len(training['rows']),'additionalSymmetricBetaHistories':len(extra['rows']),
     'originalNetworkWinnersPreserved':True,'confirmationResultsUsed':False,'selectionChecks':checks,
     'zeroInsolvenciesWilsonUpper95ByWorldCount':{str(n):z*z/(n+z*z) for n in [12,24,128]},
     'interpretation':[
         'The fairness amendment was registered after the first development screen and before any confirmation.',
         'Beta received the same price/scarcity/reserve freedoms; network winners were not retuned upward.',
         'The enterprise selecting Beta in training is a development decision, not evidence of confirmed dominance.',
         'A sample insolvency constraint does not prove the true modeled frequency is at most5%. Use fresh-confirmation Wilson intervals.',
         'A capacity holdout of12 independent worlds cannot establish a5% upper insolvency risk: even zero events has a24.25% Wilson upper bound.'
     ]}
(ROOT/'results/analysis/selection_audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
