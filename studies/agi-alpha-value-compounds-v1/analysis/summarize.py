# SPDX-License-Identifier: Apache-2.0
"""Aggregate frozen outcomes; no outcome-dependent method changes."""
from pathlib import Path
import json,statistics,hashlib,csv,sys
R=Path(__file__).resolve().parents[1]
run=json.loads((R/'results/confirmation/runs.json').read_text())
assert (R/'results/confirmation/COMPLETED.json').exists(),'Campaign incomplete'
registry=json.loads((R/'data/missions.json').read_text())['missions']
rows=run['rows'];assert len(rows)==108
missions=[];failures=[];totals={a:{'validated_scoped_packets':0,'source_binding_loss_rows':0,'griffe_alerts':0,'native_refusals':0,'strict_consumer_losses':0,'candidate_consumer_losses':0} for a in ['incumbent','retained','conventional']}
for ident,item in registry.items():
 if item.get('role')!='held-out-historical-confirmation':continue
 out={'id':ident,'repository':item['repository'],'before_ref':item['before_ref'],'after_ref':item['after_ref'],'before_tag':item['before_tag'],'after_tag':item['after_tag'],'arms':{}}
 for arm in totals:
  rr=[x for x in rows if x['mission']==ident and x['arm']==arm];assert len(rr)==3
  assert len({json.dumps(x['summary'],sort_keys=True) for x in rr})==1,'Nondeterministic summary'
  assert len({x['decision'] for x in rr})==1,'Nondeterministic acceptance'
  first=next(x for x in rr if x['repetition']==1);source=R/first['full_evidence']['path'];raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==first['full_evidence']['sha256']
  d=json.loads(raw);c=d['consumer_assessment'];valid=d['summary']['independent_report_valid'];out['changed_modules']=d['changed_modules']
  flags=[{'path':m['path'],'name':f['name'],'witness':f.get('witness'),'status':f['status']} for m in d['reports'] for f in m['functions'] if f['status']=='call_loss']
  errors=[{'path':v['path'],'errors':v.get('errors'),'unknowns':v.get('unknowns')} for v in d['independent_validation'] if not v['accepted']]
  nalerts=sum(len(m.get('griffe_alerts',[])) for m in d['reports'])
  values={'decision':first['decision'],'valid':valid is True,'functions':first['functions'],'binding_losses':len(flags),'binding_loss_details':flags,'strict_consumer_losses':len(c.get('findings',[])),'candidate_consumer_losses':len(c.get('syntactic_candidate_findings',[])),'consumer_coverage':c.get('coverage'),'candidate_coverage':c.get('candidate_coverage'),'griffe_alert_count':nalerts,'native_source_refusals':first['native_refusals'],'median_workbench_seconds':statistics.median(x['workbench_elapsed_ms'] for x in rr)/1000,'min_workbench_seconds':min(x['workbench_elapsed_ms'] for x in rr)/1000,'max_workbench_seconds':max(x['workbench_elapsed_ms'] for x in rr)/1000,'median_cpu_seconds':statistics.median(x['cpu_ns'] for x in rr)/1e9,'input_bytes':d['meter']['input_bytes'],'consumer_bytes':d['meter']['consumer_bytes'],'resources_by_repeat':[x['resources'] for x in rr],'errors':errors,'evidence':first['full_evidence'],'pack':first['pack'],'unresolved_is_safe_clearance':False,'whole_customer_upgrade_accepted':None}
  out['arms'][arm]=values
  t=totals[arm];t['validated_scoped_packets']+=int(valid is True);t['source_binding_loss_rows']+=len(flags);t['griffe_alerts']+=nalerts;t['native_refusals']+=first['native_refusals'];t['strict_consumer_losses']+=values['strict_consumer_losses'];t['candidate_consumer_losses']+=values['candidate_consumer_losses']
  if errors:failures.append({'mission':ident,'arm':arm,'errors':errors})
 missions.append(out)
for arm,t in totals.items():
 xs=[x['arms'][arm]['median_workbench_seconds'] for x in missions];t['median_of_mission_medians_seconds']=statistics.median(xs);t['range_of_mission_medians_seconds']=[min(xs),max(xs)];t['sum_median_cpu_seconds']=sum(x['arms'][arm]['median_cpu_seconds'] for x in missions)
process=json.loads((R/'metering/campaign-process.json').read_text())
summary={'schema':'value-compounds-results/v1','unique_substantive_historical_transitions':len(missions),'project_clusters':3,'actual_paid_customer_jobs':0,'timing_evaluations':108,'repetitions_are_jobs':False,'all_reported_counts_unit':'Callable rows and call sites are not distinct bugs or customer missions.','totals':totals,'missions':missions,'failures':failures,'process_resources':process,'claim':'Useful scoped decision support with a strong conventional method; no proven complete economic return or algorithmic superiority.','economic_input':{'schema':'value-compounds-economic-input/v1','capability_id':'call-compatibility','observed':{'collections_minor':0,'missions':[{'mission_id':m['id'],'acceptance':'accepted' if m['arms']['conventional']['valid'] else 'rejected','reference':m['arms']['conventional']['evidence']['path']+'; SHA256 '+m['arms']['conventional']['evidence']['sha256']+'; accepted scoped research packet only, not a completed production upgrade'} for m in missions],'resources':{'complete_confirmation_campaign':process,'timing_evaluations':108,'unique_transitions':len(missions),'runtime_model_calls':0,'runtime_network_requests':0,'construction_inference_tokens':None,'construction_inference_usd':None},'limitations':['Historical research work, no paid demand.','Same captured consumer scope across revisions; unresolved dynamic and behavioral work persists.','Canonical acceptance means internally verified scoped packet, not customer acceptance or production qualification.','Construction includes the rejected custom candidate and all integration and validation attempts; costs unknown.','One scope-screen handling disagreement recurs across callable rows; no actual lost binding demonstrated in those disputed rows.']}}}
(R/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (R/'results/outcomes.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['mission','repository','before_tag','after_tag','arm','decision','changed_modules','binding_loss_rows','strict_consumer_losses','syntactic_candidate_losses','median_workbench_seconds','median_cpu_seconds','griffe_alerts','native_refusals']);w.writeheader()
 for m in missions:
  for a,x in m['arms'].items():w.writerow({'mission':m['id'],'repository':m['repository'],'before_tag':m['before_tag'],'after_tag':m['after_tag'],'arm':a,'decision':x['decision'],'changed_modules':m['changed_modules'],'binding_loss_rows':x['binding_losses'],'strict_consumer_losses':x['strict_consumer_losses'],'syntactic_candidate_losses':x['candidate_consumer_losses'],'median_workbench_seconds':x['median_workbench_seconds'],'median_cpu_seconds':x['median_cpu_seconds'],'griffe_alerts':x['griffe_alert_count'],'native_refusals':x['native_source_refusals']})
print(json.dumps({'totals':totals,'failures':failures,'process':process},indent=2))
