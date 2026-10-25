#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Registered descriptive summaries and one paired primary bootstrap contrast."""
from __future__ import annotations
import csv,json,random,statistics,sys
from collections import Counter,defaultdict
from pathlib import Path

root=Path(sys.argv[1]);rows=[json.loads(x) for x in (root/'trials.jsonl').read_text().splitlines() if x.strip()]
main=[r for r in rows if r['category']=='main'];diagnostic=[r for r in rows if r['category']=='diagnostic']
def mean(values):return statistics.fmean(values) if values else None
def ci(values,seed=20261024):
 if not values:return None
 rng=random.Random(seed);n=len(values);samples=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
 return {'mean':mean(values),'percentile_95_interval':[samples[249],samples[9749]],'independent_streams':n,'resamples':10000,'seed':seed,'unit':'paired complete stream, including all stops'}

groups=defaultdict(list)
for r in main:groups[(r['budget'],r['arm'])].append(r)
arm_results=[]
for (budget,arm),batch in sorted(groups.items()):
 costs=Counter()
 for r in batch:costs.update(r['costs'])
 arm_results.append({'budget':budget,'arm':arm,'streams':len(batch),'offered':sum(r['offered'] for r in batch),
  'attempted':sum(r['attempted'] for r in batch),'valid':sum(r['valid'] for r in batch),'qualified':sum(r['qualified'] for r in batch),
  'mean_qualified':mean([r['qualified'] for r in batch]),'mean_work':mean([r['work'] for r in batch]),'total_work':sum(r['work'] for r in batch),
  'qualified_per_million_work':sum(r['qualified'] for r in batch)*1e6/sum(r['work'] for r in batch) if sum(r['work'] for r in batch) else None,
  'coverage_percent':sum(r['qualified'] for r in batch)*100/sum(r['offered'] for r in batch),
  'stopped':sum(r['status']!='COMPLETE' for r in batch),'reasons':dict(Counter(str(r['reason']) for r in batch)),
  'active_assets':sum(sum(a['active'] for a in r['assets']) for r in batch),'cost_breakdown':dict(costs),
  'mean_wall_ms':mean([r['wall_ms'] for r in batch]),'mean_node_cpu_ms':mean([r['node_cpu_ms'] for r in batch]),
  'unknown_python_cpu':True,'mid_stream_manual_interventions':sum(r['mid_stream_manual_interventions'] for r in batch)})

def pairs(arm,budget=1000000):return {r['stream']:r for r in main if r['budget']==budget and r['arm']==arm}
fly=pairs('flywheel');workflow=pairs('workflow');learner=pairs('learner');portfolio=pairs('portfolio')
ids=sorted(set(fly)&set(workflow));primary={
 'comparison':'flywheel minus conventional saved workflow at1M counted units','endpoint':'Qualified coverage of all72 offered missions, including the first founder mission',
 'coverage_difference_per_stream':ci([fly[s]['qualified']-workflow[s]['qualified'] for s in ids]),
 'coverage_percentage_point_difference':ci([(fly[s]['qualified']-workflow[s]['qualified'])*100/fly[s]['offered'] for s in ids]),
 'charged_work_difference':ci([fly[s]['work']-workflow[s]['work'] for s in ids]),
 'no_posthoc_exclusions':True,'multiplicity':'One primary contrast; all other contrasts and resource sensitivities descriptive.'}
equivalence=[]
for s in sorted(set(fly)&set(learner)):
 a,b=fly[s],learner[s];equivalence.append({'stream':s,'qualified_difference':a['qualified']-b['qualified'],'work_difference':a['work']-b['work'],
  'same_mission_outcomes':a['mission_results']==b['mission_results'],'same_asset_contents':[x['strategy'] for x in a['assets']]==[x['strategy'] for x in b['assets']]})

diagnostic_groups=[]
for treatment in ['inherited','removed','rebuild','equivalent']:
 batch=[r for r in diagnostic if r['parent_treatment']==treatment]
 diagnostic_groups.append({'treatment':treatment,'streams':len(batch),'qualified':sum(r['qualified'] for r in batch),'valid':sum(r['valid'] for r in batch),
  'mean_work':mean([r['work'] for r in batch]),'complete_three_stage_chains':sum(set(a['stage'] for a in r['assets'])=={'dispatch','lookahead','repair'} for r in batch),
  'active_three_stage_chains':sum(set(a['stage'] for a in r['assets'] if a['active'])=={'dispatch','lookahead','repair'} for r in batch),
  'gates':dict(Counter(d['decision'] for r in batch for d in r['discoveries'])),
  'dispatch_rollout_calls':sum(r['inherited_policy_calls']['dispatch_rollouts'] for r in batch),
  'lookahead_repair_decisions':sum(r['inherited_policy_calls']['lookahead_repair_decisions'] for r in batch),
  'reconstruction_exact_recoveries':sum(e.get('exact_contents_recovered',False) for r in batch for e in r['constructive_events']),
  'scope':'Correctness-only forced construction does not count as economically promoted production capability.'})
diag_pairs=[]
for stream in sorted(set(r['stream'] for r in diagnostic)):
 cases={r['parent_treatment']:r for r in diagnostic if r['stream']==stream};original=cases['inherited']
 for treatment in ['removed','rebuild','equivalent']:
  other=cases[treatment];common=min(len(original['mission_results']),len(other['mission_results']))
  diag_pairs.append({'stream':stream,'treatment':treatment,'qualified_difference':other['qualified']-original['qualified'],'work_difference':other['work']-original['work'],
   'same_fresh_schedules_on_common_prefix':all(original['mission_results'][i]['schedule_sha256']==other['mission_results'][i]['schedule_sha256'] for i in range(common)),
   'common_missions':common,'all_missions_completed_both':common==4})

window_effects=[]
for s in sorted(set(fly)&set(portfolio)):
 f=fly[s]['windows'];p=portfolio[s]['windows'];fr=[w['qualified_per_100k_work'] for w in f];pr=[w['qualified_per_100k_work'] for w in p]
 window_effects.append({'stream':s,'flywheel_rates':fr,'portfolio_rates':pr,'difference_in_last_minus_first_rate':(fr[-1]-fr[0])-(pr[-1]-pr[0]) if all(x is not None for x in [fr[0],fr[-1],pr[0],pr[-1]]) else None})
rate_values=[r['difference_in_last_minus_first_rate'] for r in window_effects if r['difference_in_last_minus_first_rate'] is not None]
native=json.loads((root/'NATIVE_REFERENCE.json').read_text());native_summary=[]
for mode in ['deadline','makespan']:
 batch=[r for r in native['rows'] if r['mode']==mode];native_summary.append({'mode':mode,'tasks':len(batch),'valid':sum(r['valid'] for r in batch),'qualified':sum(r['qualified'] for r in batch),
  'mean_end_to_end_ms':mean([r['attributable_end_to_end_ms'] for r in batch]),'mean_solver_reported_ms':mean([r['native']['model_solve_ms'] for r in batch if r['native'] and 'model_solve_ms' in r['native']]),
  'timeouts_or_limits':sum(r['error'] is not None or r['native'] is not None and r['native'].get('status_code')==1 for r in batch),
  'reported_status_counts':dict(Counter(str(r['native'].get('status_code',r['native'].get('status'))) if r['native'] else str(r['error']) for r in batch)),
  'objective_targets_makespan':mode=='makespan','practical_workflow_valid':sum(r.get('practical_workflow_valid',r['valid'] or r['portfolio_valid']) for r in batch),
  'practical_workflow_qualified':sum(r.get('practical_workflow_qualified',r['qualified'] or r['portfolio_qualified']) for r in batch),
  'mean_practical_workflow_ms':mean([r.get('practical_workflow_end_to_end_ms',r['native_and_check_ms']+r['portfolio_preparation_ms']) for r in batch]),
  'comparison_work_units':None})

run_start=json.loads((root/'RUN_START.json').read_text())
summary={'schema':'agi-alpha-strategy-summary/v1','run_mode':run_start.get('run_mode'),'primary':primary,'arms':arm_results,'conventional_equivalence':equivalence,
 'diagnostic':diagnostic_groups,'diagnostic_pairs':diag_pairs,'native':native_summary,'native_startup_ms':native['startup_ms'],
 'increasing_rate':{'status':'EXPLORATORY_ONLY_NOT_A_SELF_ACCELERATION_CLAIM','windows':window_effects,'difference_in_changes':ci(rate_values),
  'note':'Balanced scope mixture; no endogenous saved-work reinvestment mechanism or rate-growth guarantee. Stopped/no-work windows remain missing-rate records, never discarded from primary coverage.'},
 'limitations':['Synthetic supplied tasks and baseline schedules; no external demand, revenue, physical construction or production authority.',
 'Closed grammar search and ordinary method composition; equal conventional learner is fully enabled.',
 'Named resource units are not money, machine instructions, or equal total computation against native MILP.',
 'One machine, one implementation family,12 independent stream seeds; shared project authorship limits independence.',
 'Engineering/model/human commissioning labor is unpriced; no all-in profit claim.'],
 'artifact_counts':{'main_trials':len(main),'diagnostic_trials':len(diagnostic),'unique_primary_missions':sum(r['offered'] for r in fly.values()),'native_cases':len(native['rows'])}}
(root/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'COST_BREAKDOWN.json').write_text(json.dumps(arm_results,indent=2)+'\n')
(root/'DIAGNOSTIC_SUMMARY.json').write_text(json.dumps({'groups':diagnostic_groups,'pairs':diag_pairs},indent=2)+'\n')
with (root/'ARM_RESULTS.csv').open('w',newline='') as f:
 columns=['budget','arm','streams','offered','attempted','valid','qualified','mean_qualified','mean_work','total_work','coverage_percent','stopped','active_assets','mean_wall_ms'];writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(arm_results)
print(json.dumps({'summary':str(root/'SUMMARY.json'),'primary_streams':len(ids),'main_trials':len(main),'diagnostic_trials':len(diagnostic)}))
