"""Independent reconciliation of post-result sensitivity records, no model import."""
import gzip,hashlib,json,math
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'economics/outputs'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def money(x):return int((Decimal(str(x))*1000000).to_integral_value(rounding=ROUND_HALF_UP))
def part(x,r):return int((Decimal(x)*Decimal(str(r))).to_integral_value(rounding=ROUND_HALF_UP))
def near(a,b):return abs(a-b)<=0.00000051
checks=0;failures=[]
def req(ok,label):
 global checks
 checks+=1
 if not ok:failures.append(label)
base=read(ROOT/'protocol/economics_config.json');settings=read(ROOT/'protocol/economics_addendum_config.json');data=read(OUT/'addendum.json');summary=read(OUT/'summary.json')
req(data['provenance']['addendum_config_sha256']==sha(ROOT/'protocol/economics_addendum_config.json'),'sensitivity config hash')
req(data['provenance']['engine_sha256']==sha(ROOT/'economics/run_economics.py'),'sensitivity final engine hash')
req(data['provenance']['script_sha256']==settings['script_sha256']==sha(ROOT/'economics/run_addendum.py'),'sensitivity script hash')
req(data['provenance']['measurement_bridge_sha256']==sha(ROOT/'outputs/economics_bridge.json'),'sensitivity measured bridge hash')
req('POST-RESULT' in data['provenance']['status'],'sensitivity prospective scope')
results={r['scenario']:r for r in data['results']};events=[json.loads(x) for x in gzip.decompress((OUT/'addendum_events.jsonl.gz').read_bytes()).decode().splitlines()]
by=defaultdict(list);balances={};closing={};eventnames=set()
for i,e in enumerate(events):
 name=e['scenario'];cycle=e['cycle'];by[name,cycle].append(e);b=balances.setdefault(name,[0]*5)
 delta=[money(e[c+'_delta_usd']) for c in ['cash','receivable','collateral','capital_asset','payable']]
 for j in range(5):b[j]+=delta[j]
 req(min(b)>=0 and b[0]==money(e['cash_balance_usd']),f'event {i} account conservation')
 req(e['evidence_class']=='SIMULATED' and e['policy_fraction']==settings['policy_fraction'],f'event {i} evidence/policy')
 a=money(e['amount_usd']);event=e['event'];eventnames.add(event)
 if event=='external_initial_capital':expected=[a,0,0,0,0];req(a==money(base['initial_external_capital_usd']) and cycle==0,f'event {i} initial financing')
 elif event=='invoice_worker_entitlement':expected=[0,a,0,0,0]
 elif event=='external_worker_collection':expected=[a,-a,0,0,0]
 elif event=='receivable_default_writeoff':expected=[0,-a,0,0,0]
 elif event=='customer_refund':expected=[-a,0,0,0,0]
 elif event in ['delivery_business_cost','fixed_business_setup_and_maintenance','conversion_and_volatility_cost']:expected=[delta[0],0,0,0,a+delta[0]]
 elif event=='prior_operating_payable_payment':expected=[-a,0,0,0,-a]
 else:expected=None
 req(delta==expected,f'event {i} classified amounts')
 closing[name,cycle]=b.copy()
previous={};cum=defaultdict(lambda:defaultdict(int));rows_by=defaultdict(list)
for row in data['ledger']:
 name=row['scenario'];cycle=row['cycle'];label=f'{name} c{cycle}';r=results[name];es=by[name,cycle];rows_by[name].append(row)
 old=previous.get(name,[money(base['initial_external_capital_usd']),0,0,0,0]);end=closing[name,cycle]
 def total(kind,field='amount_usd'):return sum(money(e.get(field,0)) for e in es if e['event']==kind)
 got=total('external_worker_collection');refund=total('customer_refund');invoiced=total('invoice_worker_entitlement');default=total('receivable_default_writeoff')
 op=[e for e in es if e['event'] in ['delivery_business_cost','fixed_business_setup_and_maintenance','conversion_and_volatility_cost']];paid=-sum(money(e['cash_delta_usd']) for e in op)+total('prior_operating_payable_payment');incurred=sum(money(e['amount_usd']) for e in op)
 req(end[0]==old[0]+got-refund-paid and end[1]==old[1]+invoiced-got-default,label+' cash/AR identity')
 req(end[4]==old[4]+incurred-paid,label+' unpaid obligations retained')
 req(money(row['paid_operating_cost_usd'])==paid and money(row['incurred_operating_cost_usd'])==incurred,label+' operating cost record')
 for i,k in enumerate(['closing_cash_usd','closing_receivables_usd','closing_collateral_usd','productive_asset_book_value_usd','closing_payables_usd']):req(money(row[k])==end[i],label+' '+k)
 c=cum[name];c['net']+=got-refund;c['paid']+=paid
 reserve=part(max(0,c['net']-c['paid']-end[4]),base['business']['cash_profit_obligation_reserve_fraction']);earned=c['net']-c['paid']-end[4]
 available=max(0,min(earned-reserve,end[0]-end[4]-reserve-money(base['business']['contingency_cash_floor_usd'])))
 req(money(row['available_preallocation_operating_surplus_usd'])==available and money(row['obligation_cash_reserve_usd'])==reserve,label+' surplus/reserve')
 human=base['business']['fixed_administration_minutes_per_cycle'];extra_h=r.get('extra_engineer_hours',0);extra_review=r.get('extra_review_hours',0)
 if cycle==1:human+=60*(base['business']['initial_integration_engineer_hours']+base['business']['unsuccessful_build_engineer_hours']+base['business']['initial_verification_hours']+extra_h+extra_review)
 nonproduction=human
 for f in base['families']:
  x=base['families'][f];orders=row['accepted_by_family'][f]+row['failures_by_family'][f];attempts=row['attempts_by_family'][f];accepted=row['accepted_by_family'][f]
  human+=orders*x['setup_minutes_per_order']+attempts*(x['supervision_minutes_per_attempt']+x['verification_minutes_per_attempt'])+(attempts-orders)*x['retry_correction_minutes']+accepted*x['support_minutes_per_accepted']
  req(orders==sum(e['event']=='delivery_business_cost' and e.get('family')==f for e in es) and accepted==sum(e['event']=='invoice_worker_entitlement' and e.get('family')==f for e in es),label+' orders/accepted '+f)
 budget=r.get('full_human_minutes_per_cycle',base['human_attention_budget_minutes'])
 req(near(row['estimated_human_minutes'],human) and human<=budget,label+' full human resource scope')
 req(near(row['estimated_elapsed_hours'],row['provider_attempts']*base['business']['elapsed_hours_per_attempt']+nonproduction/60),label+' elapsed allocation')
 req(not row['purchased_projects'] and not row['productive_investment_usd'],label+' no invented capability investment')
 previous[name]=end
for name,r in results.items():
 rs=rows_by[name];last=rs[-1]
 req(len(rs)==base['cycles'],name+' complete cycles')
 for f in base['families']:req(r['accepted_by_family'][f]==sum(x['accepted_by_family'][f] for x in rs),name+' accepted totals '+f)
 req(r['closing_cash_usd']==last['closing_cash_usd'] and r['closing_payables_usd']==last['closing_payables_usd'] and r['available_operating_surplus_usd']==last['available_preallocation_operating_surplus_usd'],name+' closing totals')
 req(r['live_agent_cost_usd'] is None and r['self_financing_demonstrated'] is False,name+' empirical limits')
 if r['sensitivity_kind']=='remediation_cost':
  cost=r['extra_engineer_hours']*base['rates']['software_engineer_usd_per_hour']+r['extra_review_hours']*base['rates']['reviewer_usd_per_hour'];req(near(r['extra_estimated_cost_usd'],cost) and r['actual_remediation_hours'] is None,name+' unknown effort remains assumed')
req(len(results)==13 and len(data['ledger'])==78,'sensitivity finite design counts')
insolvent=results['posthoc_remediation_16h'];req(sum(insolvent['accepted_by_family'].values())==0 and insolvent['closing_cash_usd']==0 and insolvent['closing_payables_usd']>0,'prelaunch insolvency preserved')

alloc_cfg=read(ROOT/'protocol/economics_authorship_addendum_config.json');allocation=read(OUT/'authorship_allocation.json');b=summary['base'];n=sum(b['accepted_by_family'].values())
req(allocation['provenance']['config_sha256']==sha(ROOT/'protocol/economics_authorship_addendum_config.json'),'authorship config hash')
req(allocation['provenance']['script_sha256']==alloc_cfg['script_sha256']==sha(ROOT/'economics/paper_summary.py'),'authorship executable source hash')
req(allocation['provenance']['primary_summary_sha256']==sha(OUT/'summary.json'),'authorship source results hash')
for i,row in enumerate(allocation['rows']):
 h=row['extra_engineer_hours'];review=h*alloc_cfg['review_hours_per_engineer_hour'];bill=row['extra_unmetered_model_tool_bill_usd'];cost=h*base['rates']['software_engineer_usd_per_hour']+review*base['rates']['reviewer_usd_per_hour']+bill
 req(near(row['incremental_unmetered_cost_usd'],cost) and row['extra_review_hours']==review,f'authorship {i} cost')
 for f in base['families']:
  unit=b['full_cost_per_accepted_by_family'][f]+cost/n;rate=base['rates'][base['families'][f]['traditional_rate_key']]
  req(near(row['allocation_only_cost_per_accepted_by_family'][f],unit) and near(row['allocation_only_internal_break_even_minutes'][f],60*unit/rate),f'authorship {i} allocation '+f)
 cashprofit=b['cumulative_net_external_collections_usd']-b['cumulative_operating_cash_paid_usd'];expected=max(0,cashprofit-cost)*(1-base['business']['cash_profit_obligation_reserve_fraction'])
 req(near(row['allocation_only_available_surplus_after_20pct_obligation_buffer_usd'],expected),f'authorship {i} retrospective surplus')
 req(row['actual_authorship_time'] is None and row['actual_model_tool_bill_usd'] is None and 'no demand or liquidity rerun' in row['evidence_class'],f'authorship {i} classification')
req(len(allocation['rows'])==20,'authorship finite grid count')
report={'status':'PASS' if not failures else 'FAIL','checks':checks,'failures':failures,'post_result_simulations':len(results),'cycles':len(data['ledger']),'events':len(events),'allocation_only_rows':len(allocation['rows']),'prelaunch_insolvency_case':{'scenario':insolvent['scenario'],'accepted_by_family':insolvent['accepted_by_family'],'closing_cash_usd':insolvent['closing_cash_usd'],'closing_payables_usd':insolvent['closing_payables_usd']},'source_hashes':{'addendum':sha(OUT/'addendum.json'),'addendum_events':sha(OUT/'addendum_events.jsonl.gz'),'allocation':sha(OUT/'authorship_allocation.json'),'engine':sha(ROOT/'economics/run_economics.py')},'independence':'Separate review code, no producer/model imports or executions. Common commission/session/model family and sources.','limits':['Post-result sensitivities preserve primary assumptions and outcomes; they are not prospective primary findings.','Authorship allocation has no demand or liquidity replay. Its remaining profit cannot refute the separate prelaunch-insolvency simulation.','Actual authorship/remediation time and model/tool bills remain unmeasured.','The same event model generated all financial cases; arithmetic agreement does not validate commercial premises.']}
(ROOT/'review/INDEPENDENT_SENSITIVITY_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(0 if not failures else 1)
