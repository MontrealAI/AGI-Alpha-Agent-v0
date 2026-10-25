import copy,gzip,hashlib,json
from pathlib import Path
from run_economics import Model,load_bridge,sha,ROOT

def main():
 ap=ROOT/'protocol/economics_addendum_config.json';a=json.loads(ap.read_text());base=json.loads((ROOT/'protocol/economics_config.json').read_text());bridge,metrics,saving=load_bridge(ROOT/'outputs/economics_bridge.json')
 if sha(ROOT/'protocol/economics_config.json')!=a['primary_config_sha256']:raise ValueError('Primary frozen config differs')
 output=[];events=[];ledgers=[]
 for h in a['remediation_extra_engineer_hours']:
  c=copy.deepcopy(base);c['business']['initial_integration_engineer_hours']+=h;c['business']['initial_verification_hours']+=h*a['review_hours_per_extra_engineer_hour']
  s={'id':f'posthoc_remediation_{h:g}h','route':'direct','label':'Additional remediation before first modeled customer delivery; actual hours unknown'}
  m=Model(c,s,a['policy_fraction'],bridge,metrics,saving).run()
  x=dict(m.summary,sensitivity_kind='remediation_cost',extra_engineer_hours=h,extra_review_hours=h*a['review_hours_per_extra_engineer_hour'],extra_estimated_cost_usd=round(h*c['rates']['software_engineer_usd_per_hour']+h*a['review_hours_per_extra_engineer_hour']*c['rates']['reviewer_usd_per_hour'],6),actual_remediation_hours=None)
  output.append(x);events.extend(m.events);ledgers.extend(m.ledger)
 for minutes in a['human_attention_budget_minutes']:
  c=copy.deepcopy(base);c['human_attention_budget_minutes']=minutes;s={'id':f'posthoc_review_budget_{minutes}','route':'direct','label':'Fixed full human attention budget within this sensitivity case'}
  m=Model(c,s,a['policy_fraction'],bridge,metrics,saving).run();output.append(dict(m.summary,sensitivity_kind='human_attention_budget',full_human_minutes_per_cycle=minutes));events.extend(m.events);ledgers.extend(m.ledger)
 for factor in a['model_tool_cost_multiplier']:
  c=copy.deepcopy(base)
  for f in c['families'].values():f['model_tool_usd_per_attempt']*=factor
  s={'id':f'posthoc_tool_cost_{factor:g}x','route':'direct','label':'Assumed orchestration/model/tool cost sensitivity'}
  m=Model(c,s,a['policy_fraction'],bridge,metrics,saving).run();output.append(dict(m.summary,sensitivity_kind='model_tool_cost',model_tool_cost_multiplier=factor));events.extend(m.events);ledgers.extend(m.ledger)
 provenance={'status':'POST-RESULT SENSITIVITY ADDENDUM; primary assumptions and results preserved','frozen_addendum':str(ap.relative_to(ROOT)),'addendum_config_sha256':sha(ap),'engine_sha256':sha(ROOT/'economics/run_economics.py'),'script_sha256':sha(__file__),'measurement_bridge_sha256':sha(ROOT/'outputs/economics_bridge.json'),'evidence_class':'SIMULATED; no observed remediation time or vendor/model bill','independence':'Author calculation; shares primary model and same session'}
 out=ROOT/'economics/outputs';(out/'addendum.json').write_text(json.dumps({'provenance':provenance,'results':output,'ledger':ledgers},indent=2)+'\n')
 raw=''.join(json.dumps(x,sort_keys=True)+'\n' for x in events).encode();(out/'addendum_events.jsonl.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
 print(json.dumps({'results':output,'events':len(events)},indent=2))

if __name__=='__main__':main()
