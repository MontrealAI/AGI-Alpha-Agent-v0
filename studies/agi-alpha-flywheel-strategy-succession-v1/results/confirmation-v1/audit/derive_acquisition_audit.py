#!/usr/bin/env python3
"""POST HOC DESCRIPTIVE AUDIT: classify preserved outcomes; never rerun/tune them.

This audit was requested after the frozen confirmation completed. It is not a
new primary analysis, task selection, candidate evaluation, or source revision.
"""
from __future__ import annotations
import collections,datetime,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
trials=[json.loads(line) for line in (ROOT/'trials.jsonl').read_text().splitlines() if line.strip()]
records=[];storage=[];allocations=[];grouped=collections.defaultdict(lambda:{'stages':0,'decisions':collections.Counter(),'search_stops':collections.Counter(),
 'candidate_statuses':collections.Counter(),'executed_training_rows':0,'unfunded_training_rows':0,'acquisition_work':0,'gate_reached':0})
def classify(trial):
 rows=trial['rows']
 if trial['complete']:return 'COMPLETE'
 if any(r.get('error')=='CHECK_RESERVE' and r.get('work',0)==0 for r in rows):return 'UNFUNDED_PIPELINE_CALL'
 if any(r.get('error') in ('WORK_LIMIT','CHECK_RESERVE','TOTAL_BUDGET_EXCEEDED') for r in rows):return 'EXECUTED_PIPELINE_LIMIT'
 if any(not r.get('valid',False) for r in rows):return 'INVALID_TRAINING_RESULT'
 if trial.get('eliminated_after') is not None:return 'NORMAL_VALID_HALVING_ELIMINATION'
 if not rows:return 'NEVER_FUNDED'
 return 'UNFINISHED_VALID_PREFIX'

for trial in trials:
 folder=ROOT/trial['artifact_path'];state=json.loads((folder/'checkpoint.json').read_text())
 config=json.loads((ROOT/'inputs'/f"{trial['stream']}.json").read_text())
 raw=[]
 with gzip.open(folder/'raw.jsonl.gz','rt') as handle:
  raw=[json.loads(line) for line in handle if line.strip()]
 for phase in ['qualification','qualification-reference']:
  qrows=[r['row'] for r in raw if r['phase']==phase]
  if qrows:
   allocations.append({'category':trial['category'],'stream':trial['stream'],'arm':trial['arm'],'treatment':trial['parent_treatment'],'budget':trial['budget'],
    'phase':phase,'executed_calls':len(qrows),'registered_total_pipeline_allocations':sorted(set(r['allocated_budget'] for r in qrows)),
    'execution_budget_range':[min(r['execution_budget'] for r in qrows),max(r['execution_budget'] for r in qrows)],
    'actual_charged_work':sum(r['work'] for r in qrows),'source':str((folder/'raw.jsonl.gz').relative_to(ROOT)),
    'meaning':'Equal registered total pipeline allocations; solver/checker execution allowance can differ with current charged control-state reserve. Order alternates as frozen.'})
 learn_events=[e for e in state['events'] if e['kind']=='OUT_LEARN'];design_events=[e for e in state['events'] if e['kind']=='OUT_DESIGN']
 for ordinal,discovery in enumerate(state['discoveries']):
  search=discovery.get('search') or {};stage=discovery['stage'];candidate_rows=search.get('trials',[])
  status=collections.Counter(classify(x) for x in candidate_rows)
  decision=discovery.get('gate',{}).get('decision') if discovery.get('gate') else discovery.get('decision','NO_COMPLETE_CANDIDATE')
  relevant_learn=next((e for e in learn_events if e['stage']==stage),None)
  if relevant_learn:learn_events.remove(relevant_learn)
  relevant_design=next((e for e in design_events if e['stage']==stage),None)
  if relevant_design:design_events.remove(relevant_design)
  start_work=relevant_learn['work_total'] if relevant_learn else None
  allocation=100000 if trial['category']=='diagnostic' else 50000
  validation_count=len(config['qualification'][stage]['validation'])
  stage_cap=1500000 if trial['category']=='diagnostic' else 500000
  effective_limit=min(stage_cap,trial['budget']-start_work-18000) if start_work is not None else None
  failures=[{'candidate_index':x['index'],'task_id':r['task_id'],'error':r.get('error'),'paid_work':r.get('work',0),'allocated_pipeline_budget':r.get('allocated_budget')}
   for x in candidate_rows for r in x['rows'] if r.get('error')]
  row={'category':trial['category'],'stream':trial['stream'],'arm':trial['arm'],'treatment':trial['parent_treatment'],'budget':trial['budget'],
   'stage':stage,'ordinal':ordinal,'decision':decision,'search_stop':search.get('stop'),'candidate_statuses':dict(status),
   'candidate_selected':search.get('candidate',{}).get('digest') if search.get('candidate') else None,
   'paid_acquisition_work':discovery['acquisition'],'effective_stage_limit':effective_limit,
   'protected_qualification_reserve':2*allocation*validation_count+1024,'registered_per_output_pipeline_allocation':allocation,
   'search_paid_before_design':relevant_design['work_total']-start_work if relevant_design and start_work is not None else None,
   'executed_training_rows':sum(r.get('work',0)>0 for x in candidate_rows for r in x['rows']),
   'unfunded_training_rows':sum(r.get('work',0)==0 and r.get('error') is not None for x in candidate_rows for r in x['rows']),
   'failures':failures,'fair_qualification_allocation':(discovery.get('qualification') or {}).get('fair_allocation'),
   'gate_reached':discovery.get('gate') is not None,'gate':discovery.get('gate'),
   'evidence':str((folder/'checkpoint.json').relative_to(ROOT))}
  records.append(row);key=(trial['category'],trial['budget'],trial['arm'],trial['parent_treatment'],stage);g=grouped[key]
  g['stages']+=1;g['decisions'][decision]+=1;g['search_stops'][str(search.get('stop'))]+=1;g['candidate_statuses'].update(status)
  g['executed_training_rows']+=row['executed_training_rows'];g['unfunded_training_rows']+=row['unfunded_training_rows'];g['acquisition_work']+=row['paid_acquisition_work'];g['gate_reached']+=row['gate_reached']
 files={str(p.relative_to(folder)):p.stat().st_size for p in folder.rglob('*') if p.is_file()}
 storage.append({'category':trial['category'],'stream':trial['stream'],'arm':trial['arm'],'treatment':trial['parent_treatment'],'budget':trial['budget'],
  'total_artifact_bytes':sum(files.values()),'files':files,'checkpoint_reported_bytes':trial['storage_bytes'],
  'scope':'Actual on-disk bytes of this completed trial including checkpoint, guard, events, compressed raw records/packs and summary; no estimate of money or indefinite storage.'})

aggregate=[]
for key,g in sorted(grouped.items()):
 aggregate.append(dict(zip(['category','budget','arm','treatment','stage'],key),**{k:dict(v) if isinstance(v,collections.Counter) else v for k,v in g.items()}))
primary=[r for r in records if r['category']=='main' and r['budget']==1000000 and r['arm']=='flywheel']
report={'schema':'posthoc-acquisition-classification/v1','analysis_status':'POST_HOC_DESCRIPTIVE_AUDIT_OF_FROZEN_ARTIFACTS',
 'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_file_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'frozen_execution_source':json.loads((ROOT/'RUN_COMPLETE.json').read_text())['source_hash'],
 'notes':['No candidate, evaluator, task, budget or frozen primary statistic was changed or rerun.',
  'The frozen summary field truncated_candidates means non-complete entries; normal halving elimination must not be called a budget failure.',
  'A zero-work CHECK_RESERVE training row is a preflight refusal; no planner/checker execution occurred for that unfunded call.',
  'The protected qualification reservation is an allocation ceiling, not work actually spent. Nominal unused stage budget is not proof that the next registered pipeline call was funded.',
  'All72 offered primary missions include the initial founder mission. Diagnostic founder missions are separated from36 fresh successor missions.'],
 'primary_flywheel':{'stages':len(primary),'gate_reached':sum(r['gate_reached'] for r in primary),'decisions':dict(collections.Counter(r['decision'] for r in primary)),
  'acquisition_work_range':[min(r['paid_acquisition_work'] for r in primary),max(r['paid_acquisition_work'] for r in primary)],
  'candidate_statuses':dict(sum((collections.Counter(r['candidate_statuses']) for r in primary),collections.Counter()))},
 'aggregate':aggregate,'records':records,'qualification_allocation_audit':allocations}
(ROOT/'ACQUISITION_FAILURE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
(ROOT/'ARTIFACT_STORAGE_AUDIT.json').write_text(json.dumps({'analysis_status':'POST_HOC_DESCRIPTIVE_STORAGE_INVENTORY','total_trial_artifact_bytes':sum(r['total_artifact_bytes'] for r in storage),'trials':storage},indent=2)+'\n')
print(json.dumps({'primary_flywheel':report['primary_flywheel'],'acquisition_records':len(records),'trial_artifact_bytes':sum(r['total_artifact_bytes'] for r in storage)}))
