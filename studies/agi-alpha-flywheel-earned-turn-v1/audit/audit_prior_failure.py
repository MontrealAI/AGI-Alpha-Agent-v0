import collections, datetime, gzip, hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIOR=HERE.parents[1]/'strategy_succession'
R=PRIOR/'results/confirmation-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def read(p):
 p=Path(p); sources[str(p.relative_to(PRIOR))]={'sha256':sha(p),'bytes':p.stat().st_size};return json.loads(p.read_text())
freeze=read(PRIOR/'protocol/STUDY_FREEZE.json')
freeze_checks={name:sha(PRIOR/name)==meta['sha256'] for name,meta in freeze['files'].items()}
assert all(freeze_checks.values())
for f in ['companion/stream.mjs','companion/learning.mjs','companion/scenarios.mjs','companion/core.mjs']:
 p=PRIOR/f;sources[f]={'sha256':sha(p),'bytes':p.stat().st_size}
protocol=read(PRIOR/'protocol/MAIN_PROTOCOL.json')
trials=[]
p=R/'trials.jsonl';sources[str(p.relative_to(PRIOR))]={'sha256':sha(p),'bytes':p.stat().st_size}
for line in p.read_text().splitlines():
 if line.strip():trials.append(json.loads(line))
primary=[];all_primary=[];training_counter=collections.Counter();status_counter=collections.Counter();native=read(R/'NATIVE_REFERENCE.json')
for t in trials:
 if t['category']!='main' or t['budget']!=1000000:continue
 state=read(R/t['artifact_path']/'checkpoint.json')
 assert t['work']==sum(x['work'] for x in state['ledger'])==state['work']
 assert t['qualified']==sum(x['qualified'] for x in state['missions'])
 assert t['valid']==sum(x['valid'] for x in state['missions'])
 all_primary.append({'stream':t['stream'],'arm':t['arm'],'offered':t['offered'],'attempted':len(state['missions']),'valid':t['valid'],'qualified':t['qualified'],'work':state['work'],'assets':len(state['assets']),'costs':dict(collections.Counter({k:sum(e['work'] for e in state['ledger'] if e['kind']==k) for k in {x['kind'] for x in state['ledger']}}))})
 if t['arm']!='flywheel':continue
 assert len(state['discoveries'])==1
 a=state['discoveries'][0];s=a['search'];assert a['stage']=='dispatch' and a['gate'] is None and s['candidate'] is None
 statuses=[];rows=[]
 for candidate in s['trials']:
  rs=candidate['rows'];rows.extend(rs)
  if candidate['complete']:status='COMPLETE'
  elif any(r['error']=='CHECK_RESERVE' and r['work']==0 for r in rs):status='UNFUNDED_PIPELINE_CALL'
  elif any(not r['valid'] for r in rs):status='INVALID_EXECUTED_PREFIX'
  elif candidate['eliminated_after'] is not None:status='NORMAL_VALID_HALVING_ELIMINATION'
  elif rs:status='UNFINISHED_VALID_PREFIX'
  else:status='NEVER_STARTED'
  statuses.append(status)
 status_counter.update(statuses)
 training_counter.update({'paid_calls':sum(r['work']>0 for r in rows),'zero_work_refusals':sum(r['work']==0 for r in rows),'valid_paid_calls':sum(r['work']>0 and r['valid'] for r in rows),'truncated_paid_calls':sum(r['work']>0 and r['truncated'] for r in rows)})
 learn=next(e for e in state['events'] if e['kind']=='OUT_LEARN' and e['stage']=='dispatch')
 design=next(e for e in state['events'] if e['kind']=='OUT_DESIGN' and e['stage']=='dispatch')
 later=[e for e in state['events'] if e['kind']=='OUT_EVOLVE' and e.get('stage') in ['lookahead','repair']]
 primary.append({'stream':t['stream'],'acquisition_work':a['acquisition'],'search_paid_before_design':design['work_total']-learn['work_total'],'paid_calls':sum(r['work']>0 for r in rows),'max_training_prefix':max(sum(r['work']>0 for r in c['rows']) for c in s['trials']),'candidate_statuses':dict(collections.Counter(statuses)),'search_stop':s['stop'],'qualification':a['qualification'],'gate':a['gate'],'completed_stages':state['completed_stages'],'downstream_decisions':later,'evidence':str((R/t['artifact_path']/'checkpoint.json').relative_to(PRIOR))})
agg=[]
for arm in sorted(set(x['arm'] for x in all_primary)):
 rs=[x for x in all_primary if x['arm']==arm];cost=collections.Counter()
 for row in rs:cost.update(row['costs'])
 agg.append({'arm':arm,**{k:sum(x[k] for x in rs) for k in ['offered','attempted','valid','qualified','work','assets']},'costs':dict(cost)})
diag=[];fresh_repairs=[];fresh_lookaheads=[];repair_modes=collections.Counter()
for treatment in ['inherited','removed','rebuild','equivalent']:
 ts=[t for t in trials if t['category']=='diagnostic' and t['parent_treatment']==treatment]
 ds=[]
 for t in ts:
  state=read(R/t['artifact_path']/'checkpoint.json');assert t['qualified']==sum(m['qualified'] for m in state['missions'])
  ds.append({'stream':t['stream'],'qualified':t['qualified'],'valid':t['valid'],'work':state['work'],'gates':[a.get('gate',{}).get('decision') for a in state['discoveries']]})
  if treatment!='inherited':continue
  repair=next(a for a in state['assets'] if a['stage']=='repair');repair_modes[repair['strategy']['mode']]+=1
  p=R/t['artifact_path']/'raw.jsonl.gz';sources[str(p.relative_to(PRIOR))]={'sha256':sha(p),'bytes':p.stat().st_size}
  for n,row in enumerate(map(json.loads,gzip.open(p,'rt')),1):
   if row['phase']!='mission' or row['task']['scope']=='ordinary':continue
   scope=row['task']['scope'];counter='strategy:inherited-lookahead-decision' if scope=='repair' else 'strategy:inherited-dispatch-rollout'
   rr={'stream':t['stream'],'task_id':row['task']['id'],'valid':row['row']['valid'],'qualified':row['row']['qualified'],'parent_calls':row['row']['counts'].get(counter,0),'makespan':row['row']['result']['makespan'],'deadline':row['task']['deadline'],'raw_line_1based':n,'evidence':str(p.relative_to(PRIOR))}
   (fresh_repairs if scope=='repair' else fresh_lookaheads).append(rr)
 diag.append({'treatment':treatment,'streams':len(ds),'qualified':sum(x['qualified'] for x in ds),'valid':sum(x['valid'] for x in ds),'total_work':sum(x['work'] for x in ds),'mean_work':sum(x['work'] for x in ds)/len(ds),'gates':dict(collections.Counter(g for x in ds for g in x['gates']))})
existing_acq=read(R/'ACQUISITION_FAILURE_AUDIT.json');existing_ancestry=read(R/'SELECTED_LINEAGE_USE_AUDIT.json')
assert training_counter['paid_calls']==140 and training_counter['valid_paid_calls']==140 and training_counter['zero_work_refusals']==12
assert status_counter==collections.Counter(existing_acq['primary_flywheel']['candidate_statuses'])
assert sum(x['parent_calls']>0 and x['qualified'] for x in fresh_repairs)==0
assert sum(x['qualified'] for x in fresh_repairs)==10 and sum(x['parent_calls']>0 for x in fresh_repairs)==1
assert len(fresh_repairs)==len(fresh_lookaheads)==12
summary={x['arm']:x for x in agg};assert summary['flywheel']['qualified']==summary['learner']['qualified']==517 and summary['portfolio']['qualified']==591
assert summary['flywheel']['assets']==0
report={'schema':'earned-turn-prior-failure-audit/v1','status':'READ_ONLY_RECONCILIATION_NOT_NEW_CONFIRMATION','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prior_source_manifest':'7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7','prior_frozen_files_verified':len(freeze_checks),'all_prior_frozen_files_unchanged':all(freeze_checks.values()),'audit_source_sha256':sha(Path(__file__)),'primary_aggregates':agg,'primary_acquisitions':primary,'primary_training':dict(training_counter),'primary_candidate_statuses':dict(status_counter),'reservation':{'stage_cap':500000,'qualification_outputs':8,'per_output_pipeline_allocation':50000,'extra_reserve':1024,'qualification_reserved':401024,'qualification_reserved_percent':80.2048,'maximum_precontrol_search_room':98976,'next_call_additional_reserve':1024,'pipeline_minimum_after_control_reserve':18000,'scheduled_training_calls_for_complete_race':17,'qualification_evaluations_executed':0,'admission_tests_executed':0,'note':'Reserved allocations were not charged as spent work. Control reserve further reduces a candidate call budget; no counterfactual reallocation was executed.'},'diagnostic':diag,'fresh_repair_use':fresh_repairs,'fresh_lookahead_use':fresh_lookaheads,'repair_modes':dict(repair_modes),'fresh_repair_use_summary':{'outputs':12,'qualified':10,'outputs_using_parent':1,'qualified_outputs_using_parent':0},'native_reference_summary':{'paired_tasks':36,'portfolio_qualified':sum(r['portfolio_qualified'] for r in native['rows'] if r['mode']=='deadline'),'status':'Native specialist reference has separate wall-time accounting; no equal-unit primary comparison is asserted'},'interpretation':{'proximate_failure':'Fixed acquisition allocation plus conservative complete-pipeline preflight exhausted exploration before one candidate completed six training cases; the economic admission gate was never reached.','implementation_defect_status':'No corrupt result, invalid primary paid training output, or contradiction of frozen stop logic was found. Allocation incompatibility and growing full-history checkpoint costs are design/engineering deficiencies, not proof that a completed candidate would have won.','shared_account':'Service and improvement consumed one cumulative account; research artifacts enlarged repeatedly serialized checkpoints.','terminal_failure':'A stage is marked completed before acquisition; failed dispatch is not retried, so descendants lacking an admitted parent defer.','transfer_evidence':'No primary admitted parent exists. Diagnostic inherited construction is cheaper than exact reconstruction but more costly and one qualified result worse than the strong parent-free alternative.','repair_lineage':'Repair tasks were generated from independent conventional-portfolio baselines, not actual accepted preceding mission outputs. Stored ancestry alone cannot establish use.','representation':'Finite dispatch-weight/lookahead/repair grammar did not preserve a reusable world-specific computational representation across unrelated random DAGs. This is a plausible limit, not a tested proof of impossibility.','economic_gate':'The old net-benefit gate charged all acquisition against a no-research counterfactual and conflated full-investment recovery with marginal adoption. It was not exercised in the primary flywheel.','nonclaim':'Do not repair this code and rerun the old confirmation as fresh evidence; do not attribute portfolio/workflow contrasts to retention when no asset was retained.'},'next_hypotheses':[{'id':'H1','claim':'A family with repeated immutable structure and changed queries can repay a reusable representation.','decisive_test':'Bound candidate domains prospectively; compare competent direct, conventional reuse, cheapest equivalent builder, and inherited constructions on new task identities.'},{'id':'H2','claim':'Separately enforced service/improvement accounts preserve mission delivery during failed research.','decisive_test':'Exhaust improvement account, then verify incumbent service and authority remain intact within funded service limits.'},{'id':'H3','claim':'An accepted representation can reduce construction of a distinct successor capability.','decisive_test':'Use the actual accepted predecessor output/state; measure parent calls and removed-with-rebuild versus strong parent-free and independent equivalent construction.'},{'id':'H4','claim':'Measured released capacity can fund a bounded next construction.','decisive_test':'Use enforceable reusable capacity, debit it to the child construction; distinguish this from abstract operations and externally supplied research budget.'}],'sources':sources}
(HERE/'PRIOR_FAILURE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'PASS','prior_frozen_files':len(freeze_checks),'paid_primary_calls':training_counter['paid_calls'],'qualified':{x['arm']:x['qualified'] for x in agg},'diagnostic':diag,'fresh_repair_qualified_with_parent':0,'source_files':len(sources)},indent=2))
