import collections,hashlib,json,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'results/confirmation-v1'
OUT=Path(__file__).resolve().parent
start=time.process_time();source={};trials={}
def read(path):
 source[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest();return json.loads(path.read_text())
for p in sorted(DATA.glob('trials/*/summary.json')):
 s=read(p);r=read(p.parent/'rows.json');e=read(p.parent/'events.json');c=read(p.parent/'custody_status.json')
 trials[(s['regime']['name'],s['seed'],s['arm'])]={'summary':s,'rows':{x['id']:x for x in r},'events':e,'custody':c}
scoped=sorted((regime,seed) for regime,seed,arm in trials if arm=='flywheel' and trials[(regime,seed,arm)]['rows']['C']['details']['method']=='construct-low-rank')
assert len(scoped)==18 and collections.Counter(r for r,s in scoped)=={'recurring':6,'rare':6,'maintenance':6}
construction=[];pairs=[]
for regime,seed in scoped:
 for arm in ['flywheel','parent_rebuilt','equivalent','native_refactor','conventional_reuse','direct_specialist','no_reinvestment']:
  t=trials[(regime,seed,arm)];r=t['rows']['C'];construction.append({'regime':regime,'seed':seed,'arm':arm,'method':r['details']['method'],'qualified':r['qualified'],'algorithm_solve_persistence_cpu_ms':r['algorithm_cpu_ms'],'whole_dispatched_cpu_ms':r['cpu_ms'],'checker_cpu_ms':r['checker_cpu_ms'],'node_cpu_ms':r['node_cpu_ms'],'parent_api_calls':r['details'].get('parent_calls',0),'construction_parent_block_calls':r['details'].get('construction_parent_calls',0),'direction_rhs_columns':r['details'].get('rank',0),'account':r['account'],'input_digest':r['input_digest'],'preceding_receipt':r['details'].get('preceding_receipt')})
 assert len({trials[(regime,seed,arm)]['rows']['C']['input_digest'] for arm in ['flywheel','parent_rebuilt','equivalent','native_refactor','conventional_reuse','direct_specialist','no_reinvestment']})==1
aggregates=[]
for arm in ['flywheel','parent_rebuilt','equivalent','native_refactor','conventional_reuse','direct_specialist','no_reinvestment']:
 rr=[r for r in construction if r['arm']==arm]
 aggregates.append({'arm':arm,'paired_streams':len(rr),'qualified':sum(r['qualified'] for r in rr),'mean_algorithm_solve_persistence_cpu_ms':float(np.mean([r['algorithm_solve_persistence_cpu_ms'] for r in rr])),'mean_whole_dispatched_cpu_ms':float(np.mean([r['whole_dispatched_cpu_ms'] for r in rr])),'mean_checker_cpu_ms':float(np.mean([r['checker_cpu_ms'] for r in rr])),'construction_parent_block_calls':sum(r['construction_parent_block_calls'] for r in rr),'direction_rhs_columns':sum(r['direction_rhs_columns'] for r in rr)})
for reference in ['parent_rebuilt','equivalent','native_refactor','conventional_reuse','direct_specialist','no_reinvestment']:
 for field in ['algorithm_cpu_ms','cpu_ms']:
  groups=[];wins=0
  for regime in ['recurring','rare','maintenance']:
   vals=[]
   for rg,seed in scoped:
    if rg!=regime:continue
    a=trials[(regime,seed,'flywheel')]['rows']['C'][field];b=trials[(regime,seed,reference)]['rows']['C'][field];vals.append((a,b));wins+=a<b
   groups.append(np.array(vals))
  rng=np.random.default_rng(20261026);a=np.zeros(10000);b=np.zeros(10000)
  for g in groups:
   ix=rng.integers(0,len(g),size=(10000,len(g)));a+=g[ix,0].sum(axis=1);b+=g[ix,1].sum(axis=1)
  total_a=sum(g[:,0].sum() for g in groups);total_b=sum(g[:,1].sum() for g in groups)
  pairs.append({'reference':reference,'field':field,'streams':18,'ratio_of_means':float(total_a/total_b),'mean_paired_difference_ms':float((total_a-total_b)/18),'streams_with_lower_flywheel_cost':int(wins),'descriptive_95_ci_ratio':np.quantile(a/b,[.025,.975]).tolist(),'status':'POST_HOC_DESCRIPTIVE_SECONDARY_NOT_ADMISSION_TEST','resamples':10000,'seed':20261026})
execution=[]
for (regime,seed,arm),t in trials.items():
 b=[r for mid,r in t['rows'].items() if mid.startswith('B')];d=[r for mid,r in t['rows'].items() if mid.startswith('D')]
 execution.append({'regime':regime,'seed':seed,'arm':arm,'B_qualified':sum(r['qualified'] for r in b),'B_parent_using_qualified':sum(r['qualified'] and r['details'].get('parent_calls',0)>0 for r in b),'B_algorithm_cpu_ms':sum(r['algorithm_cpu_ms'] for r in b),'B_whole_dispatched_cpu_ms':sum(r['cpu_ms'] for r in b),'D_qualified':sum(r['qualified'] for r in d),'D_parent_using_qualified':sum(r['qualified'] and r['details'].get('parent_calls',0)>0 for r in d),'D_algorithm_cpu_ms':sum(r['algorithm_cpu_ms'] for r in d),'D_whole_dispatched_cpu_ms':sum(r['cpu_ms'] for r in d),'C_method':t['rows']['C']['details']['method'],'C_valid_parent_child':t['rows']['C']['qualified'] and t['rows']['C']['details'].get('construction_parent_calls',0)>0,'restored':t['rows'].get('RESTORE',{}).get('qualified',False),'released_quota_ms':t['custody']['earned_released_us']/1000,'earned_debit_ms':t['custody']['accounts']['earned']['spent_us']/1000,'earned_remaining_ms':t['custody']['accounts']['earned']['available_us']/1000,'service_debit_ms':t['custody']['accounts']['service']['spent_us']/1000,'external_improvement_debit_ms':t['custody']['accounts']['improvement']['spent_us']/1000,'control_cpu_ms':t['summary']['setup_custody_artifact_io_cpu_ms'],'whole_cpu_ms':t['summary']['total_cpu_ms']})
regime_aggregates=[]
for regime in ['recurring','rare','wide_change','maintenance']:
 for arm in ['flywheel','conventional_reuse','direct_specialist','parent_rebuilt','equivalent','native_refactor','no_reinvestment']:
  rr=[r for r in execution if r['regime']==regime and r['arm']==arm]
  regime_aggregates.append({'regime':regime,'arm':arm,'streams':len(rr),**{k:sum(r[k] for r in rr) for k in ['B_qualified','B_parent_using_qualified','D_qualified','D_parent_using_qualified','C_valid_parent_child','released_quota_ms','earned_debit_ms','earned_remaining_ms','service_debit_ms','external_improvement_debit_ms','control_cpu_ms','whole_cpu_ms']},'mean_whole_cpu_ms':float(np.mean([r['whole_cpu_ms'] for r in rr]))})
A=trials[next(k for k in trials if k[2]=='flywheel')]
freeze=json.loads((ROOT/'protocol/FREEZE.json').read_text());verification={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in freeze['files'].items()};assert all(verification.values())
result={'schema':'earned-turn-mechanism-attribution/v1','status':'DESCRIPTIVE_FROZEN_ARTIFACT_ANALYSIS_NO_RERUN','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'frozen_source':freeze['freeze_sha256'],'frozen_files_verified':len(verification),'scope':'Eighteen prespecified low-rank scoped streams (6each recurring,rare,maintenance); rank32wide-change streams are separate. Allpaired Cinputs identical.','construction_rows':construction,'construction_aggregates':aggregates,'construction_paired_descriptive':pairs,'execution_rows':execution,'regime_aggregates':regime_aggregates,'limits':['C algorithmCPU includes construction, one solve andNPZ persistence. It is not a pure constructor microbenchmark.','NativeC additionally uses the generic full-input inspect preflight. LowrankC uses parent/delta validation and trusted prevalidated IDs. Both have an independent final checker. The nativeC phase gap includes this asymmetry.','Exact reconstruction and equivalent arms use the same low-rank construction path plus construction/persistence of a new parent; this is the cleaner causal inheritance contrast.','Descriptive secondary intervals were added after outcomes; they do not replace the registered primary gate or justify additional confirmatory superiority claims.','Allarms except no-reinvestment receive identical releasedquota opportunities. This is external allowance reuse, not resource creation or measured economic margin.','Parentcalls are producer instrumentation, independently attributed to phases andcheckedoutputs, not independently traced CPUinstructions.'],'artifact_hashes':source,'analysis_cpu_ms':1000*(time.process_time()-start)}
(OUT/'MECHANISM_ATTRIBUTION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'construction_aggregates':aggregates,'construction_pairs':pairs,'frozen_files_unchanged':len(verification),'output':str(OUT/'MECHANISM_ATTRIBUTION.json')},indent=2))
