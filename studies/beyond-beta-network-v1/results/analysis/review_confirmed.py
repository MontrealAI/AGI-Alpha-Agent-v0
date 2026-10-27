"""Independent post-freeze arithmetic on completed ledgers; no simulation runs.

Price/workload thresholds condition on the saved mix, acceptance, collection and
failure outcomes. They do not rerun buyer choice or establish feasible demand.
"""
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'results/analysis'
FREEZE = '850e6978a3946f8f9d01dd0c6920b49916e955d12b420a65c1241d3c5cd675f6'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def load(path): return json.loads(path.read_text())
def near(a,b): assert abs(a-b)<=1e-7*max(1,abs(a),abs(b)), (a,b)
def ceil_ratio(a,b): return math.ceil(a/b) if b>0 else None
def dist(values):
    x=sorted(v for v in values if v is not None and math.isfinite(v))
    if not x:return {'n':0,'mean':None,'median':None,'p05':None,'p95':None,'meanMC95':None}
    m=mean(x);se=stdev(x)/math.sqrt(len(x)) if len(x)>1 else 0
    return {'n':len(x),'mean':m,'median':x[(len(x)-1)//2],
            'p05':x[math.floor((len(x)-1)*.05)],'p95':x[math.floor((len(x)-1)*.95)],
            'meanMC95':[m-1.96*se,m+1.96*se]}
def frequency(k,n):
    if not n:return {'count':k,'n':0,'rate':None,'wilson95':None}
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {'count':k,'n':n,'rate':p,'wilson95':[mid-half,mid+half]}

def service_thresholds(run):
    h,s=run['histories'],run['summary'];bills=h['bills']
    resource=[b for b in bills if b['category']!='refund']
    cost=sum(b['amountCents'] for b in resource)
    assert cost==s['costsCents']
    fees=sum(b['amountCents'] for b in resource if b['reference'].startswith('payment-processing:'))
    delivery=sum(b['amountCents'] for b in resource if b['lane']=='A_paid_job')
    acquisition=sum(b['amountCents'] for b in resource if b['reference'].startswith('automated-intake-and-acquisition:'))
    lanes={k:sum(b['amountCents'] for b in resource if b['lane']==k) for k in
           ['A_paid_job','B_retention_reuse','C_optional_research','common_business','historical_allowance']}
    assert sum(lanes.values())==cost
    g,r=s['collectionsCents'],s['refundsCents'];net_after_fee=g-r-fees
    accepted=[j for j in h['jobs'] if j['accepted']];n=len(accepted)
    assert n==s['accepted'];qualified=[o for o in h['offers'] if o['scopeSupported']]
    chosen=[o for o in qualified if o['choice']=='ai']
    mean_price=mean(j['priceCents'] for j in accepted) if n else None
    mean_human=mean(j['humanPriceCents'] for j in accepted) if n else None
    scale=(cost-fees)/net_after_fee if net_after_fee>0 else None
    variable=delivery+acquisition+fees;fixed=cost-variable
    unit_contribution=(g-r-variable)/n if n else 0
    minimum_accepted=ceil_ratio(fixed,unit_contribution)
    exposure_fixed=cost-delivery-fees
    unit_after_delivery=(g-r-delivery-fees)/n if n else 0
    exposure_min=ceil_ratio(exposure_fixed,unit_after_delivery)
    choice_completion=n/len(chosen) if chosen else 0
    required_choices=ceil_ratio(exposure_min,choice_completion) if exposure_min is not None else None
    adoption=required_choices/len(qualified) if required_choices is not None and qualified else None
    buyer_ceilings=[];buyer_scales=[]
    for offer in qualified:
        s_offer=offer['completionBelief'];u=offer['utilitiesCents']
        if s_offer<=0:continue
        outside=max(u['human'],u['postpone'],u['decline'])
        ceiling=offer['priceCents']+(u['ai']-outside)/s_offer
        buyer_ceilings.append(ceiling/100)
        if offer['priceCents']>0:buyer_scales.append(ceiling/offer['priceCents'])
    # Exact costs and collection ratio, up to penny rounding when prices change.
    out={'scenario':s['scenario'],'arm':run['arm'],'seed':run['seed'],
         'profitable':s['profitCents']>0,'insolvent':s['insolvent'],'accepted':n,'usefulAccepted':s['usefulAccepted'],
         'qualifiedContacted':len(qualified),'qualifiedAIChoices':len(chosen),
         'fullCostUSD':cost/100,'costLanesUSD':{k:v/100 for k,v in lanes.items()},
         'grossCollectionsUSD':g/100,'refundsUSD':r/100,'processingFeesUSD':fees/100,
         'fullProfitUSD':s['profitCents']/100,
         'meanAcceptedPriceUSD':mean_price/100 if n else None,
         'meanAcceptedHumanReferenceUSD':mean_human/100 if n else None,
         'minimumProportionalPriceScaleAtFixedMix':scale,
         'minimumMeanAcceptedPriceUSDAtFixedMix':mean_price*scale/100 if n and scale is not None else None,
         'completeCostPerAcceptedUSD':cost/n/100 if n else None,
         'maximumCompleteCostPerAcceptedUSDAtCurrentReceipts':(g-r)/n/100 if n else None,
         'minimumAcceptedVolumeAtFixedMix':minimum_accepted,
         'observedAcceptedVolumeAboveFixedMixBreakEven':n>=minimum_accepted if minimum_accepted is not None else False,
         'minimumAcceptedAtFixedProspectExposure':exposure_min,
         'minimumQualifiedBuyerAcceptanceAtFixedExposure':adoption,
         'minimumAdoptionFitsUnitInterval':adoption<=1 if adoption is not None else False,
         'medianQualifiedBuyerPriceCeilingUSDAtObservedBeliefs':dist(buyer_ceilings)['median'],
         'medianQualifiedBuyerProportionalPriceCeilingAtObservedBeliefs':dist(buyer_scales)['median'],
         'qualifiedOffersWithNonemptyBreakEvenPriceInterval':sum(scale<x for x in buyer_scales) if scale is not None else None,
         'fixedMixContributionPerAcceptedUSD':unit_contribution/100 if n else None,
         'fixedMixFixedCostUSD':fixed/100,
         'sourceJobLearningAlreadyInA':True,'sourceARechargedToRetention':False}
    return out

def alpha_thresholds(run):
    h,C=run['histories'],run['config'];assets={a['id']:a for a in run['assets']}
    campaigns={a['id']:a for a in h['campaigns']};invoices={i['id']:i for i in h['invoices']}
    results=[]
    for r in h['alphaAssessments']:
        asset=assets[r['assetId']];campaign=campaigns[asset['id']]
        if campaign['sourceKind']=='B_paid_job_retention':
            i=invoices[campaign['originInvoiceId']]
            assert i['collectedWeek'] is not None and i['collectedWeek']<=campaign['week']
            # Later refunds may occur; the original controller cannot know them.
            assert campaign['jobDevelopmentAlreadyChargedCents']>0
        complete=r['lifecycleCostCents']+r['evaluationCostCents']
        assert complete==r['completeLifecycleCostCents']
        delta=r['lowerDeltaCents'];uses=r['forecastEligibleUses'];minimum=max(1,C['alphaMinimumNetCents'])
        if delta is not None:assert math.floor(delta*uses-complete)==r['assessedLowerBoundNetCents']
        needed=ceil_ratio(complete+minimum,delta) if delta is not None else None
        ceiling=max(0,math.floor(delta*uses)-minimum) if delta is not None else 0
        f=campaign['forecast'] if r['kind']=='initial' else None
        row={'scenario':run['summary']['scenario'],'arm':run['arm'],'seed':run['seed'],
             'assetId':asset['id'],'kind':r['kind'],'sourceKind':campaign['sourceKind'],
             'gateVerdict':r['verdict'],'completeIncrementalLifecycleUSD':complete/100,
             'alreadyPaidSourceJobAUSD':campaign['jobDevelopmentAlreadyChargedCents']/100,
             'sourceAIncludedAgainInIncrementalThreshold':False,
             'conservativePerUseValueUSD':delta/100 if delta is not None else None,
             'forecastEligibleUses':uses,'minimumReuseForPositiveConservativeNet':needed,
             'maximumValueSupportedCompleteLifecycleUSD':ceiling/100,
             'gateLowerLifetimeNetUSD':r['assessedLowerBoundNetCents']/100,
             'latentCandidateProductive':asset['productive'],
             'independentClusters':r['independentClusters'],
             'evaluationCostUSD':r['evaluationCostCents']/100}
        if f:
            planned_life=f['forecastLifeWeeks'];rate=uses/planned_life
            upfront=complete-f['upkeepCents'];maintenance=asset['maintenanceCents'];reval=f['revalidationReserveCents']
            interval=C['assetRevalidationWeeks']
            lifetime=next((t for t in range(1,math.floor(planned_life)+1)
                           if delta is not None and delta*rate*t-(upfront+maintenance*t+(t//interval)*reval)>=minimum),None)
            other=complete-campaign['construction']['costCents']
            available=f['financialSnapshot']['availableCents']
            earned=f['financialSnapshot']['earnedAvailableCents']
            construction_ceiling=max(0,min(available-other,ceiling-other))
            row.update({'forecastApplicableUsesPerWeek':rate,'plannedUsefulLifetimeWeeks':planned_life,
                        'minimumUsefulWeeksIncludingWeeklyUpkeepAndRevalidation':lifetime,
                        'upfrontIncrementalUSDExcludingFutureUpkeep':upfront/100,
                        'maintenanceUSDPerWeek':maintenance/100,'revalidationReservedUSD':reval/100,
                        'maximumCashAndValueSupportedConstructionUSD':construction_ceiling/100,
                        'maximumEarnedSurplusAndValueSupportedConstructionUSD':max(0,min(earned-other,ceiling-other))/100,
                        'fullProspectiveHurdleFundableFromPriorOperatingSurplus':earned>=f['completeCostCents'],
                        'priorAvailableOperatingSurplusUSD':earned/100,
                        'minimumApplicableUsesPerWeekAtPlannedLife':(complete+minimum)/(delta*planned_life) if delta is not None and delta>0 else None,
                        'lifetimeThresholdAssumesBoundAndDemandPersist':True})
        results.append(row)
    admitted={e['id'] for e in h['network'] if e['type']=='modeled-admission'}
    return results,{'actualSimulatedGraphAdmissions':len(admitted),
                    'nonproductiveCandidateGraphAdmissions':sum(not assets[k]['productive'] for k in admitted),
                    'paidOriginGraphAdmissions':sum(assets[k]['sourceKind']=='B_paid_job_retention' for k in admitted),
                    'initialPositiveGateAssessments':sum(x['kind']=='initial' and x['gateVerdict']=='admit' for x in results),
                    'admittedAssetIds':sorted(admitted)}

def main():
    result_path=ROOT/'results/confirmation.json'
    if not result_path.exists():raise SystemExit('Confirmation not complete; no model or seed was run by this analysis.')
    freeze=load(ROOT/'protocol/freeze.json');assert sha(ROOT/'protocol/freeze.json')==FREEZE
    for name,value in freeze['sourceHashes'].items():assert sha(ROOT/name)==value, name
    result=load(result_path);archive=ROOT/'results/confirmation_ledgers.jsonl.gz'
    assert sha(archive)==result['ledgerArchive']['sha256']
    services=[];alphas=[];graph=[];seen=set()
    with gzip.open(archive,'rt') as handle:
        for line in handle:
            if not line.strip():continue
            run=json.loads(line);key=(run['summary']['scenario'],run['arm'],run['seed'])
            assert key not in seen;seen.add(key)
            services.append(service_thresholds(run));a,g=alpha_thresholds(run);alphas.extend(a)
            graph.append({'scenario':key[0],'arm':key[1],'seed':key[2],**g})
    assert len(services)==result['policyHistories']
    grouped=defaultdict(list)
    for row in services:grouped[(row['scenario'],row['arm'])].append(row)
    thresholds={}
    fields=['meanAcceptedPriceUSD','minimumMeanAcceptedPriceUSDAtFixedMix',
            'completeCostPerAcceptedUSD','maximumCompleteCostPerAcceptedUSDAtCurrentReceipts',
            'minimumAcceptedVolumeAtFixedMix','minimumAcceptedAtFixedProspectExposure',
            'minimumQualifiedBuyerAcceptanceAtFixedExposure','minimumProportionalPriceScaleAtFixedMix',
            'medianQualifiedBuyerPriceCeilingUSDAtObservedBeliefs',
            'medianQualifiedBuyerProportionalPriceCeilingAtObservedBeliefs']
    for (scenario,arm),rows in grouped.items():
        thresholds.setdefault(scenario,{})[arm]={
            'independentWorlds':len(rows),'zeroAcceptedWorlds':sum(x['accepted']==0 for x in rows),
            'noFinitePriceThresholdWorlds':sum(x['minimumProportionalPriceScaleAtFixedMix'] is None for x in rows),
            'noFiniteVolumeThresholdWorlds':sum(x['minimumAcceptedVolumeAtFixedMix'] is None for x in rows),
            'requiredAdoptionAboveOneWorlds':sum(x['minimumQualifiedBuyerAcceptanceAtFixedExposure'] is not None and x['minimumQualifiedBuyerAcceptanceAtFixedExposure']>1 for x in rows),
            'profitable':frequency(sum(x['profitable'] for x in rows),len(rows)),
            'insolvent':frequency(sum(x['insolvent'] for x in rows),len(rows)),
            **{field:dist([x[field] for x in rows]) for field in fields}}
    # Full signed paired enterprise differences, never clipped gross savings.
    full_rows={(r['scenario'],r['arm'],r['seed']):r for r in result['rows']}
    graph_rows={(r['scenario'],r['arm'],r['seed']):r for r in graph}
    contrasts={}
    for scenario in result['scenarios']:
        left=[r for r in result['rows'] if r['scenario']==scenario and r['arm']=='network']
        for right in ['same-price-beta','local','no-paid-learning','no-separate-research']:
            ds=[];admitted_ds=[];nonproductive_worlds=0
            for row in left:
                other=full_rows[(scenario,right,row['seed'])]
                delta=(row['profitCents']-other['profitCents'])/100;ds.append(delta)
                g=graph_rows[(scenario,'network',row['seed'])]
                if g['actualSimulatedGraphAdmissions']>0:admitted_ds.append(delta)
                nonproductive_worlds+=g['nonproductiveCandidateGraphAdmissions']>0
            contrasts.setdefault(scenario,{})['network_minus_'+right]={
                'fullSignedProfitDifferenceUSD':dist(ds),'positiveDifference':frequency(sum(x>0 for x in ds),len(ds)),
                'conditionalOnAnyGraphAdmission':{'worlds':len(admitted_ds),'fullSignedProfitDifferenceUSD':dist(admitted_ds),
                    'positiveDifference':frequency(sum(x>0 for x in admitted_ds),len(admitted_ds))},
                'networkWorldsWithNonproductiveAdmission':frequency(nonproductive_worlds,len(ds)),
                'notAnIsolatedPerAssetCausalEffect':True}
    output={'schema':'beyond-beta-confirmed-break-even-readout/v1','rootFreezeSHA256':FREEZE,
            'confirmationSHA256':sha(result_path),'ledgerSHA256':sha(archive),
            'policyHistoriesReconciled':len(services),'thresholds':thresholds,'confirmedSignedContrasts':contrasts,
            'alphaAssessments':len(alphas),
            'interpretation':[
                'All thresholds are algebra on saved traces, not new demand/price scenarios or optimized real-world advice.',
                'Price scaling holds tasks, buyer choices, errors, collection timing and default/refund outcomes fixed; it cannot establish willingness to pay.',
                'Buyer ceilings solve the declared best-response utility inequality at each saved belief/queue state; they are modeled preferences, not measured willingness to pay. Equality loses to the outside option.',
                'Volume thresholds retain the observed failure/acquisition burden per accepted artifact. Capacity and buyer response must still permit the implied workload.',
                'Required buyer acceptance fixes observed prospect exposure and completion conditional on an AI choice; values above1 are impossible under that frozen mixture.',
                'The Alpha threshold deducts remaining B and new C, never prepaid customer A twice. Future per-use value and reuse density must persist for the algebraic lifetime threshold.',
                'A positive gate is conditional observed evidence; actual full signed enterprise contrasts determine commercial incremental value.',
                'A world with negative incremental enterprise profit after admission does not alone prove a specific asset caused the loss.',
                'peerBenefitWork counts useful peer use, not a positive network causal effect; earnedFunded counts any earnings funding, not full lifecycle repayment.',
                'No-alpha-effect is a global mechanism-null sensitivity that also removes the declared effects of initially endowed capabilities.'
            ]}
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/'confirmed_break_even.json').write_text(json.dumps(output,indent=2)+'\n')
    with gzip.open(OUT/'confirmed_threshold_rows.jsonl.gz','wt') as handle:
        for row in services:handle.write(json.dumps({'type':'service',**row})+'\n')
        for row in alphas:handle.write(json.dumps({'type':'alpha',**row})+'\n')
        for row in graph:handle.write(json.dumps({'type':'graph',**row})+'\n')
    print(json.dumps({'complete':True,'policyHistories':len(services),'alphaAssessments':len(alphas),
                      'output':str(OUT/'confirmed_break_even.json')}))

if __name__=='__main__':main()
