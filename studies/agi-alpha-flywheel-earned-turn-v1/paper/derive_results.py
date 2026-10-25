import json,collections,statistics,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results/confirmation-v1';analysis=json.loads((R/'ANALYSIS.json').read_text());trials=[]
for p in sorted((R/'trials').iterdir()):
 s=json.loads((p/'summary.json').read_text());rows=json.loads((p/'rows.json').read_text());trials.append({'summary':s,'rows':rows,'path':str(p.relative_to(ROOT))})
phase={};costs={}
for arm in analysis['arms']:
 tt=[t for t in trials if t['summary']['arm']==arm];allrows=[r for t in tt for r in t['rows']];costs[arm]={'whole_cpu_ms':sum(t['summary']['total_cpu_ms'] for t in tt),'algorithm_cpu_ms':sum(r['algorithm_cpu_ms'] for r in allrows),'checker_cpu_ms':sum(r['checker_cpu_ms'] for r in allrows),'node_cpu_ms':sum(r['node_cpu_ms'] for r in allrows),'action_cpu_ms':sum(r['cpu_ms'] for r in allrows),'control_cpu_ms':sum(t['summary']['setup_custody_artifact_io_cpu_ms'] for t in tt),'median_action_wall_ms':float(np.median([r['wall_ms'] for r in allrows])),'p95_action_wall_ms':float(np.quantile([r['wall_ms'] for r in allrows],.95))}
 for regime in ['recurring','rare','wide_change','maintenance']:
  for mid in ['A','B','C','D','RESTORE','SHIFT']:
   rr=[r for t in tt if t['summary']['regime']['name']==regime for r in t['rows'] if r['id']==mid or mid in ['B','D'] and r['id'].startswith(mid)]
   if rr:phase[f'{arm}:{regime}:{mid}']={'n':len(rr),'mean_cpu_ms':statistics.mean(r['cpu_ms'] for r in rr),'mean_algorithm_cpu_ms':statistics.mean(r['algorithm_cpu_ms'] for r in rr),'mean_checker_cpu_ms':statistics.mean(r['checker_cpu_ms'] for r in rr)}
f=R/'trials/00-recurring-flywheel';rows=json.loads((f/'rows.json').read_text());events=json.loads((f/'events.json').read_text());tasks=json.loads((f/'tasks.json').read_text());z=np.load(f/'solutions.npz');example={'trial':str(f.relative_to(ROOT)),'seed':json.loads((f/'summary.json').read_text())['seed'],'missions':[{k:r[k] for k in ['id','input_digest','solution_digest','receipt_digest','details','checker','cpu_ms']} for r in rows if r['id'] in ['A','B08','C','D01','SHIFT','UNSUPPORTED']],'successor_requirement':next(e for e in events if e['kind']=='SUCCESSOR_REQUIREMENT'),'first_output':{'nodes':tasks['A']['n'],'edges':len(tasks['A']['edges']),'max_abs_response':float(np.max(np.abs(z['A']))),'min_response':float(z['A'].min()),'max_response':float(z['A'].max()),'input_loads_changed_B08':tasks['A']['rhs']!=tasks['B08']['rhs']}}
res={'analysis_sha256':hashlib.sha256((R/'ANALYSIS.json').read_bytes()).hexdigest(),'costs':costs,'phases':phase,'example_first_registered_stream':example,'all_regime_scope_refusals':sum(r['id']=='UNSUPPORTED' and not r['valid'] and r['checker']['reason']=='CONDUCTANCE_SCOPE' for t in trials for r in t['rows']),'maintenance_rechecks':sum(r['id']=='RESTORE' and r['valid'] for t in trials for r in t['rows']),'prior_file_freeze_unchanged':'rechecked separately','derived_not_new_confirmation':True}
(R/'DERIVED_REPORT.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'costs':costs,'example':example,'refusals':res['all_regime_scope_refusals'],'restores':res['maintenance_rechecks']},indent=2))
