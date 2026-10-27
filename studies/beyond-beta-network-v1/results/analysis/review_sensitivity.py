"""Post-freeze summary-only audit; no simulation, seeds or policy changes."""
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev
import hashlib, json, math

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/analysis'
FREEZE='850e6978a3946f8f9d01dd0c6920b49916e955d12b420a65c1241d3c5cd675f6'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):assert abs(a-b)<=1e-7*max(1,abs(a),abs(b)),(a,b)
def dist(xs):
 x=sorted(v for v in xs if v is not None and math.isfinite(v))
 if not x:return {'n':0,'mean':None,'meanMC95':None}
 m=mean(x);se=stdev(x)/math.sqrt(len(x)) if len(x)>1 else 0
 return {'n':len(x),'mean':m,'median':x[(len(x)-1)//2],
  'p05':x[math.floor((len(x)-1)*.05)],'p95':x[math.floor((len(x)-1)*.95)],
  'min':x[0],'max':x[-1],'meanMC95':[m-1.96*se,m+1.96*se]}
def freq(k,n):
 z=1.959963984540054;p=k/n;den=1+z*z/n
 mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return {'count':k,'n':n,'rate':p,'wilson95':[max(0,mid-half),min(1,mid+half)]}
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))

def main():
 p=ROOT/'results/sensitivity.json'
 if not p.exists():raise SystemExit('Sensitivity not complete. No model or seed was executed.')
 assert sha(ROOT/'protocol/freeze.json')==FREEZE
 F=load(ROOT/'protocol/freeze.json')
 for file,digest in F['sourceHashes'].items():assert sha(ROOT/file)==digest,file
 d=load(p);protocol=load(ROOT/'protocol/protocol.json')
 selection=load(ROOT/'protocol/selected_policies.json')
 reg=protocol['sensitivity'];seeds=reg['seeds']
 registered={(k,canonical(v)) for k,values in reg['oneFactors'] for v in values}
 assert len(registered)==136 and len(seeds)==20 and len(set(seeds))==20
 assert len(d['cases'])==136 and len(d['rows'])==5440 and d['auditedRuns']==5440
 assert {(c['parameter'],canonical(c['value'])) for c in d['cases']}==registered
 assert len({c['id'] for c in d['cases']})==136
 base=next(c for c in protocol['scenarios'] if c['id']=='central')
 groups=defaultdict(list)
 for r in d['rows']:groups[r['case']].append(r)
 summaries=[];same_config={};duplicates=0;admission_rows=[];campaign_rows=[]
 for c in d['cases']:
  parameter,value=c['parameter'],c['value'];assert c['C']=={**base,parameter:value}
  rr=groups[c['id']]
  assert len(rr)==40
  pairs={(r['arm'],r['seed']):r for r in rr}
  assert len(pairs)==40
  assert set(pairs)=={(a,s) for a in ['network','same-price-beta'] for s in seeds}
  for r in rr:
   assert r['policy']==selection['selected']['central']['network']['policy']['id']
   assert r['parameter']==parameter and r['value']==value
   assert r['ablation']==('none' if r['arm']=='network' else 'beta-only')
   assert r['automatedProviderHumanHours']==0 and r['actualJobs']==0 and r['actualCollectionsUSD']==0
  network=[pairs['network',s] for s in seeds]
  beta=[pairs['same-price-beta',s] for s in seeds]
  ds=[(a['profitCents']-b['profitCents'])/100 for a,b in zip(network,beta)]
  # Recompute critical published aggregates from the per-world rows.
  for arm,rows,label in [('network',network,'network'),('same-price-beta',beta,'beta')]:
   for metric in ['profitCents','costsCents','usefulAccepted','accepted','paidOriginCandidates',
                  'retentionCampaigns','successfulCampaigns','alphaUses','peerUsefulOutcomes','alphaFalseAdmissions']:
    x=[r[metric] for r in rows];published=c['summary'][label][metric]
    close(mean(x),published['mean']);assert published['n']==20
    assert min(x)==published['min'] and max(x)==published['max']
  close(mean(ds)*100,c['summary']['contrast']['differences']['profitCents']['mean'])
  assert c['summary']['contrast']['independentWorlds']==20
  assert sum(v>0 for v in ds)==c['summary']['contrast']['positiveProfitDifference']['count']
  # Exact duplicate configurations must reproduce the same economic histories.
  cfg=canonical(c['C'])
  comparable=[{k:v for k,v in r.items() if k not in ['case','parameter','value']} for r in rr]
  comparable.sort(key=lambda r:(r['arm'],r['seed']))
  if cfg in same_config:
   assert comparable==same_config[cfg];duplicates+=1
  else:same_config[cfg]=comparable
  admissions=sum(r['successfulCampaigns'] for r in network)
  paid=sum(r['paidOriginAdmissions'] for r in network)
  campaigns=sum(r['investmentCampaigns'] for r in network)
  false=sum(r['alphaFalseAdmissions'] for r in network)
  uses=sum(r['alphaUses'] for r in network)
  peer=sum(r['peerUsefulOutcomes'] for r in network)
  for a,b,delta in zip(network,beta,ds):
   if a['investmentCampaigns']>0:
    campaign_rows.append({'case':c['id'],'parameter':parameter,'value':value,'seed':a['seed'],
      'campaigns':a['investmentCampaigns'],'retentionCampaigns':a['retentionCampaigns'],
      'optionalResearchCampaigns':a['separateResearchCampaigns'],'failedCampaigns':a['failedCampaigns'],
      'rejectedAlpha':a['alphaRejected'],'productiveCampaigns':a['productiveCampaigns'],
      'admissions':a['successfulCampaigns'],'uses':a['alphaUses'],'peerUsefulJobs':a['peerUsefulOutcomes'],
      'BExpenseUSD':a['B_retentionReuseCostCents']/100,'CExpenseUSD':a['C_optionalResearchCostCents']/100,
      'assessmentExpenseUSD':a['alphaAssessmentCostCents']/100,
      'completeNetworkProfitUSD':a['profitCents']/100,'fullSignedNetworkMinusBetaUSD':delta})
   if a['successfulCampaigns']>0:
    admission_rows.append({'case':c['id'],'parameter':parameter,'value':value,'seed':a['seed'],
      'campaigns':a['investmentCampaigns'],'paidAdmissions':a['paidOriginAdmissions'],
      'allAdmissions':a['successfulCampaigns'],'falseAdmissions':a['alphaFalseAdmissions'],
      'uses':a['alphaUses'],'peerUsefulJobs':a['peerUsefulOutcomes'],
      'completeNetworkProfitUSD':a['profitCents']/100,'fullSignedNetworkMinusBetaUSD':delta,
      'usefulOutcomeDifference':a['usefulAccepted']-b['usefulAccepted']})
  total_contacted=sum(r['contacted'] for r in network)
  full=dist([r['profitCents']/100 for r in network]);contrast=dist(ds)
  if not admissions:
   interpretation='No acquired Alpha was admitted; any profit contrast arises from discovery and its operational consequences.'
  elif mean(ds)<=0:
   interpretation='Acquired Alpha appears in this stress, but mean complete incremental enterprise profit is nonpositive.'
  else:
   interpretation='Positive mean complete policy contrast with some admissions; descriptive one-factor stress, not independent confirmation or isolated asset causality.'
  row={'case':c['id'],'parameter':parameter,'value':value,'independentWorlds':20,
    'fullNetworkProfitUSD':full,'fullBetaProfitUSD':dist([r['profitCents']/100 for r in beta]),
    'fullSignedNetworkMinusBetaUSD':contrast,'positiveIncrementalProfit':freq(sum(x>0 for x in ds),20),
    'profitable':freq(sum(r['profitCents']>0 for r in network),20),
    'insolvent':freq(sum(r['insolvent'] for r in network),20),
    'zeroUseful':freq(sum(r['usefulAccepted']==0 for r in network),20),
    'usefulOutcomes':dist([r['usefulAccepted'] for r in network]),
    'acceptedOutcomes':dist([r['accepted'] for r in network]),
    'completeCostUSD':dist([r['costsCents']/100 for r in network]),
    'fullCostPerUsefulUSD':dist([r['fullCostPerUsefulCents']/100 if r['fullCostPerUsefulCents'] is not None else None for r in network]),
    'meanOfferedPriceRatio':dist([r['meanOfferedPriceRatio'] for r in network]),
    'pooledAIChoicesPerContacted':sum(r['aiChoices'] for r in network)/total_contacted if total_contacted else None,
    'meanContacted':mean(r['contacted'] for r in network),'meanPotentialProspects':mean(r['potentialProspects'] for r in network),
    'capacityRefusals':dist([r['capacityRefusals'] for r in network]),
    'queueP95Weeks':dist([r['queueP95Weeks'] for r in network]),
    'escapedErrorShare':dist([r['escapedErrorShare'] for r in network]),
    'campaigns':campaigns,'failedCampaigns':sum(r['failedCampaigns'] for r in network),
    'rejectedAlpha':sum(r['alphaRejected'] for r in network),
    'productiveCampaigns':sum(r['productiveCampaigns'] for r in network),
    'retentionCampaigns':sum(r['retentionCampaigns'] for r in network),
    'optionalResearchCampaigns':sum(r['separateResearchCampaigns'] for r in network),
    'paidCandidates':sum(r['paidOriginCandidates'] for r in network),
    'admissions':admissions,'paidOriginAdmissions':paid,'falseAdmissions':false,
    'worldsWithAdmission':sum(r['successfulCampaigns']>0 for r in network),
    'totalUses':uses,'peerUseAttempts':sum(r['alphaPeerUses'] for r in network),'usefulPeerJobs':peer,
    'interpretation':interpretation}
  summaries.append(row)
 by_parameter=defaultdict(list)
 for r in summaries:by_parameter[r['parameter']].append(r)
 executed={}
 for parameter in ['humanReference','buyerValueMedian','prospectsMonthly','acquisitionCostPerProspect',
                   'improvementProbability','initialCompletionBelief','tokenMultiplier','computeMultiplier',
                   'collectionDelayWeeks','concurrency','inputQuotaWeekly','cpuHoursWeekly',
                   'alphaProbeCount','workflowLatencyMultiplier','deadlineMultiplier','setupCost']:
  rows=sorted(by_parameter[parameter],key=lambda r:r['value'])
  positive=[r['value'] for r in rows if r['fullNetworkProfitUSD']['mean']>0]
  transitions=[]
  for left,right in zip(rows,rows[1:]):
   if (left['fullNetworkProfitUSD']['mean']>0)!=(right['fullNetworkProfitUSD']['mean']>0):
    transitions.append({'betweenExecutedValues':[left['value'],right['value']],
      'leftMeanUSD':left['fullNetworkProfitUSD']['mean'],'rightMeanUSD':right['fullNetworkProfitUSD']['mean']})
  executed[parameter]={'values':[r['value'] for r in rows],'positiveMeanExecutedValues':positive,
    'adjacentSignChanges':transitions,'rows':rows,
    'noContinuousThresholdOrReoptimizedPriceClaim':True}
 output={'schema':'beyond-beta-summary-sensitivity-audit/v1','sourceHashes':{
   'freeze':FREEZE,'sensitivity':sha(p),'selection':sha(ROOT/'protocol/selected_policies.json')},
  'counts':{'registeredCases':136,'worldsPerCase':20,'parameterWorldInstances':2720,
    'policyHistories':5440,'uniqueExogenousWorldSeeds':20,'duplicateConfigControls':duplicates},
  'allRegisteredCasesPairsAndPublishedAggregatesReconciled':True,
  'sameConfigurationDeterminismVerified':True,
  'caseSummaries':summaries,'executedPointThresholds':executed,'admissionWorldRows':admission_rows,
  'campaignWorldRows':campaign_rows,'distinctSeedsWithAnyCampaign':len({r['seed'] for r in campaign_rows}),
  'positiveMeanCasesWithAdmissions':[r['case'] for r in summaries if r['fullSignedNetworkMinusBetaUSD']['mean']>0 and r['admissions']>0],
  'positiveMeanCasesWithoutAdmissions':[r['case'] for r in summaries if r['fullSignedNetworkMinusBetaUSD']['mean']>0 and r['admissions']==0],
  'casesWithPositiveMonteCarloLowerDifference':[r['case'] for r in summaries if r['fullSignedNetworkMinusBetaUSD']['meanMC95'][0]>0],
  'casesWithNegativeMonteCarloUpperDifference':[r['case'] for r in summaries if r['fullSignedNetworkMinusBetaUSD']['meanMC95'][1]<0],
  'recordOccurrencesNotIndependentTrials':{k:sum(r[k] for r in summaries) for k in
     ['campaigns','retentionCampaigns','optionalResearchCampaigns','failedCampaigns','rejectedAlpha','productiveCampaigns','admissions','paidOriginAdmissions','falseAdmissions','totalUses','usefulPeerJobs']},
  'limitations':[
   'Only20 distinct world seeds are reused across136 settings. Per-case paired worlds are the statistical units;2720parameter/world instances and5440policy histories are not independent replications.',
   'One-factor stresses retain the frozen central selected policy; they do not reoptimize price, reserves or investment rules.',
   'Human-reference stresses simultaneously alter the matched human offer and market-referenced agent price; they are not pure own-price elasticity estimates.',
   'Reported sign-change brackets concern executed discrete points and mean full profit, not a proven continuous threshold.',
   'Positive policy gain with zero admissions is not incremental learned Alpha.',
   'Positive gain in a case with admissions does not isolate individual asset causality and is not new confirmation.',
   'alphaRejected counts final admission failures, which can include an adverse assessment, stale Beta or graph rejection; the exact failure stage is unavailable from summary fields.',
   'productiveCampaigns uses latent productivity together with the campaign planned-admission flag, not final graph admission; use successfulCampaigns and paidOriginAdmissions for actual simulated admission counts.',
   'Cases with positive point estimates or intervals are selected from136correlated stresses; no unregistered multiple-comparison claim is made.',
   'Zero insolvencies in20worlds has a16.1% Wilson95upper bound, not proof of a5%risk limit.',
   'Counts pooled over settings are record occurrences, not independent inventions or independent customer trials.',
   'Tariffs and human labor anchors are sourced; task capability, buyer preferences, capacity, latency and asset effects remain model assumptions.'
  ]}
 OUT.mkdir(exist_ok=True,parents=True)
 (OUT/'sensitivity_readout.json').write_text(json.dumps(output,indent=2)+'\n')
 print(json.dumps({'complete':True,'cases':136,'histories':5440,'uniqueSeeds':20,
  'occurrences':output['recordOccurrencesNotIndependentTrials'],
  'positiveMeanWithAdmissions':output['positiveMeanCasesWithAdmissions'],
  'positiveMeanWithoutAdmissions':output['positiveMeanCasesWithoutAdmissions'],
  'output':str(OUT/'sensitivity_readout.json')}))
if __name__=='__main__':main()

