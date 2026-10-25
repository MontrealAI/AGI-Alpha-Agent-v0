import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 out=ROOT/'economics/outputs';s=json.loads((out/'summary.json').read_text());cfg=json.loads((ROOT/'protocol/economics_config.json').read_text());led=json.loads((out/'ledger.json').read_text())['rows'];families=json.loads((out/'family_results.json').read_text())['rows'];extra=json.loads((ROOT/'protocol/economics_authorship_addendum_config.json').read_text());b=s['base'];n=sum(b['accepted_by_family'].values());r=cfg['rates'];cashprofit=b['cumulative_net_external_collections_usd']-b['cumulative_operating_cash_paid_usd'];allocation=[]
 for hours in extra['additional_authorship_engineer_hours']:
  for bill in extra['additional_unmetered_model_tool_bill_usd']:
   review=hours*extra['review_hours_per_engineer_hour'];cost=hours*r['software_engineer_usd_per_hour']+review*r['reviewer_usd_per_hour']+bill
   allocation.append({'extra_engineer_hours':hours,'extra_review_hours':review,'extra_unmetered_model_tool_bill_usd':bill,'incremental_unmetered_cost_usd':round(cost,6),'allocation_only_cost_per_accepted_by_family':{f:round(v+cost/n,6) for f,v in b['full_cost_per_accepted_by_family'].items()},'allocation_only_internal_break_even_minutes':{f:round(60*(v+cost/n)/r[cfg['families'][f]['traditional_rate_key']],6) for f,v in b['full_cost_per_accepted_by_family'].items()},'allocation_only_available_surplus_after_20pct_obligation_buffer_usd':round(max(0,cashprofit-cost)*0.8,6),'actual_authorship_time':None,'actual_model_tool_bill_usd':None,'evidence_class':'ASSUMED cost-allocation sensitivity; no demand or liquidity rerun'})
 (out/'authorship_allocation.json').write_text(json.dumps({'status':'POST-RESULT ADDENDUM; frozen primary results unchanged','provenance':{'config_sha256':sha(ROOT/'protocol/economics_authorship_addendum_config.json'),'primary_summary_sha256':sha(out/'summary.json'),'script_sha256':sha(__file__)},'warning':'These are extra costs beyond frozen integration/build estimates, allocated equally per accepted output across362modeled outputs. Do not mistake allocated end-period profitability for prelaunch liquidity. Separate remediation addendum reruns early cash exhaustion. No actual authorship hour or model/tool bill was measured.','rows':allocation},indent=2)+'\n')
 score=[]
 for f,cost in b['full_cost_per_accepted_by_family'].items():
  x=next(z for z in families if z['scenario']=='base' and z['policy_fraction']==0 and z['cycle']==6 and z['family']==f);rate=x['traditional_hourly_rate_usd']
  score.append({'family':f,'accepted_six_cycles':b['accepted_by_family'][f],'modeled_full_cost_per_accepted_usd':cost,'traditional_rate_usd_per_hour':rate,'internal_break_even_human_minutes':round(60*cost/rate,6),'customer_price_usd':x['price_usd'],'customer_all_in_with_review_usd':x['customer_all_in_usd'],'customer_break_even_human_minutes':x['customer_human_break_even_minutes'],'customer_savings_at_assumed_60min_usd':round(rate-x['customer_all_in_usd'],6),'customer_savings_at_assumed_120min_usd':round(2*rate-x['customer_all_in_usd'],6),'live_full_agent_cost_usd':None})
 compact={'status':'Observed measurements and modeled business claims remain separate','source_summary_sha256':sha(out/'summary.json'),'base':b,'commercial_scorecard':score,'base_cycle_table':[x for x in led if x['scenario']=='base' and x['policy_fraction']==0.5],'selected_scenarios':[x for x in s['scenario_results'] if x['policy_fraction'] in (0,0.5)],'investment_metric':'npv_usd means undiscounted finite-life net benefit at zero discount rate','commensurability_limit':'Observed adapters jointly generate three family deliverables on each of6project instances, reused acrosscycles/arms. Financial scenarios separately price family outputs, model independent operational failures and assume repeated demand. Shared native CPU is divided once among three outputs; no threefold empirical market coverage or independent customer validation follows. Joint cost allocation is conventional, not measured marginal cost per service.','unknowns':['full authenticated Agent billing and attention','external accepted-demand and willingness to pay','actual study authorship and remediation effort','same-budget frontier expansion versus conventional cache','profitable child-capability return']}
 (out/'paper_numbers.json').write_text(json.dumps(compact,indent=2)+'\n')
 fields=['scenario','policy_fraction','cycle','closing_cash_usd','available_preallocation_operating_surplus_usd','estimated_human_minutes','estimated_elapsed_hours','productive_investment_usd','full_surplus_next_plan_coverage','next_plan_budget_feasible']
 with (out/'chart_cycle_cash.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields+['release_assurance','rollout_planning','bilingual_dossier']);w.writeheader()
  for x in led:w.writerow(dict({k:x[k] for k in fields},**x['accepted_by_family']))
 with (out/'chart_policy_outputs.csv').open('w',newline='') as f:
  fields=['scenario','policy_fraction','closing_cash_usd','available_operating_surplus_usd','cumulative_investment_usd'];w=csv.DictWriter(f,fieldnames=fields+['release_assurance','rollout_planning','bilingual_dossier']);w.writeheader()
  for x in s['scenario_results']:w.writerow(dict({k:x[k] for k in fields},**x['accepted_by_family']))
 print(json.dumps({'scorecard':score,'authorship_allocation_rows':len(allocation),'source_summary_sha256':sha(out/'summary.json')},indent=2))

if __name__=='__main__':main()
