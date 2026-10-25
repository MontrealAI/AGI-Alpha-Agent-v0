#!/usr/bin/env python3
"""Post hoc descriptive use audit; no execution, selection or frozen edits."""
import collections,datetime,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
trials=[json.loads(x) for x in (ROOT/'trials.jsonl').read_text().splitlines() if x.strip()]
inherited=[x for x in trials if x['category']=='diagnostic' and x['parent_treatment']=='inherited']
removed={x['stream']:x for x in trials if x['category']=='diagnostic' and x['parent_treatment']=='removed'}
rows=[];fresh_comparisons=[]
for trial in inherited:
 folder=ROOT/trial['artifact_path'];state=json.loads((folder/'checkpoint.json').read_text());config=json.loads((ROOT/'inputs'/f"{trial['stream']}.json").read_text())
 with gzip.open(folder/'raw.jsonl.gz','rt') as f:raw=[json.loads(x) for x in f if x.strip()]
 for stage in ['dispatch','lookahead','repair']:
  discovery=next(d for d in state['discoveries'] if d['stage']==stage);selected=discovery['search']['candidate']['strategy'];asset=next(a for a in state['assets'] if a['stage']==stage)
  train_ids={t['id'] for t in config['qualification'][stage]['training']};q_ids={t['id'] for t in config['qualification'][stage]['validation']}
  counter={'dispatch':None,'lookahead':'strategy:inherited-dispatch-rollout','repair':'strategy:inherited-lookahead-decision'}[stage]
  groups={'selected_training':[x for x in raw if x['phase']=='discovery' and x['task']['id'] in train_ids and x['strategy']==selected],
   'other_training':[x for x in raw if x['phase']=='discovery' and x['task']['id'] in train_ids and x['strategy']!=selected],
   'selected_qualification':[x for x in raw if x['phase']=='qualification' and x['task']['id'] in q_ids and x['strategy']==selected],
   'fresh_missions':[x for x in raw if x['phase']=='mission' and x['strategy']==selected]}
  phases={}
  for phase,entries in groups.items():
   details=[]
   for entry in entries:
    result=entry['row'];calls=result['counts'].get(counter,0) if counter else None
    details.append({'task_id':entry['task']['id'],'valid':result['valid'],'qualified':result['qualified'],'parent_calls':calls,
     'makespan':result['result']['makespan'] if result.get('result') else None,'deadline':entry['task'].get('deadline'),
     'actual_repair_branch':result.get('result',{}).get('repair_mode') if result.get('result') else None,
     'charged_work':result['work'],'source_raw_phase':entry['phase']})
   phases[phase]={'outputs':len(details),'valid':sum(x['valid'] for x in details),'qualified':sum(x['qualified'] for x in details),
    'direct_parent_calls':sum(x['parent_calls'] or 0 for x in details) if counter else None,
    'outputs_with_parent_call':sum((x['parent_calls'] or 0)>0 for x in details) if counter else None,
    'qualified_outputs_with_parent_call':sum(x['qualified'] and (x['parent_calls'] or 0)>0 for x in details) if counter else None,'details':details}
  rows.append({'stream':trial['stream'],'stage':stage,'asset_digest':asset['digest'],'parent_digest':asset['parent_digest'],'selected_strategy':selected,
   'immediate_parent_counter':counter,'phases':phases,'source':str((folder/'raw.jsonl.gz').relative_to(ROOT)),
   'interpretation':'A positive counter is a recorded immediate-parent execution in this exact phase. Embedded ancestry alone is not execution. Stable repair can still use transitive dispatch content while skipping its immediate lookahead parent.'})
 a={x['id']:x for x in trial['mission_results']};b={x['id']:x for x in removed[trial['stream']]['mission_results']}
 for task_id,x in a.items():
  y=b[task_id];fresh_comparisons.append({'stream':trial['stream'],'task_id':task_id,'scope':x['scope'],'inherited_qualified':x['qualified'],'removed_qualified':y['qualified'],
   'inherited_makespan':x['makespan'],'removed_makespan':y['makespan'],'inherited_minus_removed_makespan':x['makespan']-y['makespan'],
   'same_schedule':x['schedule_sha256']==y['schedule_sha256'],'both_qualified':x['qualified'] and y['qualified']})
aggregate={}
for stage in ['lookahead','repair']:
 entries=[x for x in rows if x['stage']==stage];aggregate[stage]={}
 for phase in ['selected_training','other_training','selected_qualification','fresh_missions']:
  aggregate[stage][phase]={field:sum(x['phases'][phase][field] for x in entries) for field in ['outputs','valid','qualified','direct_parent_calls','outputs_with_parent_call','qualified_outputs_with_parent_call']}
  aggregate[stage][phase]['streams_with_parent_call']=sum(x['phases'][phase]['direct_parent_calls']>0 for x in entries)
  aggregate[stage][phase]['streams_with_qualified_parent_call']=sum(x['phases'][phase]['qualified_outputs_with_parent_call']>0 for x in entries)
report={'schema':'selected-lineage-use-audit/v1','analysis_status':'POST_HOC_DESCRIPTIVE_ARTIFACT_AUDIT','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'audit_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'frozen_execution_source':json.loads((ROOT/'RUN_COMPLETE.json').read_text())['source_hash'],
 'scope':'Twelve inherited diagnostic streams, with fixed removed-ancestry comparators. No new execution or candidate selection.',
 'notes':['Counter locations are raw[i].row.counts[immediate_parent_counter]. Exact selected AST values are matched structurally to checkpoint.discoveries[].search.candidate.strategy, ignoring JSON object member order only.',
  'Selected qualification means the selected candidate on the protected qualification corpus; qualified means that output separately met the user deadline. They are different predicates.',
  'Losing-candidate search calls do not prove that the retained child uses its parent. Qualified output plus a parent call is still not a net-benefit or superiority claim.',
  'All these retained assets were diagnostic correctness-only admissions; no primary asset was admitted.'],
 'aggregate':aggregate,'per_stream_stage':rows,'fresh_inherited_vs_removed':fresh_comparisons}
(ROOT/'SELECTED_LINEAGE_USE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'aggregate':aggregate,'positive_makespan_examples':[x for x in fresh_comparisons if x['both_qualified'] and x['inherited_minus_removed_makespan']<0]}))
