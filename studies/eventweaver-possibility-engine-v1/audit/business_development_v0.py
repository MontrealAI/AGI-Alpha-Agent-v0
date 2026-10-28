from __future__ import annotations
import argparse, csv, hashlib, heapq, json, math, random, statistics, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
A=json.loads((ROOT/'protocol/business_assumptions.json').read_text())
SCENARIOS={
 'base':{},
 'price_war':{'competitor_factor':0.68,'competitor_response_day':60},
 'weak_demand':{'demand_factor':0.55,'trust_factor':1.35},
 'supplier_shock':{'rate_factor':1.45,'capacity_factor':0.6,'common_probability':0.30},
 'slow_payment':{'payment_lag_factor':2.5,'default_add':0.10},
 'correlated_downturn':{'demand_factor':0.65,'rate_factor':1.35,'capacity_factor':0.65,'common_probability':0.35,'default_add':0.10,'payment_lag_factor':2,'competitor_factor':0.80},
 'identical_free_library':{'competitor_factor':0.50,'competitor_response_day':0,'trust_factor':1.2,'outside_hours_factor':0.65},
 'conditional_ai_improvement':{'ours_hours_factor':0.7,'outside_hours_factor':0.7,'competitor_factor':0.78,'inference_factor':0.5},
 'no_collection_recourse':{'strategic_default':True},
 'high_demand':{'demand_factor':2.5}
}

def rng(seed,key):
 return random.Random(int.from_bytes(hashlib.sha256(f'{seed}:{key}'.encode()).digest()[:8],'big'))

def money(x): return int(round(x*100))

class Ledger:
 def __init__(self,details=False):
  self.b=defaultdict(int); self.rows=[]; self.details=details; self.free_flow=0; self.capital=0; self.peak_restricted=0; self.peak_debt=0; self.shortfall=0; self.rescue=0; self.interest=0
 def post(self,day,debit,credit,cents,kind,buyer=''):
  if cents<0: raise ValueError('negative journal amount')
  if not cents:return
  self.b[debit]+=cents; self.b[credit]-=cents
  if self.details:self.rows.append({'day':day,'debit':debit,'credit':credit,'cents':cents,'kind':kind,'buyer':buyer})
  if debit=='cash' and kind not in ('equity','rescue_equity','loan_draw'):self.free_flow+=cents
  if credit=='cash' and kind!='loan_repay':self.free_flow-=cents
  self.capital=max(self.capital,-self.free_flow);self.peak_restricted=max(self.peak_restricted,self.b['restricted_cash']);self.peak_debt=max(self.peak_debt,-self.b['debt'])
 def fund(self,day,cents):
  need=max(0,cents-self.b['cash'])
  if need:
   draw=min(need,max(0,money(A['credit_limit'])+self.b['debt']))
   self.post(day,'cash','debt',draw,'loan_draw');need-=draw
   if need:
    self.shortfall=max(self.shortfall,need);self.rescue+=need
    self.post(day,'cash','equity',need,'rescue_equity')
 def expense(self,day,amount,kind,buyer=''):
  c=money(amount);self.fund(day,c);self.post(day,'expense:'+kind,'cash',c,kind,buyer)
 def settle(self,day):
  repay=min(self.b['cash'],max(0,-self.b['debt']))
  self.post(day,'debt','cash',repay,'loan_repay')

def simulate(seed,policy,scenario='base',details=False,override=None):
 s=dict(SCENARIOS[scenario]);s.update(override or {})
 r=rng(seed,'project');z=r.gauss(0,1)
 demand=s.get('demand_factor',1)*math.exp(0.20*z-0.02)
 rate=A['specialist_hourly_cost']*s.get('rate_factor',1)*math.exp(0.08*z)
 capacity=A['weekly_delivery_hours']/7*s.get('capacity_factor',1)
 common=r.random()<s.get('common_probability',A['common_mode_probability'])
 common_day=r.randint(65,140)
 price=policy['price'];arr=policy['arrangement'];pool=arr=='pooled'
 ledger=Ledger(details);events=[];seq=0;states=[];buyers=[];counts=Counter();h=Counter();core_paid=False
 def event(day,action,amount=0,kind='',bid='',extra=None):
  nonlocal seq
  if day>A['runoff_days']:raise RuntimeError('unrun obligation beyond horizon')
  seq+=1;heapq.heappush(events,(int(day),seq,action,float(amount),kind,bid,extra))
 def state(day,bid,status,**kw):
  counts[status]+=1
  if details:states.append(dict(day=int(day),buyer=bid,status=status,**kw))
 def expense(day,amount,kind,bid=''):event(day,'expense',amount,kind,bid)
 for k,v in A['startup_costs'].items():expense(0,v,'fixed_'+k)
 for d in range(30,A['acquisition_days']+1,30):expense(d,A['overhead_monthly'],'fixed_overhead')
 n=max(1,int(A['prospects']*demand));expense(1,n*A['prospect_acquisition_cost'],'acquisition')
 counts['prospects']=n;arrivals=[]
 for i in range(n):
  q=rng(seed,f'prospect:{i}');bid=f'B{i:04d}'
  day=q.randint(1,A['acquisition_days'])
  if q.random()>A['lead_rate']:continue
  state(day,bid,'inquiry');expense(day,A['qualification_hours']*rate,'qualification',bid);h['qualification']+=A['qualification_hours']
  if q.random()>A['qualified_rate']:
   state(day,bid,'unqualified',reason='scope, event-interface, authority or budget mismatch');continue
  state(day,bid,'qualified');expense(day,rate*A['quotation_hours'],'quotation',bid);h['quotation']+=A['quotation_hours']
  gross=A['gross_value_median']*q.lognormvariate(0,0.4);urgency=q.uniform(3,18)
  hrs=q.uniform(*A['internal_design_hours_range'])+q.uniform(*A['internal_review_hours_range'])
  outside_h=s.get('outside_hours_factor',1);competitor_factor=s.get('competitor_factor',1) if day>=s.get('competitor_response_day',0) else 1
  comp=q.uniform(*A['competitor_quote_range'])*competitor_factor
  review=A['buyer_review_hours']*A['specialist_hourly_cost']
  outside={
   'internal_ai':0.94*gross-hrs*outside_h*A['specialist_hourly_cost']-review-14*urgency,
   'free_tools':0.91*gross-(hrs+4)*outside_h*A['specialist_hourly_cost']-review-21*urgency,
   'competitor':0.96*gross-comp-review-7*urgency,
   'wait':0.72*gross-0.8*min(comp,hrs*outside_h*A['specialist_hourly_cost'])-review-30*urgency,
   'do_nothing':0.0}
  outside_choice=max(outside,key=outside.get);outside_u=outside[outside_choice]
  wait=18 if pool else 10
  trust=A['new_supplier_trust_cost']*s.get('trust_factor',1)
  rights_cost=q.uniform(20,160) if pool else 0
  setup_extra=4*A['specialist_hourly_cost'] if arr=='license' else 0
  max_price=.94*gross-review-wait*urgency-trust-rights_cost-setup_extra-outside_u
  requested=price*(1-q.uniform(.02,.10));offer=min(price,max(requested,max_price)) if max_price>=price*.92 else price
  offer=round(offer,2);state(day,bid,'quotation',posted_price=price,reservation_price=round(max_price,2),outside_choice=outside_choice,outside_utility=round(outside_u,2))
  if max_price<offer:
   state(day,bid,'lost',reason=outside_choice);continue
  hours=(4.0 if pool else 8.0 if arr=='bespoke' else 3.0)*s.get('ours_hours_factor',1)
  predicted_cost=hours*rate+A['inference_per_order']+A['compute_tools_per_order']+2.0*rate
  if offer<predicted_cost*1.05:
   state(day,bid,'seller_refusal',reason='price below expected incremental obligation');continue
  state(day,bid,'negotiation',price=offer);h['procurement']+=.7;expense(day,.7*rate+35,'contracting',bid)
  if q.random()<.12:
   state(day+7,bid,'procurement_refusal');continue
  contract_day=day+q.randint(3,14)
  if contract_day>A['acquisition_days']:
   state(contract_day,bid,'intake_closed');continue
  b={'id':bid,'day':contract_day,'price':offer,'q':q,'hours':hours,'gross_value':gross,'outside_choice':outside_choice,'outside_u':outside_u,'buyer_ex_ante_gain':max_price-offer,'rate':rate,'wait':wait}
  state(contract_day,bid,'contract',price=offer,contingent_pool=pool)
  event(contract_day,'deposit',offer*A['deposit_fraction'],'deposit',bid)
  arrivals.append(b);buyers.append({k:v for k,v in b.items() if k!='q'})
 arrivals.sort(key=lambda b:(b['day'],b['id']))
 groups=[]
 if pool:
  pending=[]
  for b in arrivals:
   for old in list(pending):
    if b['day']-old['day']>A['pool_formation_days']:
     day=old['day']+A['pool_formation_days'];event(day,'deposit_refund',old['price']*A['deposit_fraction'],'pool_refund',old['id']);state(day,old['id'],'pool_expired');pending.remove(old)
   pending.append(b);expense(b['day'],.55*rate,'coordination',b['id']);h['coordination']+=.55
   if len(pending)==A['pool_size']:groups.append((b['day'],pending));pending=[]
  for b in pending:
   day=b['day']+A['pool_formation_days'];event(day,'deposit_refund',b['price']*A['deposit_fraction'],'pool_refund',b['id']);state(day,b['id'],'pool_expired')
 else:groups=[(b['day'],[b]) for b in arrivals]
 available=1.;max_wait=0;benefits=[];delivery_hours=0;interventions=0;renewals=0
 for ready,group in groups:
  batch_hours=(3.0 if pool else 0)*s.get('ours_hours_factor',1)
  expected_finish=max(available,ready)+(sum(b['hours'] for b in group)+batch_hours)/capacity
  if expected_finish-ready>A['max_delivery_wait_days']:
   for b in group:
    event(ready,'deposit_refund',b['price']*A['deposit_fraction'],'capacity_refund',b['id']);state(ready,b['id'],'capacity_refusal')
   continue
  start=max(available,ready)
  if batch_hours:expense(start,batch_hours*rate+30,'shared_batch_validation');h['batch_validation']+=batch_hours;delivery_hours+=batch_hours
  for b in group:
   q=b['q'];bid=b['id'];p=b['price'];hours=b['hours'];begin=max(available,start);finish=math.ceil(begin+hours/capacity);available=finish
   max_wait=max(max_wait,finish-b['day']);delivery_hours+=hours;h['delivery']+=hours
   state(begin,bid,'execution',hours=hours);expense(begin,hours*rate,'delivery',bid)
   expense(begin,A['inference_per_order']*s.get('inference_factor',1),'inference',bid);expense(begin,A['compute_tools_per_order'],'compute_tools',bid)
   first=q.random()<max(.5,A['first_pass_acceptance']-(.12 if common and finish>=common_day else 0))
   accepted=first
   if not first:
    state(finish,bid,'initial_refusal');correction_hours=q.uniform(1,3);delivery_hours+=correction_hours;h['correction']+=correction_hours;interventions+=1;expense(finish,correction_hours*rate+15,'correction',bid)
    available+=correction_hours/capacity;finish=math.ceil(available);accepted=q.random()<A['correction_success'];state(finish,bid,'correction',accepted=accepted)
   if not accepted:
    event(finish,'deposit_refund',p*A['deposit_fraction'],'delivery_refund',bid);state(finish,bid,'final_refusal');continue
   state(finish,bid,'acceptance',unchanged_contract=True);event(finish,'acceptance',p,'acceptance',bid)
   benefits.append(b['buyer_ex_ante_gain']);interventions+=1
   support_h=q.uniform(.5,1.5);h['support']+=support_h;delivery_hours+=support_h;expense(finish+20,support_h*rate,'support',bid);state(finish+20,bid,'support')
   defect=(q.random()<(.35 if common else .045));refund=0
   if defect:
    repair=q.uniform(1.5,4.5);h['warranty']+=repair;delivery_hours+=repair;interventions+=1;expense(finish+30,repair*rate,'warranty_repair',bid)
    if common and not core_paid:expense(finish+25,6*rate+120,'common_mode_repair');h['common_repair']+=6;delivery_hours+=6;core_paid=True
    refund=p*(.5 if q.random()<.65 else 1.0);event(finish+35,'warranty_refund',refund,'warranty_refund',bid);state(finish+35,bid,'warranty_refund',amount=refund)
   lag=int(q.uniform(0,70)*s.get('payment_lag_factor',1));payday=finish+A['payment_terms_days']+lag
   default=q.random()<min(.6,A['commercial_default']+s.get('default_add',0)+(.04 if common else 0)) or s.get('strategic_default',False)
   event(payday,'default' if default else 'collection',0,'bad_debt' if default else 'collection',bid)
   state(payday,bid,'default' if default else 'collection')
   state(finish+A['warranty_days'],bid,'warranty_closed')
   renew=q.random()<A['renewal_probability'] and not defect and not default
   renew_cost=1.6*rate+20
   if renew and A['renewal_fee']>renew_cost*1.1:
    rd=finish+180;state(rd,bid,'renewal_quotation',price=A['renewal_fee']);expense(rd,.25*rate,'renewal_sales',bid);h['renewal_sales']+=.25
    if q.random()<.65:
     state(rd+7,bid,'renewal_acceptance');expense(rd+7,renew_cost,'renewal_delivery',bid);h['renewal_delivery']+=1.6;delivery_hours+=1.6
     event(rd+7,'renewal_invoice',A['renewal_fee'],'renewal_invoice',bid+'R');event(rd+67,'collection',0,'renewal_collection',bid+'R');state(rd+67,bid,'renewal_collection');renewals+=1
   else:state(finish+180,bid,'exit_or_no_renewal')
 ledger.post(0,'cash','equity',money(A['equity']),'equity')
 receivable=defaultdict(int);deposit=defaultdict(int);last=0
 while events:
  day,_,action,amount,kind,bid,extra=heapq.heappop(events)
  if day>last:
   interest=round(max(0,-ledger.b['debt'])*A['annual_interest_rate']*(day-last)/365)
   if interest:ledger.expense(day,interest/100,'financing');ledger.interest+=interest
   last=day
  c=money(amount)
  if action=='expense':ledger.expense(day,amount,kind,bid)
  elif action=='deposit':deposit[bid]+=c;ledger.post(day,'restricted_cash','deposit_liability',c,kind,bid)
  elif action=='deposit_refund':
   v=deposit.pop(bid,0);ledger.post(day,'deposit_liability','restricted_cash',v,kind,bid)
  elif action=='acceptance':
   receivable[bid]+=c;ledger.post(day,'receivable','revenue',c,kind,bid)
   v=deposit.pop(bid,0);receivable[bid]-=v;ledger.post(day,'deposit_liability','receivable',v,'deposit_applied',bid);ledger.post(day,'cash','restricted_cash',v,'deposit_released',bid)
  elif action=='warranty_refund':
   credited=min(c,receivable[bid]);receivable[bid]-=credited;ledger.post(day,'contra_revenue','receivable',credited,'warranty_credit',bid)
   cash_refund=c-credited;ledger.fund(day,cash_refund);ledger.post(day,'contra_revenue','cash',cash_refund,'warranty_cash_refund',bid)
  elif action=='renewal_invoice':receivable[bid]+=c;ledger.post(day,'receivable','revenue',c,kind,bid)
  elif action=='collection':
   v=receivable.pop(bid,0);ledger.post(day,'cash','receivable',v,kind,bid)
  elif action=='default':
   v=receivable.pop(bid,0);ledger.post(day,'expense:bad_debt','receivable',v,kind,bid)
  else:raise ValueError(action)
 ledger.settle(last)
 b=ledger.b;net_rev=-b['revenue']-b['contra_revenue'];expenses=sum(v for k,v in b.items() if k.startswith('expense:'))
 fixed=sum(v for k,v in b.items() if k.startswith('expense:fixed_'));profit=net_rev-expenses;operating=profit+fixed+b['expense:financing']
 if abs(sum(b.values())) or b['receivable'] or b['restricted_cash'] or b['deposit_liability']:raise AssertionError('unclosed ledger')
 if b['cash']-b['debt']-money(A['equity'])-ledger.rescue != profit:raise AssertionError('cash-profit-equity bridge')
 accepted=counts['acceptance'];result={'seed':seed,'scenario':scenario,'arrangement':arr,'posted_price':price,'net_revenue':net_rev/100,'expenses':expenses/100,'operating_contribution':operating/100,'fixed_cost':fixed/100,'financing_cost':b['expense:financing']/100,'full_profit':profit/100,'roi_on_cost':profit/expenses if expenses else 0,'required_capital':ledger.capital/100,'peak_restricted_cash':ledger.peak_restricted/100,'peak_debt':ledger.peak_debt/100,'funding_shortfall':ledger.rescue/100,'final_cash':b['cash']/100,'final_debt':-b['debt']/100,'final_day':last,'accepted':accepted,'contracts':counts['contract'],'quotes':counts['quotation'],'inquiries':counts['inquiry'],'qualified':counts['qualified'],'pool_expired':counts['pool_expired'],'initial_refusals':counts['initial_refusal'],'final_refusals':counts['final_refusal'],'defaults':counts['default'],'warranty_refunds':counts['warranty_refund'],'renewals':renewals,'human_hours':sum(h.values()),'delivery_human_hours':delivery_hours,'interventions':interventions,'interventions_per_accepted':interventions/accepted if accepted else None,'max_wait_days':max_wait,'mean_buyer_ex_ante_benefit':statistics.mean(benefits) if benefits else None,'common_mode':common,'successor_investment':0,'stop_decision':'No expansion: fresh profitable demand and interface-qualified delivery required'}
 if details:result.update(journal=ledger.rows,accounts=dict(b),lifecycle=sorted(states,key=lambda x:(x['day'],x['buyer'])),buyers=buyers,human_hours_by_task=dict(h),state_counts=dict(counts))
 return result

def summarize(rows):
 out={'runs':len(rows)}
 for k in ['net_revenue','expenses','operating_contribution','fixed_cost','financing_cost','full_profit','roi_on_cost','required_capital','peak_restricted_cash','peak_debt','funding_shortfall','accepted','contracts','quotes','inquiries','qualified','pool_expired','initial_refusals','final_refusals','defaults','warranty_refunds','renewals','human_hours','delivery_human_hours','interventions','max_wait_days']:
  vals=sorted(x[k] for x in rows);n=len(vals);m=statistics.mean(vals)
  out[k]={'mean':m,'p05':vals[int(.05*(n-1))],'p50':vals[int(.5*(n-1))],'p95':vals[int(.95*(n-1))],'se_mean':statistics.stdev(vals)/math.sqrt(n) if n>1 else 0}
 for name,key in [('loss','full_profit'),('cash_shortfall','funding_shortfall')]:
  p=sum((r[key]<0 if name=='loss' else r[key]>0) for r in rows)/len(rows);n=len(rows);z=1.96;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
  out[name+'_probability']={'estimate':p,'wilson95':[max(0,mid-half),min(1,mid+half)],'interpretation':'Conditional Monte Carlo sampling interval; excludes model misspecification'}
 losses=sorted(r['full_profit'] for r in rows);out['worst_five_percent_mean_profit']=statistics.mean(losses[:max(1,len(losses)//20)])
 benefits=[r['mean_buyer_ex_ante_benefit'] for r in rows if r['mean_buyer_ex_ante_benefit'] is not None];out['buyer_benefit_conditional_on_participation']=statistics.mean(benefits) if benefits else None
 out['human_interventions_per_accepted']=sum(r['interventions'] for r in rows)/max(1,sum(r['accepted'] for r in rows))
 return out

def develop(n=96):
 candidates=[{'arrangement':a,'price':p} for a in ['bespoke','pooled','license'] for p in [1200,1800,2400,3000,3600]]
 results=[]
 for policy in candidates:
  rows=[simulate(10000+i,policy) for i in range(n)];sm=summarize(rows);results.append(dict(policy=policy,summary=sm))
 best=max(results,key=lambda x:x['summary']['full_profit']['mean']);out={'scope':'Bounded development; no-launch has incremental economic value zero and is always an admissible outside action','candidate_count':len(candidates),'seeds':{'start':10000,'n':n},'candidates':results,'selected_for_research_confirmation':best['policy'],'launch_selection':'No launch if no policy beats zero full-project profit; continue simulated campaign to answer the research mandate'}
 (ROOT/'results/business_development.json').write_text(json.dumps(out,indent=2)+'\n')
 policy=dict(best['policy'],protocol_version='commercial-v1',selection='Highest development mean full-project profit; not authorization to launch',development_hash=hashlib.sha256(json.dumps(out,sort_keys=True).encode()).hexdigest(),acceptance='technical_v1 unchanged; buyer scope/fit acceptance modeled separately',exit_day=A['acquisition_days'],reinvest_rule='Only realized unencumbered profit after all obligations and fixed cost recovery; no modeled investment when negative',no_launch_alternative=0)
 (ROOT/'protocol/commercial_policy.json').write_text(json.dumps(policy,indent=2)+'\n');return out

def confirm(n=1024):
 policy=json.loads((ROOT/'protocol/commercial_policy.json').read_text());all_rows=[];summaries={}
 for s in SCENARIOS:
  rows=[simulate(700001+i,policy,s) for i in range(n)];summaries[s]=summarize(rows);all_rows+=rows
 with (ROOT/'results/business_confirmation.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)
 report={'policy':policy,'runs_per_scenario':n,'seed_start':700001,'scenarios':SCENARIOS,'summaries':summaries,'scenario_probabilities':'Not assigned; scenarios are conditional stress tests, not an unconditional forecast','precision':'SE and intervals measure sampling only; demand/value/behavior assumptions dominate external uncertainty'}
 (ROOT/'results/business_confirmation.json').write_text(json.dumps(report,indent=2)+'\n')
 base=[r for r in all_rows if r['scenario']=='base'];median=sorted(base,key=lambda x:x['full_profit'])[len(base)//2]
 interesting=max(base,key=lambda x:(x['accepted']>=2 and x['warranty_refunds']>0 and x['defaults']>0,x['accepted']))
 for name,row in [('median',median),('lifecycle',interesting)]:
  d=simulate(row['seed'],policy,'base',True);(ROOT/f'results/business_{name}_ledger.json').write_text(json.dumps(d,indent=2)+'\n')
 return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['develop','confirm','demo']);ap.add_argument('--runs',type=int);args=ap.parse_args();t=time.perf_counter()
 if args.mode=='develop':out=develop(args.runs or 96);print(json.dumps({'selected':out['selected_for_research_confirmation'],'best_mean_profit':max(x['summary']['full_profit']['mean'] for x in out['candidates'])}))
 elif args.mode=='confirm':out=confirm(args.runs or 1024);print(json.dumps({k:{'profit':v['full_profit']['mean'],'accepted':v['accepted']['mean'],'loss_probability':v['loss_probability']['estimate']} for k,v in out['summaries'].items()}))
 else:print(json.dumps(simulate(700001,json.loads((ROOT/'protocol/commercial_policy.json').read_text()),details=True),indent=2))
 print('runtime_seconds',round(time.perf_counter()-t,3))
