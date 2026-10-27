"""Read-only audit of completed capacity development and fresh holdout rows."""
import hashlib,json,math
from pathlib import Path
from statistics import mean,stdev
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def dist(x):
    x=sorted(x);m=mean(x);se=stdev(x)/len(x)**.5 if len(x)>1 else 0
    return {'n':len(x),'mean':m,'median':x[(len(x)-1)//2],
            'p05':x[math.floor((len(x)-1)*.05)],'p95':x[math.floor((len(x)-1)*.95)],
            'meanMC95':[m-1.96*se,m+1.96*se]}
def freq(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*(p*(1-p)/n+z*z/(4*n*n))**.5/d
    return {'count':k,'n':n,'rate':p,'wilson95':[max(0,c-h),min(1,c+h)]}
def score(rows):
    x=sorted(r['discountedAccrualProfitCents'] for r in rows)
    return mean(x)+.25*mean(x[:math.ceil(len(x)*.1)])
d=read('results/scale.json');lock=read('protocol/selected_capacity.json')
assert len(d['rows'])==432 and len(d['capacityHoldoutRows'])==72 and d['auditedRuns']==504
assert lock['confirmationSeedsInspected']==0
selection_seeds=set(range(1035000,1035012));holdout_seeds=set(range(1060000,1060012))
assert selection_seeds.isdisjoint(holdout_seeds)
holdouts=[]
for leads in [12,48,144]:
    cases=[x for x in d['cases'] if x['C']['prospectsMonthly']==leads]
    candidates=[]
    for case in cases:
        rows=[r for r in d['rows'] if r['case']==case['id'] and r['arm']=='network']
        assert {r['seed'] for r in rows}==selection_seeds
        candidates.append({'case':case['id'],'score':score(rows),'risk':sum(r['insolvent'] for r in rows)/len(rows)})
    eligible=[x for x in candidates if x['risk']<=.05]
    if not eligible:eligible=[x for x in candidates if x['risk']==min(y['risk'] for y in candidates)]
    expected=sorted(eligible,key=lambda x:(-x['score'],x['case']))[0]
    selected=lock['selections'][str(leads)];assert selected['case']==expected['case']
    rows=[r for r in d['capacityHoldoutRows'] if r['case']==selected['case']]
    network=[r for r in rows if r['arm']=='network'];beta={r['seed']:r for r in rows if r['arm']=='same-price-beta'}
    assert {r['seed'] for r in network}==holdout_seeds==set(beta)
    diffs=[(r['profitCents']-beta[r['seed']]['profitCents'])/100 for r in network]
    c=selected['config']
    holdouts.append({'expectedProspectsMonthly':leads,'selectedCase':selected['case'],
        'concurrency':c['concurrency'],'weeklyInputQuota':c['inputQuotaWeekly'],
        'weeklyOutputQuota':c['outputQuotaWeekly'],'weeklyComputeResourceHours':c['cpuHoursWeekly'],
        'weeklyValidatorHours':c['validatorHoursWeekly'],'independentWorlds':len(network),
        'fullProfitUSD':dist([r['profitCents']/100 for r in network]),
        'fullSignedIncrementalProfitUSD':dist(diffs),'positiveIncrementalProfit':freq(sum(x>0 for x in diffs),len(diffs)),
        'profitable':freq(sum(r['profitCents']>0 for r in network),len(network)),
        'insolvent':freq(sum(r['insolvent'] for r in network),len(network)),
        'usefulOutcomes':dist([r['usefulAccepted'] for r in network]),
        'usefulOutcomesPerActiveMonth':dist([r['acceptedPerMonth'] for r in network]),
        'queueP95Weeks':dist([r['queueP95Weeks'] for r in network]),
        'paidOriginCandidates':sum(r['paidOriginCandidates'] for r in network),
        'retentionCampaigns':sum(r['retentionCampaigns'] for r in network),
        'optionalResearchCampaigns':sum(r['separateResearchCampaigns'] for r in network),
        'admissions':sum(r['successfulCampaigns'] for r in network),
        'paidOriginAdmissions':sum(r['paidOriginAdmissions'] for r in network),
        'usefulPeerUseJobs':sum(r['peerUsefulOutcomes'] for r in network),
        'inputUtilization':dist([r['inputUtilization'] for r in network]),
        'outputUtilization':dist([r['outputUtilization'] for r in network]),
        'computeUtilization':dist([r['cpuUtilization'] for r in network]),
        'capacityRefusals':dist([r['capacityRefusals'] for r in network]),
        'escapedErrorShare':dist([r['escapedErrorShare'] for r in network]),
    })
development=[r for r in d['rows'] if r['arm']=='network']
rare=[{k:r[k] for k in ['case','seed','successfulCampaigns','paidOriginAdmissions','peerUsefulOutcomes','profitCents']}
      for r in development if r['successfulCampaigns']>0]
examples=[]
for scenario in ['conservative','central','favorable']:
    p=ROOT/f'results/examples/{scenario}_network.json'
    if not p.exists():continue
    run=json.loads(p.read_text());h=run['histories'];s=run['summary'];stages={}
    for kind in ['B_paid_job_retention','C_optional_research']:
        rows=[r for r in h['decisions'] if r['sourceKind']==kind]
        if not rows:continue
        best=max(rows,key=lambda x:x['forecastNetCents'])
        stages[kind]={'decisions':len(rows),'affordable':sum(r['affordable'] for r in rows),
            'capacityBookable':sum(r['capacityAvailable'] for r in rows),
            'decisionsByOutcome':dict(Counter(r['decision'] for r in rows)),
            'maximumBenefitCostRatio':max(r['benefitCostRatio'] for r in rows),
            'leastNegativeCase':{'week':best['week'],'keys':best['keys'],
                'extractionOrConstructionUSD':best['construction']['costCents']/100,
                'completeIncrementalHurdleUSD':best['completeCostCents']/100,
                'forecastGrossBenefitUSD':best['forecastGrossBenefitCents']/100,
                'forecastDisplacedServiceContributionUSD':best['forecastDisplacementCostCents']/100,
                'forecastNetUSD':best['forecastNetCents']/100,
                'forecastEligibleUses':best['forecastEligibleUses'],
                'alreadyPaidSourceAUSD':best['jobDevelopmentAlreadyChargedCents']/100}}
    examples.append({'scenario':scenario,'seed':run['seed'],'illustrativeSavedExampleNotPooledConfirmation':True,
        'accepted':s['accepted'],'usefulAccepted':s['usefulAccepted'],
        'paidCandidates':s['paidOriginCandidates'],'rightsClearedCandidates':s['rightsClearedCandidates'],
        'decisions':stages,'assessmentCount':len(h['alphaAssessments']),
        'actualGraphAdmissions':sum(e['type']=='modeled-admission' for e in h['network']),
        'reasonLearningStops':'Forecast return after scarce-capacity opportunity cost is negative before gate execution' if stages and not h['alphaAssessments'] else 'See recorded stage counts'})
out={'schema':'beyond-beta-capacity-and-learning-stage-readout/v1','scaleSHA256':sha('results/scale.json'),
     'capacitySelectionSHA256':sha('protocol/selected_capacity.json'),
     'all504HistoriesPresent':True,'selectionRuleIndependentlyRecomputed':True,
     'heldOutWorldsPerCondition':12,'capacityHoldouts':holdouts,
     'developmentOnlyGraphAdmissions':rare,'savedExampleLearningStages':examples,
     'limitations':[
        'Development-grid admissions are not fresh confirmation and cannot be substituted for zero-admission capacity holdouts.',
        'The selected capacity comparison holds agents and quotas equal across network and Beta.',
        'Positive enterprise profit does not establish incremental Alpha or network benefit.',
        'The pre-investment opportunity-cost estimate uses blind worst-case reservation and can dominate small retention extraction cost.',
        'The policy grid does not include a separately optimized paid-retention-only enterprise; the no-separate-research ablation is diagnostic, not a global optimality proof.',
        'At12 independent worlds, zero insolvencies has a24.25% Wilson95 upper bound.',
        'All capacities, demand, performance and retained-effect assumptions remain model conditions, not production entitlements.'
     ]}
(ROOT/'results/analysis/capacity_readout.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'passed':True,'holdoutCases':[{k:r[k] for k in ['selectedCase','paidOriginCandidates','retentionCampaigns','optionalResearchCampaigns','admissions','usefulPeerUseJobs']} for r in holdouts],
                  'developmentOnlyAdmissions':rare,'output':'results/analysis/capacity_readout.json'},indent=2))
