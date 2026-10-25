import argparse,collections,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
from checker import check,inspect

ARMS=('flywheel','conventional_reuse','direct_specialist','parent_rebuilt','equivalent','native_refactor','no_reinvestment')
REGIMES=('recurring','rare','wide_change','maintenance')
REPS=10000
BOOTSTRAP_SEED=20261025

def canonical(obj,unicode=False):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False,ensure_ascii=not unicode).encode()
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()
def wbdigest(domain,obj):return hashlib.sha256(('successor-omega/v1:'+domain+'\0').encode()+canonical(obj,True)).hexdigest()
def file_hash(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b,tol=1e-6):return isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol

def bootstrap_pairs(records,reference):
 bykey={(r['regime'],r['seed'],r['arm']):r for r in records}
 groups=[]
 for regime in REGIMES:
  seeds=sorted({r['seed'] for r in records if r['regime']==regime and r['arm']=='flywheel'})
  group=[]
  for seed in seeds:
   a,b=bykey.get((regime,seed,'flywheel')),bykey.get((regime,seed,reference))
   if a is None or b is None or a['total_cpu_ms'] is None or b['total_cpu_ms'] is None:return {'status':'INCOMPLETE_PAIRS'}
   group.append((a['total_cpu_ms'],b['total_cpu_ms']))
  if group:groups.append(np.asarray(group,dtype=float))
 if not groups:return {'status':'NO_PAIRS'}
 rng=np.random.default_rng(BOOTSTRAP_SEED);a_samples=np.zeros(REPS);b_samples=np.zeros(REPS)
 for group in groups:
  indexes=rng.integers(0,len(group),size=(REPS,len(group)))
  a_samples+=group[indexes,0].sum(axis=1);b_samples+=group[indexes,1].sum(axis=1)
 av=sum(g[:,0].sum() for g in groups);bv=sum(g[:,1].sum() for g in groups)
 if bv<=0 or np.any(b_samples<=0):return {'status':'NONPOSITIVE_REFERENCE'}
 ratios=a_samples/b_samples;ci=np.quantile(ratios,[.025,.975],method='linear')
 return {'status':'COMPLETE','reference':reference,'paired_streams':sum(len(g) for g in groups),'point_ratio_of_means':av/bv,'percentile_95_ci':[float(ci[0]),float(ci[1])],'resamples':REPS,'seed':BOOTSTRAP_SEED,'sampling':'Paired stream bootstrap within each workload regime; retain each stratum size, then ratio of pooled means. No task-level independence.'}

def run(root,expected_source,development=False,output=None):
 started=time.perf_counter();cpu=time.process_time();root=Path(root).resolve();issues=[];manifest={};records=[];all_checks=[];changes_by_stream={};pair_inputs=collections.defaultdict(dict)
 protocol_path=Path(__file__).resolve().parents[1]/'protocol/CONFIRMATORY_PROTOCOL.json';protocol=json.loads(protocol_path.read_text())
 if protocol['independent_units']!=24 or protocol['replicates_per_regime']!=6 or tuple(protocol['arms'])!=ARMS or protocol['uncertainty']['bootstrap_replicates']!=REPS or protocol['uncertainty']['seed']!=BOOTSTRAP_SEED:raise ValueError('PROTOCOL_ANALYSIS_MISMATCH')
 def issue(folder,kind,detail):issues.append({'trial':str(folder.relative_to(root)) if folder!=root else '.', 'kind':kind,'detail':str(detail)})
 def need(condition,folder,kind,detail):
  if not condition:issue(folder,kind,detail)
  return condition
 def load(path):
  manifest[str(path.relative_to(root))]={'bytes':path.stat().st_size,'sha256':file_hash(path)}
  return json.loads(path.read_text())
 summaries=sorted(root.rglob('summary.json'))
 if not summaries:raise ValueError('NO_TRIAL_SUMMARIES')
 for summary_path in summaries:
  folder=summary_path.parent
  try:s=load(summary_path)
  except Exception as e:issue(folder,'SUMMARY_UNREADABLE',e);continue
  if not all(k in s for k in ['seed','regime','arm']):issue(folder,'SUMMARY_IDENTITY_FIELDS','seed/regime/arm required');continue
  regime=s['regime']['name'] if isinstance(s['regime'],dict) else s['regime'];arm=s['arm'];seed=s['seed'];fresh=2 if regime=='rare' else 12;offered=11+fresh
  need(regime in REGIMES and arm in ARMS,folder,'UNKNOWN_REGISTERED_ARM_OR_REGIME',f'{arm}/{regime}')
  need(s.get('source_hash')==expected_source,folder,'SOURCE_IDENTITY',s.get('source_hash'))
  need(s.get('offered')==offered,folder,'OFFERED_DENOMINATOR',(s.get('offered'),offered))
  rows=load(folder/'rows.json') if (folder/'rows.json').exists() else []
  tasks=load(folder/'tasks.json') if (folder/'tasks.json').exists() else {}
  events=load(folder/'events.json') if (folder/'events.json').exists() else []
  custody=load(folder/'custody_status.json') if (folder/'custody_status.json').exists() else None
  if custody=={}:custody=None
  ids=[r['id'] for r in rows];need(len(ids)==len(set(ids)),folder,'DUPLICATE_OUTPUT_ROWS',ids)
  if not rows and not s.get('failure'):issue(folder,'NO_VERIFIABLE_RAW_ROWS','No raw rows and no recorded terminal failure.')
  vector_path=folder/'solutions.npz';vectors={}
  if vector_path.exists():
   manifest[str(vector_path.relative_to(root))]={'bytes':vector_path.stat().st_size,'sha256':file_hash(vector_path)}
   with np.load(vector_path,allow_pickle=False) as z:vectors={k:z[k].tolist() for k in z.files}
  checked_by_id={};rowmap={r['id']:r for r in rows};taskids={};methods=collections.Counter();parent_qualified=0;parent_api_calls=0
  for row in rows:
   mid=row['id'];methods[row.get('details',{}).get('method','unknown')]+=1
   if mid not in tasks:issue(folder,'MISSING_TASK',mid);continue
   task=tasks[mid];taskids[mid]=digest(task)
   need(taskids[mid]==row.get('input_digest'),folder,'TASK_DIGEST',mid)
   oid=digest({k:task[k] for k in ['n','edges','ground']})
   need(oid==row.get('operator_digest'),folder,'OPERATOR_DIGEST',mid)
   vector=vectors.get(mid)
   if vector is not None:
    independent=check(task,vector)
    need(digest(vector)==row.get('solution_digest'),folder,'SOLUTION_DIGEST',mid)
    need(independent['valid']==row.get('checker',{}).get('valid'),folder,'CHECKER_DISAGREEMENT',mid)
    for key in ['relative_residual','energy_error','max_abs_residual']:
     need(close(independent.get(key),row.get('checker',{}).get(key),1e-12),folder,'CHECKER_VALUE',f'{mid}:{key}')
   else:
    independent={'valid':False,'reason':inspect(task) or 'NO_STORED_OUTPUT'}
    need(not row.get('checker',{}).get('valid',False),folder,'MISSING_ACCEPTED_VECTOR',mid)
   checked_by_id[mid]=bool(independent['valid'] and row.get('accepted'))
   need(row.get('qualified')==checked_by_id[mid] and row.get('valid')==checked_by_id[mid],folder,'ACCEPTANCE_OUTCOME',mid)
   all_checks.append({'trial':str(folder.relative_to(root)),'id':mid,'independently_valid':independent['valid'],'accepted':row.get('accepted'),'qualified':checked_by_id[mid],'reason':independent['reason']})
   if mid.startswith('D') and checked_by_id[mid] and row.get('details',{}).get('parent_calls',0)>0:
    parent_qualified+=1;parent_api_calls+=row['details']['parent_calls']
   pack_path=folder/(mid+'-pack.json')
   if not pack_path.exists():issue(folder,'MISSING_WORKBENCH_PACK',mid);continue
   pack=load(pack_path);body={k:v for k,v in pack.items() if k!='integrityDigest'}
   need(wbdigest('workbench-pack',body)==pack.get('integrityDigest'),folder,'WORKBENCH_PACK_INTEGRITY',mid)
   need(wbdigest('workbench-release',pack['frozen'])==pack.get('releaseDigest'),folder,'WORKBENCH_RELEASE_INTEGRITY',mid)
   semantic={k:v for k,v in pack['spec'].items() if k not in ['name','language']}
   need(wbdigest('workbench-mission',semantic)==pack['frozen'].get('missionDigest'),folder,'WORKBENCH_MISSION_INTEGRITY',mid)
   need(pack['frozen'].get('sourceHash')==expected_source,folder,'PACK_SOURCE_IDENTITY',mid)
   input_record=json.loads(pack['spec']['inputs']['payload_json'])
   need(input_record.get('task_digest')==taskids[mid] and input_record.get('operator_digest')==oid and input_record.get('mission')==mid,folder,'PACK_WORLD_BINDING',mid)
   need(pack.get('evaluation',{}).get('authority')==[] and pack['frozen'].get('authority')==[] and pack.get('evaluation',{}).get('admission')=='HOLD',folder,'INHERITED_AUTHORITY_OR_PROOF',mid)
   report=None
   for artifact in pack['result']['artifacts']:
    content={k:v for k,v in artifact.items() if k!='digest'}
    need(wbdigest('workbench-artifact',content)==artifact.get('digest'),folder,'ARTIFACT_INTEGRITY',mid)
    if artifact['name']=='numerical-result.json':report=json.loads(artifact['content'])
   if report:
    need(not report.get('authority') and not report.get('proof'),folder,'REPORT_AUTHORITY',mid)
    if report.get('valid'):
     need(report.get('task_digest')==taskids[mid] and report.get('solution_digest')==row.get('solution_digest'),folder,'REPORT_BINDING',mid)
   if custody is not None:
    request=custody.get('requests',{}).get(mid)
    if request is None:issue(folder,'MISSING_CUSTODY_REQUEST',mid)
    else:
     receipt=request.get('receipt',{})
     need(digest(receipt)==request.get('receipt_digest')==row.get('receipt_digest'),folder,'RECEIPT_DIGEST',mid)
     need(receipt.get('task_digest')==taskids[mid] and receipt.get('solution_digest')==row.get('solution_digest') and receipt.get('source_hash')==expected_source and receipt.get('pack_digest')==pack['integrityDigest'],folder,'RECEIPT_BINDING',mid)
     need(request.get('accepted')==row.get('accepted'),folder,'RECEIPT_ACCEPTANCE',mid)
     need(request.get('charged_us')==math.ceil(row['cpu_ms']*1000),folder,'CPU_CHARGE',mid)
     need(request.get('account')==row.get('account'),folder,'CHARGE_ACCOUNT',mid)
  useful=['A']+[f'B{j:02}' for j in range(1,9)]+['C']+[f'D{j:02}' for j in range(1,fresh+1)]+['SHIFT']
  qualified=sum(checked_by_id.get(mid,False) or mid=='C' and checked_by_id.get('C-FALLBACK',False) for mid in useful)
  need(qualified==s.get('qualified'),folder,'QUALIFIED_RECONCILIATION',(qualified,s.get('qualified')))
  refused=inspect(tasks['UNSUPPORTED']) if 'UNSUPPORTED' in tasks else None
  if 'UNSUPPORTED' in rowmap:need(refused=='CONDUCTANCE_SCOPE' and not checked_by_id.get('UNSUPPORTED'),folder,'UNSUPPORTED_NOT_OUTSIDE_SCOPE',None)
  requirement=next((e for e in events if e.get('kind')=='SUCCESSOR_REQUIREMENT'),None)
  if requirement is not None:
   preceding=rowmap.get('B08');btask=tasks.get('B08');bx=vectors.get('B08')
   if preceding is None or btask is None or bx is None:issue(folder,'MISSING_ACCEPTED_PREDECESSOR','B08')
   else:
    need(checked_by_id.get('B08') and requirement.get('parent_receipt')==preceding['receipt_digest'] and requirement.get('parent_input')==preceding['input_digest'] and requirement.get('parent_solution')==preceding['solution_digest'],folder,'CAUSAL_PREDECESSOR_BINDING','B08')
    rank=s['regime']['rank'];ordered=sorted(range(len(btask['edges'])),key=lambda i:(-abs(btask['edges'][i][2]*(bx[btask['edges'][i][0]]-bx[btask['edges'][i][1]])),i))[:rank]
    selected=[[i,btask['edges'][i][2]*.5] for i in ordered]
    need(requirement.get('changes')==selected,folder,'ACTUAL_PREDECESSOR_FLOW_SELECTION',selected)
    changed=json.loads(json.dumps(btask));
    for i,delta in selected:changed['edges'][i][2]+=delta
    ctask=tasks.get('C',tasks.get('C-FALLBACK'))
    if ctask is not None:need(digest(changed)==digest(ctask),folder,'ACTUAL_CHANGED_MISSION_STATE','C')
    changes_by_stream[(regime,seed,arm)]=digest(selected)
  for mid,dg in taskids.items():pair_inputs[(regime,seed,mid)][arm]=dg
  for name,receipt in s.get('asset_files',{}).items():
   path=folder/Path(receipt['path']).name
   if not path.exists():issue(folder,'MISSING_RETAINED_ASSET',name);continue
   actual=file_hash(path);manifest[str(path.relative_to(root))]={'bytes':path.stat().st_size,'sha256':actual}
   need(actual==receipt.get('sha256') and path.stat().st_size==receipt.get('bytes'),folder,'ASSET_BYTES',name)
   with np.load(path,allow_pickle=False) as z:
    meta=json.loads(str(z['meta']))
    if name=='successor' and requirement is not None:
     need(meta.get('preceding_accepted_receipt')==requirement['parent_receipt'] and meta.get('changes')==requirement['changes'],folder,'PERSISTED_SUCCESSOR_LINEAGE',name)
     need(meta.get('base_operator')==rowmap.get('A',{}).get('operator_digest'),folder,'PERSISTED_PARENT_OPERATOR',name)
     need(meta.get('operator')==rowmap.get('C',{}).get('operator_digest') and meta.get('operator')!=meta.get('base_operator'),folder,'DISTINCT_CHANGED_OPERATOR',name)
     need(meta.get('identity')==digest({'kind':'low-rank-response/v1','parent':meta.get('parent'),'operator':meta.get('operator'),'preceding_accepted_receipt':meta.get('preceding_accepted_receipt'),'changes':meta.get('changes')}),folder,'SUCCESSOR_RECIPE_IDENTITY',name)
     need(rowmap.get('C',{}).get('details',{}).get('construction_parent_calls',0)>0,folder,'CONSTRUCTION_PARENT_CALL',name)
     for row in rows:
      if row['id'].startswith('D') and row.get('details',{}).get('method')=='woodbury':
       need(row['details'].get('asset')==meta.get('identity') and row['details'].get('parent')==meta.get('parent') and row['details'].get('parent_calls',0)>0,folder,'FRESH_CHILD_PARENT_CALL',row['id'])
  account_totals={};released=0
  if custody is not None:
   journal_path=folder/'custody/journal.jsonl';anchor_path=folder/'custody/anchor.jsonl'
   if journal_path.exists() and anchor_path.exists():
    for path in [journal_path,anchor_path]:manifest[str(path.relative_to(root))]={'bytes':path.stat().st_size,'sha256':file_hash(path)}
    journal=[json.loads(line) for line in journal_path.read_text().splitlines()];anchors=[json.loads(line) for line in anchor_path.read_text().splitlines()];head='0'*64
    for sequence,event in enumerate(journal):
     body={k:v for k,v in event.items() if k!='hash'}
     need(event.get('sequence')==sequence and event.get('previous')==head and event.get('hash')==hashlib.sha256(canonical(body,True)).hexdigest(),folder,'JOURNAL_CHAIN',sequence);head=event.get('hash')
    need(anchors==[{'sequence':i,'head':e['hash']} for i,e in enumerate(journal)],folder,'JOURNAL_ANCHORS',None)
    need(custody.get('checkpoint',{}).get('head')==head and custody.get('checkpoint',{}).get('sequence')==len(journal)-1,folder,'CUSTODY_SNAPSHOT_HEAD',None)
   else:issue(folder,'MISSING_CUSTODY_CHAIN','journal or anchor')
   requests=custody['requests'];released=custody['earned_released_us'];need(sum(r.get('released_us',0) for r in requests.values())==released,folder,'CAPACITY_TRANSFER_TOTAL',None)
   if not development:
    need(custody['config']['service_us']==protocol['budgets']['service_dispatch_cpu_ms']*1000 and custody['config']['improvement_us']==protocol['budgets']['external_improvement_dispatch_cpu_ms']*1000 and custody['config']['earned_cap_us']==protocol['budgets']['earned_transfer_cap_ms']*1000,folder,'REGISTERED_ACCOUNT_CAPS',None)
   need(released<=custody['config']['earned_cap_us'],folder,'CAPACITY_TRANSFER_CAP',None)
   for name,account in custody['accounts'].items():
    spent=sum(r.get('charged_us',0) for r in requests.values() if r['account']==name);reserved=sum(r['ceiling_us'] for r in requests.values() if r['account']==name and r['status']=='PENDING')
    transferred=-released if name=='service' else released if name=='earned' else 0
    need(account['spent_us']==spent and account['reserved_us']==reserved and account['available_us']==account['external_us']+transferred-spent-reserved,folder,'ACCOUNT_CONSERVATION',name);account_totals[name]=spent/1000
   for req in requests.values():
    if req.get('released_us',0):need(req['account']=='service' and req.get('accepted') and req['released_us']<=req['ceiling_us']-req['charged_us'],folder,'RELEASE_FROM_ACCEPTED_UNUSED_SERVICE',req['id'])
   need(account_totals.get('earned',0)<=released/1000 or s.get('account_overrun'),folder,'SUCCESSOR_USES_UNFUNDED_CAPACITY',None)
   need(not any(a.get('active_proof') or a.get('authority') for a in custody.get('assets',{}).values()),folder,'ASSET_AUTHORITY',None)
  charged=sum(r.get('cpu_ms',0) for r in rows);need(close(charged,s.get('charged_action_cpu_ms')),folder,'ACTION_CPU_TOTAL',None)
  total=s.get('total_cpu_ms');need(isinstance(total,(int,float)) and math.isfinite(total) and total>=charged,folder,'FULL_CPU_BOUNDARY',total)
  budget_violation=bool(s.get('account_overrun') or s.get('control_budget_exceeded') or custody is not None and any(r.get('status')=='OVERRUN' for r in custody['requests'].values()))
  scope_recovery=refused=='CONDUCTANCE_SCOPE' and checked_by_id.get('SHIFT',False) and (regime!='maintenance' or checked_by_id.get('RESTORE',False))
  records.append({'trial':str(folder.relative_to(root)),'seed':seed,'regime':regime,'arm':arm,'qualified':qualified,'offered':offered,'attempted_useful':sum(mid in rowmap or mid=='C' and 'C-FALLBACK' in rowmap for mid in useful),'total_cpu_ms':total,'charged_action_cpu_ms':charged,'external_control_cpu_ms':total-charged if isinstance(total,(int,float)) else None,'total_wall_ms':s.get('total_wall_ms'),'account_cpu_ms':account_totals,'released_service_quota_ms':released/1000,'qualified_fresh_child_outputs':parent_qualified,'qualified_fresh_child_parent_calls':parent_api_calls,'reported_successor_constructed':s.get('successor_constructed'),'methods':dict(methods),'scope_refusal':refused,'scope_recovery_pass':scope_recovery,'budget_violation':budget_violation,'asset_count':len(s.get('asset_files',{})),'reported_failure':s.get('error',s.get('failure'))})
 counts=collections.Counter((r['regime'],r['seed'],r['arm']) for r in records)
 need(all(v==1 for v in counts.values()),root,'DUPLICATE_TRIAL_KEYS',None)
 streams={(r['regime'],r['seed']) for r in records}
 if not development:
  need(len(streams)==24 and len(records)==24*len(ARMS),root,'CONFIRMATION_TRIAL_COUNT',(len(streams),len(records)))
  for regime in REGIMES:need(sum(x[0]==regime for x in streams)==6,root,'STRATUM_COUNT',regime)
  for regime,seed in streams:need({r['arm'] for r in records if r['regime']==regime and r['seed']==seed}==set(ARMS),root,'INCOMPLETE_ARM_SET',(regime,seed))
  need(len({seed for _,seed in streams})==24,root,'UNIQUE_NETWORK_SEEDS',None)
  need(all(type(seed) is int and 0<=seed<2**32 for _,seed in streams),root,'REGISTERED_SEED_SCOPE',None)
  need(not ({seed for _,seed in streams}&set(range(27001,27005))|{seed for _,seed in streams}&set(range(27101,27105))),root,'DEVELOPMENT_SEED_REUSE',None)
 divergences=[]
 for (regime,seed,mid),values in pair_inputs.items():
  if len(set(values.values()))>1:divergences.append({'regime':regime,'seed':seed,'mission':mid,'arm_digests':values})
 need(not divergences,root,'PAIRED_INPUT_DIVERGENCE',divergences)
 summary=[]
 for arm in ARMS:
  rr=[r for r in records if r['arm']==arm]
  if not rr:continue
  summary.append({'arm':arm,'streams':len(rr),'qualified':sum(r['qualified'] for r in rr),'offered':sum(r['offered'] for r in rr),'all_qualified':all(r['qualified']==r['offered'] for r in rr),'total_cpu_ms':sum(r['total_cpu_ms'] for r in rr if r['total_cpu_ms'] is not None),'mean_cpu_ms':sum(r['total_cpu_ms'] for r in rr if r['total_cpu_ms'] is not None)/len(rr),'qualified_fresh_child_parent_calls':sum(r['qualified_fresh_child_parent_calls'] for r in rr),'released_service_quota_ms':sum(r['released_service_quota_ms'] for r in rr),'successor_account_spent_ms':sum(r['account_cpu_ms'].get('earned',0) for r in rr)})
 primary=bootstrap_pairs(records,'native_refactor');conventional=bootstrap_pairs(records,'conventional_reuse');byarm={r['arm']:r for r in summary}
 fly_quality=byarm.get('flywheel',{}).get('all_qualified',False);all_primary_quality=all(byarm.get(a,{}).get('all_qualified',False) for a in ['flywheel','native_refactor','conventional_reuse'])
 gain=primary.get('status')=='COMPLETE' and primary['percentile_95_ci'][1]<.95;ni=conventional.get('status')=='COMPLETE' and conventional['percentile_95_ci'][1]<1.10
 operational=all(not r['reported_failure'] and not r['budget_violation'] and r['scope_recovery_pass'] for r in records)
 result={'schema':'earned-turn-independent-results/v1','status':'PASS' if not issues else 'ISSUES_FOUND','analysis_status':'DEVELOPMENT_AUDIT' if development else 'FROZEN_CONFIRMATORY_REANALYSIS','expected_source':expected_source,'protocol_sha256':file_hash(protocol_path),'audit_source_sha256':file_hash(Path(__file__)),'checker_source_sha256':file_hash(Path(__file__).with_name('checker.py')),'issues':issues,'trials':records,'aggregates':summary,'primary_cpu_ratio':primary,'conventional_noninferiority':conventional,'product_gate':{'all_flywheel_qualified':fly_quality,'all_three_primary_comparators_qualified':all_primary_quality,'zero_failures_budget_violations_and_all_stream_scope_recovery':operational,'upper_95_ratio_vs_native_below_0_95':gain,'upper_95_ratio_vs_conventional_below_1_10':ni,'passed':bool(all_primary_quality and operational and gain and ni and not issues),'investment_recovery':'UNRESOLVED_UNKNOWN_HUMAN_AND_MONETARY_COSTS','acceleration':'NOT_TESTED'},'paired_input_divergences':divergences,'numeric_checks':all_checks,'source_artifacts':manifest,'audit_cpu_ms':1000*(time.process_time()-cpu),'audit_wall_ms':1000*(time.perf_counter()-started),'independence':'Separate raw-data aggregation without producer analysis imports; checker separately sums node balances. Same commission and host; reviewer previously corrected executor validation and integer-ground assembly. Parent counters are producer instrumentation, independently attributed rather than CPU-traced.','cost_boundary':'Audit compute is additional research cost, not part of already measured service trials. Raw claimed totalCPU is reconciled to charged actions but cannot be independently reconstructed from CPU hardware after the fact.'}
 destination=Path(output) if output else Path(__file__).with_name('results')/'INDEPENDENT_RESULTS.json';destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print(json.dumps({'status':result['status'],'trials':len(records),'checked_outputs':len(all_checks),'issues':len(issues),'product_gate':result['product_gate'],'output':str(destination)}))
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--results',required=True);p.add_argument('--expected-source',required=True);p.add_argument('--development',action='store_true');p.add_argument('--output');a=p.parse_args()
 if len(a.expected_source)!=64 or any(c not in '0123456789abcdef' for c in a.expected_source) or not a.development and a.expected_source=='0'*64:raise ValueError('EXPECTED_FROZEN_SOURCE_REQUIRED')
 r=run(a.results,a.expected_source,a.development,a.output)
 if r['issues']:sys.exit(2)

if __name__=='__main__':main()
