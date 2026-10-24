# SPDX-License-Identifier: Apache-2.0
import argparse, csv, gzip, hashlib, json
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out');args=p.parse_args()
source=Path(args.input);out=Path(args.out) if args.out else source/'analysis';out.mkdir(parents=True,exist_ok=True)
raw=source/'missions.jsonl.gz' if (source/'missions.jsonl.gz').exists() else source/'missions.jsonl'
ledger=source/'ledgers.jsonl.gz' if (source/'ledgers.jsonl.gz').exists() else source/'ledgers.jsonl'
opener=gzip.open if raw.suffix=='.gz' else open
with opener(raw,'rt') as stream:rows=[json.loads(line) for line in stream]
metrics=json.loads((source/'metrics.json').read_text());rng=np.random.default_rng(20261023)
methods=metrics['methods'];conditions=metrics['scenarios'];seeds=metrics['seeds'];epochs=metrics['epochs']
complete=[x for x in rows if x['status']=='complete'];bad=[x for x in rows if x['status']!='complete']
index={(x['scenario'],x['seed'],x['epoch'],x['method']):x for x in complete}
expected=len(methods)*len(conditions)*len(seeds)*epochs
if len(rows)!=expected or bad:raise RuntimeError(f'Incomplete campaign: {len(rows)}/{expected} rows; {len(bad)} failures. Preserve raw data; do not silently omit.')
if len(index)!=len(complete):raise RuntimeError('Duplicate mission/method rows')
def cpu(d):return (d.get('user',0)+d.get('system',0))/1000
def values(row):
 m=row['measured'];o=row['outcome']
 return {'utility':o['utility'],'completedJobs':o['completedJobs'],'failedJobs':o['failures'],'sampleAcquisitions':o['attemptedJobs'],'calibrationAcquisitions':o['calibrations'],'diagnosticAcquisitions':row['diagnosticAcquisitions'],'instrumentTicks':o['resourceTicks'],'policyCpuMs':cpu(m['methodCpuMicros']),'evidenceCpuMs':cpu(m['evidenceCpuMicros']),'externalEvaluatorCpuMs':cpu(m['externalEvaluatorCpuMicros']),'recorderSetupCpuMs':cpu(m.get('recorderSetupCpuMicros',{})),'accountedRowCpuMs':cpu(m['methodCpuMicros'])+cpu(m['evidenceCpuMicros'])+cpu(m['externalEvaluatorCpuMicros'])+cpu(m.get('recorderSetupCpuMicros',{})),'policyWallMs':m['methodWallMs'],'evidenceWallMs':m['evidenceMs'],'receiptBytes':row.get('receipt',{}).get('receiptBytes',0) if row.get('receipt') else 0,'proofBytes':row['result'].get('proofBytes',0)}
keys=list(values(complete[0]));clusters={};summary=[]
for condition in conditions:
 for method in methods:
  matrix=np.array([[np.mean([values(index[condition,seed,epoch,method])[key] for epoch in range(epochs)]) for key in keys] for seed in seeds])
  clusters[condition,method]=matrix
  resample=rng.integers(0,len(seeds),size=(10000,len(seeds)))
  boot=matrix[resample].mean(axis=1)
  entry={'condition':condition,'method':method,'clusters':len(seeds),'epochsPerCluster':epochs}
  for i,key in enumerate(keys):entry[key]={'mean':float(matrix[:,i].mean()),'ci95':[float(x) for x in np.percentile(boot[:,i],[2.5,97.5])],'total':float(matrix[:,i].sum()*epochs)}
  summary.append(entry)
contrasts=[];u=keys.index('utility');c=keys.index('accountedRowCpuMs')
for condition in conditions:
 for other in ['idea','greedy','disclosed','clone','expert','adaptive-expert']:
  left=clusters[condition,'verified'];right=clusters[condition,other];resample=rng.integers(0,len(seeds),size=(10000,len(seeds)))
  delta=left-right;boot=delta[resample].mean(axis=1);ratio=(left[resample][:,:,u].mean(axis=1)-right[resample][:,:,u].mean(axis=1))/right[resample][:,:,u].mean(axis=1)
  contrasts.append({'condition':condition,'reference':other,'utilityDifference':float(delta[:,u].mean()),'utilityDifferenceCI95':[float(x) for x in np.percentile(boot[:,u],[2.5,97.5])],'relativeUtilityDifference':float((left[:,u].mean()-right[:,u].mean())/right[:,u].mean()),'relativeUtilityDifferenceCI95':[float(x) for x in np.percentile(ratio,[2.5,97.5])],'cpuDifferenceMs':float(delta[:,c].mean()),'cpuDifferenceCI95':[float(x) for x in np.percentile(boot[:,c],[2.5,97.5])],'interpretation':'primary' if condition=='ordinary' and other=='idea' else 'descriptive-secondary'})
cloneMismatch=[];modelMismatch=[];truthRejected=0
for condition in conditions:
 for seed in seeds:
  for epoch in range(epochs):
   a=index[condition,seed,epoch,'verified'];b=index[condition,seed,epoch,'clone'];e=index[condition,seed,epoch,'expert']
   if a['result']['plan']!=b['result']['plan'] or a['outcome']!=b['outcome']:cloneMismatch.append([condition,seed,epoch])
   if a['result']['objective']!=e['result']['objective']:modelMismatch.append([condition,seed,epoch])
   if a['outcome']['failures']>0:truthRejected+=1
temporal=[]
for condition in conditions:
 for method in methods:
  cumulative=0
  for epoch in range(epochs):
   v=np.array([index[condition,seed,epoch,method]['outcome']['utility'] for seed in seeds]);cumulative+=v.mean()
   temporal.append({'condition':condition,'method':method,'epoch':epoch,'meanUtility':float(v.mean()),'cumulativeMeanUtility':float(cumulative)})
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
result={'schema':'nova-seeds-analysis/v1','rawSha256':digest(raw),'ledgerSha256':digest(ledger),'rows':len(rows),'pairedMissions':len(rows)//len(methods),'clusters':len(seeds),'summary':summary,'contrasts':contrasts,'exactChecks':{'cloneMismatches':cloneMismatch,'stationaryModelObjectiveMismatches':modelMismatch,'verifiedMissionsWithRealizedFailures':truthRejected},'temporal':temporal,'uncertainty':'32 paired seed clusters; 10000 percentile bootstrap resamples; descriptive secondary intervals; no calendar-market inference','measuredCampaign':metrics,'monetary':{'observedCustomerRevenue':0,'liveTransactions':0,'fullCostProfit':None,'humanHours':None,'authoringModelCost':None,'instrumentCost':None,'demandEvidence':None}}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
flat=[{'condition':x['condition'],'method':x['method'],**{k:x[k]['mean'] for k in keys}} for x in summary]
with (out/'means.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
with (out/'temporal.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(temporal[0]));w.writeheader();w.writerows(temporal)
primary=next(x for x in contrasts if x['interpretation']=='primary')
print(json.dumps({'rows':len(rows),'missions':len(rows)//len(methods),'primary':primary,'cloneMismatchCount':len(cloneMismatch),'modelMismatchCount':len(modelMismatch),'output':str(out/'summary.json')},indent=2))
