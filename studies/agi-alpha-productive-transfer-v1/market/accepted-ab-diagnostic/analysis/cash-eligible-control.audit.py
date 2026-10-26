# SPDX-License-Identifier: Apache-2.0
"""Independent arithmetic check of the one declared post-campaign software control."""
import collections, datetime, gzip, hashlib, json, pathlib, time

base=pathlib.Path(__file__).resolve().parent
package=base.parent;study=package.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
checks=collections.Counter();failures=[]
def ck(ok,name,context=None):
    checks[name]+=1
    if not ok:failures.append({'name':name,'context':context})
start=time.perf_counter()
data=read(base/'cash-eligible-control.result.json');input=read(base/'cash-eligible-control.input.json')
ck(data['inputSHA256']==sha(base/'cash-eligible-control.input.json'),'declared input identity')
ck(data['sourceSHA256']==sha(base/'cash-eligible-control.mjs'),'executed source identity')
ck(data['seed']==input['seed']==3001,'single prespecified seed')
freeze=read(package/'freeze.json')
for f in freeze['files']:ck(sha(study/f['path'])==f['sha256'],'registered frozen files unchanged',f['path'])
with gzip.open(package/'results/all-paired-histories.jsonl.gz','rt') as f:reference=json.loads(next(f))
ck(reference['scenario']=='accepted-ab-reference-deterministic' and reference['seed']==3001,'declared reference identity')
pair=data['pair'];A=pair['arms']['A'];B=pair['arms']['B'];exact=pair['exactAsset']['sha256']
ck(A['summary']==B['summary'] and pair['differences']['B_minus_A_profitCents']==0,'no incremental A/B benefit')
for arm in ['A','B']:
    r=pair['arms'][arm];c=r['config'];h=r['histories'];s=r['summary']
    permitted={'id','integrationCents','arrivalProbability','reserveCents'}|({'authoringCostCents'} if arm=='B' else set())
    for key,value in reference['arms'][arm]['config'].items():
        if key not in permitted:ck(c[key]==value,'quality competitors and all undeclared inputs unchanged',(arm,key))
    ck(c['integrationCents']==0 and c['arrivalProbability']==1 and c['reserveCents']==0,'declared common cash conditions',arm)
    ck(c['computeAndToolCents']==c['activeComputeAndToolCents']==500 and c['initialPriceCents']==2000,'same nominal cost and target price',arm)
    ck(c['authoringCostCents']==(2500 if arm=='B' else 0),'declared complete construction envelope',arm)
    bills={b['id']:b for b in h['bills']};invoices={i['id']:i for i in h['invoices']}
    balance=c['initialCashCents'];paid=set();collected=set()
    for event in h['cash']:
        balance+=event['amountCents'];ref=event['reference']
        ck(balance==event['cashAfterCents'] and balance>=0,'cash balance conserved and nonnegative',arm)
        if event['amountCents']<0:
            ck(ref in bills and ref not in paid and bills[ref]['amountCents']==-event['amountCents'],'cash bill paid exactly once',arm);paid.add(ref)
        else:
            ck(ref in invoices and ref not in collected and invoices[ref]['amountCents']==event['amountCents'],'accepted invoice collected exactly once',arm);collected.add(ref)
    receivable=sum(i['amountCents'] for i in h['invoices'] if i['status']=='pending')
    unpaid=sum(b['amountCents'] for b in h['bills'] if not b['paid'])
    ck(balance==s['finalCashCents'] and s['profitCents']==balance+receivable-unpaid-c['initialCashCents'],'profit excludes initial capital',arm)
    ck(all(j['accepted'] or not j['invoiceCreated'] for j in h['jobs']),'rejected work never invoiced',arm)
    ck(not h['investments'] and not s['assetActive'] and s['assetUses']==0,'no forced construction or free activation',arm)
    ck(s['actualRevenueCents']==0 and r['observedCustomerCollectionsCents']==0,'actual collections remain zero',arm)

earned=[]
for d in B['histories']['investmentDecisions']:
    h=B['histories'];c=B['config'];week=d['week']
    pre_bills=[b for b in h['bills'] if b['week']<week or (b['week']==week and b['category'] not in ['delivery','capability'])]
    pre_ids={b['id'] for b in pre_bills}
    events=[e for e in h['cash'] if e['week']<week or (e['week']==week and (e['amountCents']>0 or e['reference'] in pre_ids))]
    cash_before=c['initialCashCents']+sum(e['amountCents'] for e in events)
    unpaid_before=sum(b['amountCents'] for b in pre_bills if not b['paid'] or b['paidWeek']>week)
    cost_before=sum(b['amountCents'] for b in pre_bills)
    collections_before=sum(e['amountCents'] for e in events if e['amountCents']>0)
    available=min(cash_before-unpaid_before-c['reserveCents'],collections_before-cost_before-c['reserveCents'])
    earned.append(available)
    ck(available==d['availableCashCents'],'decision-time earned funds independently reconstructed',week)
    ck(available>=2500 and d['fullCostCents']==2500,'cash sufficient for the complete declared envelope',week)
    ck(d['asset']['sha256']==exact,'same exact accepted B asset offered',week)
    ck(d['expectedIncrementalSavingPerUseCents']==0,'no invented marginal benefit',week)
    expected=-2500-d['productiveWeeksAfterAdoption']*c['assetMaintenanceCentsPerWeek']-d['expectedForegoneContributionCents']
    ck(expected==d['expectedNetBenefitCents'] and expected<=0,'full forecast independently reconstructed',week)
    ck(d['action']=='retain-incumbent' and set(d['reasons'])=={'no positive task saving','expected full-cost repayment not positive'},'zero-saving refusal isolated from liquidity failure',week)
ck(len(earned)==data['decisions']==data['cashEligibleDecisions']==44,'all 44 decisions cash eligible')
report={'schema':'agi-alpha-post-campaign-cash-eligibility-arithmetic-audit/v1',
 'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not failures else 'FAIL',
 'classification':'POST_CAMPAIGN_SOFTWARE_CONTROL_NOT_REGISTERED_MARKET_OUTCOME','seed':3001,
 'checks':dict(checks),'failures':failures,'resultSHA256':sha(base/'cash-eligible-control.result.json'),
 'auditSourceSHA256':sha(pathlib.Path(__file__)),'cashEligibleDecisions':len(earned),
 'minimumAvailableEarnedCashCents':min(earned),'maximumAvailableEarnedCashCents':max(earned),
 'BInvestments':0,'firstEligibleDecision':data['firstCashEligibleDecision'],
 'resources':{'wallSeconds':time.perf_counter()-start,'cpuSeconds':None,'monetaryCostCents':None,'authoringInferenceCostCents':None},
 'boundary':'A separate arithmetic implementation on the same project/session/host. This isolates an incentive-policy path; it is not field validation, new demand calibration or an additional registered world.'}
with (base/'cash-eligible-control.audit.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ['status','cashEligibleDecisions','minimumAvailableEarnedCashCents','maximumAvailableEarnedCashCents','BInvestments']}))
raise SystemExit(bool(failures))
