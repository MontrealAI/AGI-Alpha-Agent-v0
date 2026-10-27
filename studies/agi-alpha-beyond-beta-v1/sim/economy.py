# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, copy, csv, gzip, hashlib, json, math, pathlib, sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np
from graph_admission import make_simulated_record, inspect as inspect_graph

HERE=pathlib.Path(__file__).resolve().parent
POLICIES=('optimized_no_assets','optimized_optional','fixed_optional')

def json_scalar(x):
    if isinstance(x,np.generic):return x.item()
    raise TypeError(f'Unsupported JSON value: {type(x).__name__}')
def dumps(x,**kwargs):return json.dumps(x,default=json_scalar,**kwargs)
def canonical(x):return dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(canonical(x)).hexdigest()
def rng(seed,*keys):return np.random.default_rng(np.random.SeedSequence([seed,*keys]))
def clip(x,a=0.,b=1.):return max(a,min(b,x))
def stats(values):
    a=np.asarray(values,float)
    return {'mean':float(a.mean()),'median':float(np.median(a)),'p05':float(np.quantile(a,.05)),'p95':float(np.quantile(a,.95)),'min':float(a.min()),'max':float(a.max())}
def write_csv(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with open(path,'w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)

def unit(cu,register):
    t=register['tariffs']
    cost=sum(cu[f'{m}_{k}']*t[f'{m}_{k}_per_million']/1e6 for m in ('astra','terra') for k in ('input','output'))+cu['container_sessions_16gb']*t['container_16gb_20minute_usd']+cu['tools_usd']+cu['other_usd']
    return {'usd':cost,'tokens':sum(cu[f'{m}_{k}'] for m in ('astra','terra') for k in ('input','output')),'minutes':cu['resource_minutes'],'container_minutes':cu['container_sessions_16gb']*20}

def cost_table(register):
    out={s['id']:unit(s,register) for s in register['stages']}
    for name in ['correction','revalidation','recovery','asset_construction_unit','asset_evaluation_unit','asset_integration_unit','asset_revalidation_unit','asset_maintenance_month','recipient_acquisition']:out[name]=unit(register[name],register)
    return out

def resource_sum(items):
    items=list(items)
    return {k:sum(i[k] for i in items) for k in ('usd','tokens','minutes','container_minutes')}
def scaled(x,v):return {k:a*v for k,a in x.items()}

def buyer_probabilities(c,fractions,values=None,trusts=None,queue_days=0.,incident_penalty=0.):
    m=c['market'];vals=np.asarray(values if values is not None else [v for v in m['value_grid'] for _ in m['trust_grid']],float);trs=np.asarray(trusts if trusts is not None else [t for _ in m['value_grid'] for t in m['trust_grid']],float)
    f=np.asarray(fractions,float)[None,:]
    own=vals[:,None]*m['our_quality_belief']-f-m['our_review_fraction']-m['integration_fraction']-trs[:,None]-incident_penalty-(m['base_delivery_days']+queue_days)*m['delay_cost_fraction_per_day']
    human=vals[:,None]*m['human_quality_belief']-1-m['human_review_fraction']-m['human_delivery_days']*m['delay_cost_fraction_per_day']
    utility=np.stack((own,np.broadcast_to(human,own.shape),np.full_like(own,m['postpone_utility_fraction']),np.zeros_like(own)),axis=-1)/m['taste_scale_fraction']
    utility-=utility.max(axis=-1,keepdims=True);e=np.exp(utility);return e[...,0]/e.sum(axis=-1)

@dataclass
class Belief:
    weights: np.ndarray
    arrival_shape: float
    arrival_rate: float
    queue_days:float=0.
    incident_penalty:float=0.
    prices: list=field(default_factory=list)
    outcomes: list=field(default_factory=list)
    def update(self,c,fraction,offered,purchased,incoming):
        self.arrival_shape+=incoming;self.arrival_rate+=1
        if offered:
            p=buyer_probabilities(c,[fraction],queue_days=self.queue_days,incident_penalty=self.incident_penalty)[:,0];log=np.log(np.maximum(self.weights,1e-300))+purchased*np.log(np.maximum(p,1e-12))+(offered-purchased)*np.log(np.maximum(1-p,1e-12));log-=log.max();self.weights=np.exp(log);self.weights/=self.weights.sum()
        self.prices.append(fraction);self.outcomes.append((offered,purchased))

@dataclass
class Asset:
    name:str
    ready:int
    good:bool
    estimated_correctness:float
    estimated_transfer:float
    transfer:np.ndarray
    graph:dict
    active:bool=True
    uses:int=0
    acquisition_done:set=field(default_factory=set)

@dataclass
class Campaign:
    action:str
    starts:int
    components:list
    remaining_minutes:float
    remaining_tokens:float
    total_minutes:float
    total_tokens:float
    bill:float
    seed_funded:float
    operating_funded:float
    expected_gain:float
    consumed_minutes:float=0.
    consumed_tokens:float=0.

@dataclass
class Result:
    world:int
    scenario:str
    policy:str
    metrics:dict
    ledger:list
    events:list
    graph_records:dict
    belief:dict


def initial_primitives(c,sc,seed,world):
    r=rng(seed,world,999);n=c['scope']['recipient_agents'];d=c['scope']['domains'];equivalent={};partial={}
    for a in ('R','V'):
        draws=r.random((n,d));equivalent[a]=draws<c['scope'][f'existing_equivalent_{a}'];partial[a]=(draws>=c['scope'][f'existing_equivalent_{a}'])&(draws<c['scope'][f'existing_equivalent_{a}']+c['scope']['partial_equivalent_probability'])
    multiplier=math.exp(r.normal(-sc['world_arrival_log_sigma']**2/2,sc['world_arrival_log_sigma']));months=[]
    for month in range(1,c['months']+1):
        r=rng(seed,world,month,10);n=int(r.poisson(sc['arrivals_month']*(1+sc['arrival_growth'])**(month-1)*multiplier));u=r.random((n,40));values=np.exp(r.normal(math.log(sc['buyer_value_multiplier'])-c['market']['value_log_sigma']**2/2,c['market']['value_log_sigma'],n));taste=r.gumbel(size=(n,4));burst=r.random()<c['operations']['monthly_common_burst_probability'];months.append((u,values,taste,burst))
    return equivalent,partial,months,multiplier


def expected_delivery(c,sc,table,coverage_R=0.,coverage_V=0.):
    stages=resource_sum(table[s['id']] for s in c['_stages'])
    for label,coverage in [('R',coverage_R),('V',coverage_V)]:
        removable=resource_sum(table[s['id']] for s in c['_stages'] if s['potentially_reusable_by']==label)
        for k in stages:stages[k]-=removable[k]*coverage
    stages=scaled(stages,sc['activity_quantity_multiplier'])
    richmix=c['scope']['base_share']+(1-c['scope']['base_share'])*c['scope']['rich_activity_multiplier']
    stages=scaled(stages,richmix)
    component=sc['reconstruction_correctness']+(sc['retained_component_correctness']-sc['reconstruction_correctness'])*coverage_R
    good=sc['semantic_correctness']*component*(1-sc['shared_fault_probability']);bad=1-good;truepasses=falsepasses=corrections=0.
    sensitivity=.5*(sc['semantic_validator_sensitivity']+sc['mechanical_validator_sensitivity']);checker=sc['reconstruction_correctness']+(sc['retained_component_correctness']-sc['reconstruction_correctness'])*coverage_V;ordinary_miss=(1-checker)*.5+checker*(1-sensitivity);miss=ordinary_miss*(1-sc['shared_fault_probability'])+sc['shared_fault_miss']*sc['shared_fault_probability']
    for attempt in range(c['operations']['max_corrections']+1):
        truepasses+=good*sc['validator_specificity'];falsepasses+=bad*miss
        rg=good*(1-sc['validator_specificity']);rb=bad*(1-miss)
        if attempt==c['operations']['max_corrections']:break
        corrections+=rg+rb;good=rg*.95+rb*sc['correction_success'];bad=rg*.05+rb*(1-sc['correction_success'])
    correction=scaled(resource_sum([table['correction'],table['revalidation']]),corrections*sc['activity_quantity_multiplier']*richmix)
    for k in stages:stages[k]+=correction[k]
    stages['true_pass']=truepasses;stages['false_pass']=falsepasses
    return stages


def coverage(c,assets,month,belief=False):
    out={}
    for name in ('R','V'):
        existing=c['scope'][f'existing_equivalent_{name}']+c['scope']['partial_equivalent_probability']*c['scope']['partial_reconstruction_saving']
        if name in assets and assets[name].active and month>=assets[name].ready:
            a=assets[name];fraction=a.estimated_transfer*len(c['assets'][name]['domains'])/(c['scope']['domains']-1);existing+=(1-existing)*fraction
        out[name]=clip(existing)
    return out


def price_plan(c,sc,table,belief,assets,month,policy,mask=0):
    cov=coverage(c,assets,month)
    for name in ('R','V'):
        if mask&c['assets'][name]['bit']:
            prior=cov[name];cov[name]=prior+(1-prior)*sc['transfer_success']*sc['asset_build_success']
    delivery=expected_delivery(c,sc,table,cov['R'],cov['V']);fractions=[c['fixed_price_ablation']] if policy=='fixed_optional' else c['price_fractions'];prob=belief.weights@buyer_probabilities(c,fractions,queue_days=belief.queue_days,incident_penalty=belief.incident_penalty)
    arrivals=belief.arrival_shape/belief.arrival_rate*c['scope']['supported_domain_fraction']
    maxcapacity=min(c['operations']['monthly_workbench_minutes']/max(1,delivery['minutes']),c['operations']['monthly_token_quota']/max(1,delivery['tokens']))
    started=np.minimum(arrivals*prob,maxcapacity)
    ref=sc['human_reference']*(c['scope']['base_share']+(1-c['scope']['base_share'])*c['scope']['rich_human_reference_multiplier'])
    collect=delivery['true_pass']*sc['collection_probability']*(1-c['operations']['payment_fraction'])
    margins=np.asarray(fractions)*ref*collect-delivery['usd']-c['operations']['storage_per_delivery']-c['operations']['payment_fixed']*(delivery['true_pass']+delivery['false_pass'])*sc['collection_probability']-delivery['false_pass']*c['operations']['postdelivery_discovery']*table['recovery']['usd']*sc['activity_quantity_multiplier']
    qualification=(belief.arrival_shape/belief.arrival_rate)*c['operations']['qualification_units_per_opportunity']*table['intake_clarification']['usd']*sc['activity_quantity_multiplier'];value=started*margins-c['operations']['monthly_control_cost']-c['operations']['monthly_business_automation_cost']-qualification
    k=int(np.argmax(value));return {'fraction':float(fractions[k]),'expected_monthly_net':float(value[k]),'expected_started':float(started[k]),'expected_adoption':float(prob[k]),'delivery':delivery,'coverage':cov,'curve':[{'fraction':float(f),'expected_monthly_net':float(v),'expected_started_projects':float(n),'expected_adoption':float(p)} for f,v,n,p in zip(fractions,value,started,prob)]}


def choose_campaign(c,sc,table,register,belief,assets,campaign,attempted,month,cash,reserve,policy):
    base=price_plan(c,sc,table,belief,assets,month,policy)
    if policy=='optimized_no_assets' or campaign:return None,base
    actions=[]
    missing=[n for n in ('R','V') if n not in attempted]
    if 'R' in missing:actions.append(('R',1,['R']))
    if 'V' in missing:actions.append(('V',2,['V']))
    if len(missing)==2:actions.append(('bundle',3,['R','V']))
    best=None
    for action,mask,components in actions:
        source=register['investment_campaigns'][action];quantity=sc['activity_quantity_multiplier'];bill=source['derived_budget_usd']*quantity
        devminutes=c['operations']['monthly_workbench_minutes']*c['operations']['research_fraction_limit'];devtokens=c['operations']['monthly_token_quota']*c['operations']['research_fraction_limit']
        duration=1+math.ceil(max(source['resource_minutes']*quantity/devminutes,sum(source[f'{m}_{k}'] for m in ('astra','terra') for k in ('input','output'))*quantity/devtokens))
        horizon=min(c['policy']['forecast_months'],c['months']-month-duration,min(c['assets'][n]['lifetime_months'] for n in components))
        protected_seed=0. if c['policy']['allow_seed_funded_research'] else c['seed_cash']
        if horizon<=0 or cash-reserve-protected_seed-c['policy']['minimum_research_cash_headroom']<bill:continue
        after=price_plan(c,sc,table,belief,assets,month,policy,mask)
        survival=sum((1-max(c['assets'][n]['obsolescence_probability'] for n in components))**a/(1+c['policy']['financial_monthly_discount_rate'])**(a+duration) for a in range(horizon))
        monthly_maintenance=len(components)*table['asset_maintenance_month']['usd']*quantity
        revalidation=len(components)*(horizon//3)*table['asset_revalidation_unit']['usd']*quantity
        incremental=(after['expected_monthly_net']-base['expected_monthly_net']-monthly_maintenance)*survival-bill-revalidation
        occupied_fraction=min(1,source['resource_minutes']*quantity/max(1,duration*c['operations']['monthly_workbench_minutes']))
        foregone=max(0,base['expected_started']-c['operations']['monthly_workbench_minutes']*(1-occupied_fraction)/max(1,base['delivery']['minutes']))
        opportunity=foregone*duration*max(0,base['expected_monthly_net']/max(1,base['expected_started']))
        incremental-=opportunity
        if incremental<=bill*c['policy']['value_hurdle_fraction']:continue
        reserve_test=cash-bill-reserve>=c['policy']['minimum_research_cash_headroom']
        if not reserve_test:continue
        proposal={'deterministic_reserve_test_passed':reserve_test,'action':action,'components':components,'bill':bill,'expected_incremental_terminal_cash':incremental,'estimated_build_months':duration,'forecast_horizon':horizon,'opportunity_cost_forecast':opportunity,'cash_after_purchase':cash-bill,'reserve':reserve,'price_before':base['fraction'],'price_after':after['fraction']}
        if best is None or incremental>best['expected_incremental_terminal_cash']:best=proposal
    return best,base

def simulate(c,register,scenario,world,policy,seed,shared=None,structural_off=False):
    c=copy.deepcopy(c);c['_stages']=register['stages'];sc=c['scenarios'][scenario];o=c['operations'];market=c['market'];table=cost_table(register)
    equiv,partial,months,demand=shared or initial_primitives(c,sc,seed,world);equiv={k:v.copy() for k,v in equiv.items()};partial={k:v.copy() for k,v in partial.items()};experience=np.zeros((c['scope']['recipient_agents'],c['scope']['domains']))
    discovery=resource_sum(scaled(table[k],n) for k,n in c['discovery_budget_counts'].items());setup_months=math.ceil(max(discovery['minutes']/o['monthly_workbench_minutes'],discovery['tokens']/o['monthly_token_quota']))
    fixed=o['monthly_control_cost']+o['monthly_business_automation_cost'];cash=c['seed_cash']-discovery['usd']-setup_months*fixed;assert cash>=0
    totals={k:0. for k in ['collections','payment_fees','qualified_opportunities','qualification_cost','unsupported_intake_cost','orders','human_choices','retain_choices','decline_choices','attempted_projects','true_accepted_projects','false_passes','validated_deliveries','failed_projects','abstentions','expired_orders','correction_rounds','production_cost','correction_cost','recovery_cost','storage_cost','fixed_cost','refunds','investment_cost','maintenance_cost','revalidation_cost','recipient_acquisition_cost','research_seed_funded','research_operating_funded','delivery_tokens','delivery_workbench_minutes','delivery_container_minutes','research_tokens','research_workbench_minutes','research_container_minutes','cash_blocked','capacity_blocked','observed_incidents','undetected_paid_false_pass_revenue','R_uses','V_uses','existing_equivalent_uses','graph_rejections','research_campaigns','research_admissions','price_boundary_months']}
    totals['discovery_cost']=discovery['usd'];totals['setup_fixed_cost']=setup_months*fixed
    belief=Belief(np.asarray(market['prior_weights'],float)/sum(market['prior_weights']),market['arrival_prior_shape'],market['arrival_prior_rate']);assets={};catalog={};attempted=set();campaign=None;events=[];ledgers=[];invoices={};refunds={};incident_notices={};queue=[];recovery_backlog=[];stopped=False;unpaid_fixed=0.;unpaid_refund=0.;transfer_trials=0;transfer_successes=0;price_history=[];last_delivered=[]
    for month in range(1,c['months']+c['runoff_months']+1):
        row={'month':month,'calendar_month_since_discovery_start':month+setup_months,'opening_cash':cash,'collections':0.,'operating_outflow':0.,'investment_outflow':0.,'refund_outflow':0.,'arrears_outflow':0.,'incoming_opportunities':0,'offered_projects':0,'orders':0,'attempted_projects':0,'true_accepted_projects':0,'false_passes':0,'validated_deliveries':0,'price_fraction':None,'price_reference_base':sc['human_reference'],'research_action':'retain','research_progress_fraction':None,'active_assets':'','price_curve':[],'belief_weights_before':belief.weights.tolist(),'observed_incidents':0}
        payments=invoices.pop(month,[])
        for amount in payments:
            fee=amount*o['payment_fraction']+o['payment_fixed'];cash+=amount-fee;row['collections']+=amount;row['operating_outflow']+=fee;totals['collections']+=amount;totals['payment_fees']+=fee
        discovered=incident_notices.pop(month,0);totals['observed_incidents']+=discovered;row['observed_incidents']=discovered
        unpaid_refund+=sum(refunds.pop(month,[]));p=min(cash,unpaid_refund);cash-=p;unpaid_refund-=p;row['refund_outflow']+=p;totals['refunds']+=p
        p=min(cash,unpaid_fixed);cash-=p;unpaid_fixed-=p;row['arrears_outflow']+=p;totals.setdefault('arrears_paid',0.);totals['arrears_paid']+=p
        if unpaid_fixed+unpaid_refund>1e-8:stopped=True
        def spend(amount,key,investment=False):
            nonlocal cash
            if amount>cash+1e-9:return False
            cash-=amount;totals[key]+=amount;row['investment_outflow' if investment else 'operating_outflow']+=amount;return True
        active_month=month<=c['months'] and not stopped
        if active_month:
            if not spend(fixed,'fixed_cost'):unpaid_fixed+=fixed;stopped=True;active_month=False
        elif month>c['months'] and (payments or row['refund_outflow'] or recovery_backlog):
            if not spend(o['monthly_control_cost'],'fixed_cost'):unpaid_fixed+=o['monthly_control_cost'];stopped=True
        known_refunds=sum(sum(x) for x in refunds.values());reserve=o['reserve_months']*fixed+known_refunds+o['warranty_reserve_fraction']*sum(last_delivered[-3:])+sum(p['usd'] for p in recovery_backlog)
        row['reserve']=reserve
        resource_keys=['delivery_tokens','delivery_workbench_minutes','delivery_container_minutes','research_tokens','research_workbench_minutes','research_container_minutes']
        resources_before={k:totals[k] for k in resource_keys}
        burst=months[month-1][3] if active_month else False;factor=o['burst_capacity_multiplier'] if burst else 1.
        minutes=o['monthly_workbench_minutes']*factor;tokens=o['monthly_token_quota']*factor;container_minutes=4*o['monthly_workbench_minutes']*factor
        row['capacity_tokens']=tokens;row['capacity_workbench_minutes']=minutes;row['capacity_container_minutes']=container_minutes
        def execute(plan,key,investment_resource=False):
            nonlocal minutes,tokens,container_minutes
            if plan['minutes']>minutes+1e-9 or plan['tokens']>tokens+1e-9 or plan['container_minutes']>container_minutes+1e-9:return False
            if not investment_resource and not spend(plan['usd'],key):return False
            minutes-=plan['minutes'];tokens-=plan['tokens'];container_minutes-=plan['container_minutes'];prefix='research' if investment_resource else 'delivery';totals[prefix+'_tokens']+=plan['tokens'];totals[prefix+'_workbench_minutes']+=plan['minutes'];totals[prefix+'_container_minutes']+=plan['container_minutes'];return True
        remaining_recovery=[]
        for recovery_plan in recovery_backlog:
            if not execute(recovery_plan,'recovery_cost'):
                if cash<recovery_plan['usd']:
                    unpaid_fixed+=recovery_plan['usd'];stopped=True;active_month=False
                else:remaining_recovery.append(recovery_plan)
        recovery_backlog=remaining_recovery
        if active_month:
            u,values,taste,burst=months[month-1]
            public=rng(seed,world,month,30)
            for name in ('R','V'):
                available=(public.random(equiv[name].shape)<c['scope']['copying_probability_per_month'])&(~equiv[name]);available[:,5]=False
                for receiver,domain_copy in zip(*np.nonzero(available)):
                    acq=scaled(table['recipient_acquisition'],sc['activity_quantity_multiplier'])
                    if cash-acq['usd']>=reserve and execute(acq,'recipient_acquisition_cost'):equiv[name][receiver,domain_copy]=True
            for name,a in assets.items():
                if not a.active or month<a.ready:continue
                ac=c['assets'][name];r=rng(seed,world,month,100+ac['bit'])
                if month-a.ready>=ac['lifetime_months'] or r.random()<ac['obsolescence_probability']:
                    a.active=False;a.graph['revoked']=True;events.append({'kind':'retirement','asset':name,'month':month});continue
                maintenance=scaled(table['asset_maintenance_month'],sc['activity_quantity_multiplier'])
                if cash-maintenance['usd']<reserve or not execute(maintenance,'maintenance_cost'):
                    a.active=False;a.graph['revoked']=True;events.append({'kind':'maintenance_hold','asset':name,'month':month});continue
                if (month-a.ready)>0 and (month-a.ready)%3==0:
                    if not execute(scaled(table['asset_revalidation_unit'],sc['activity_quantity_multiplier']),'revalidation_cost'):
                        a.active=False;a.graph['revoked']=True;events.append({'kind':'revalidation_hold','asset':name,'month':month})
            reserved_research={'minutes':0.,'tokens':0.,'container_minutes':0.}
            if campaign:
                source=register['investment_campaigns'][campaign.action];ctotal=source['container_sessions_16gb']*20*sc['activity_quantity_multiplier'];frac=min(campaign.remaining_minutes/campaign.total_minutes,min(minutes,o['monthly_workbench_minutes']*o['research_fraction_limit'])/campaign.total_minutes,min(tokens,o['monthly_token_quota']*o['research_fraction_limit'])/campaign.total_tokens,container_minutes/ctotal)
                reserved_research={'minutes':campaign.total_minutes*frac,'tokens':campaign.total_tokens*frac,'container_minutes':ctotal*frac};minutes-=reserved_research['minutes'];tokens-=reserved_research['tokens'];container_minutes-=reserved_research['container_minutes']
            belief.queue_days=30*sum(q['estimated_minutes'] for q in queue)/max(1,o['monthly_workbench_minutes'])
            belief.incident_penalty=market['observed_incident_trust_coefficient']*totals['observed_incidents']/max(10,totals['validated_deliveries'])
            plan=price_plan(c,sc,table,belief,assets,month,policy);fraction=plan['fraction'];price_history.append(fraction);row['price_fraction']=fraction;row['price_curve']=plan['curve'];row['estimated_queue_days']=belief.queue_days
            if fraction in (min(c['price_fractions']),max(c['price_fractions'])):totals['price_boundary_months']+=1
            incoming=len(u);row['incoming_opportunities']=incoming;offered=0;purchased=0
            qualification=scaled(table['intake_clarification'],o['qualification_units_per_opportunity']*sc['activity_quantity_multiplier'])
            for j in range(incoming):
                if cash-qualification['usd']<reserve or not execute(qualification,'qualification_cost'):break
                totals['qualified_opportunities']+=1
                supported=u[j,0]<c['scope']['supported_domain_fraction'];domain=min(4,int(u[j,1]*5)) if supported else 5
                if not supported:
                    execute(scaled(table['intake_clarification'],sc['activity_quantity_multiplier']),'unsupported_intake_cost');continue
                rich=u[j,2]>c['scope']['base_share'];scope=c['scope']['rich_activity_multiplier'] if rich else 1.;human=sc['human_reference']*(c['scope']['rich_human_reference_multiplier'] if rich else 1.);price=fraction*human;value=values[j]*human
                own=value*market['our_quality_belief']-price-human*(market['our_review_fraction']+market['integration_fraction']+sc['buyer_trust_fraction']+belief.incident_penalty+(market['base_delivery_days']+belief.queue_days)*market['delay_cost_fraction_per_day'])
                incumbent=value*market['human_quality_belief']-human*(1+market['human_review_fraction']+market['human_delivery_days']*market['delay_cost_fraction_per_day'])
                utility=np.asarray([own,incumbent,human*market['postpone_utility_fraction'],0.])+human*market['taste_scale_fraction']*taste[j];choice=int(np.argmax(utility));offered+=1
                if choice==0:
                    purchased+=1;recipient=min(c['scope']['recipient_agents']-1,int(u[j,3]*c['scope']['recipient_agents']));queue.append({'origin':month,'project':f'{world}:{month}:{j}','u':u[j],'recipient':recipient,'domain':domain,'scope':scope,'human_reference':human,'price':price,'estimated_minutes':1660*scope*sc['activity_quantity_multiplier']})
                else:totals[('human_choices','retain_choices','decline_choices')[choice-1]]+=1
            totals['orders']+=purchased;row['orders']=purchased;row['offered_projects']=offered
            belief.update(c,fraction,offered,purchased,incoming)
            held=queue;queue=[];monthly_delivered_revenue=0.
            for project in held:
                if month-project['origin']>o['max_queue_age_months']:totals['expired_orders']+=1;continue
                v=project['u'];recipient=project['recipient'];domain=project['domain'];scope=project['scope'];activity=sc['activity_quantity_multiplier']*scope;savings={};qualities={};used=[]
                for name in ('R','V'):
                    saving=1. if equiv[name][recipient,domain] else c['scope']['partial_reconstruction_saving'] if partial[name][recipient,domain] else min(.20,experience[recipient,domain]*.02)
                    established=1. if equiv[name][recipient,domain] else c['scope']['partial_reconstruction_saving'] if partial[name][recipient,domain] else 0.
                    quality=sc['reconstruction_correctness']+(sc['retained_component_correctness']-sc['reconstruction_correctness'])*established
                    if equiv[name][recipient,domain]:totals['existing_equivalent_uses']+=1
                    a=assets.get(name)
                    if a and a.active and month>=a.ready and not structural_off and not equiv[name][recipient,domain]:
                        review=inspect_graph(a.graph,month,catalog,domain)
                        if not review['admitted']:totals['graph_rejections']+=1
                        elif recipient not in a.acquisition_done:
                            acq=scaled(table['recipient_acquisition'],sc['activity_quantity_multiplier'])
                            if cash-acq['usd']>=reserve+unpaid_fixed+unpaid_refund and execute(acq,'recipient_acquisition_cost'):
                                a.acquisition_done.add(recipient);transfer_trials+=1;transfer_successes+=int(a.transfer[recipient]);a.estimated_transfer=(2+sum(int(a.transfer[z]) for z in a.acquisition_done))/(4+len(a.acquisition_done))
                        if recipient in a.acquisition_done and a.transfer[recipient] and review['admitted']:
                            saving=1.;quality=sc['retained_component_correctness'] if a.good else .65;used.append(a)
                    savings[name]=saving;qualities[name]=quality
                first=resource_sum(scaled(table[s['id']],1-savings.get(s['potentially_reusable_by'],0.)) for s in register['stages']);first=scaled(first,activity)
                extra=scaled(resource_sum([table['correction'],table['revalidation']]),activity)
                worst_cash=first['usd']+o['max_corrections']*extra['usd']+table['recovery']['usd']*activity+o['storage_per_delivery']
                protected=o['reserve_months']*fixed+sum(sum(x) for x in refunds.values())+unpaid_fixed+unpaid_refund+o['warranty_reserve_fraction']*(sum(last_delivered[-2:])+monthly_delivered_revenue)+sum(p['usd'] for p in recovery_backlog)
                if cash-worst_cash<protected:totals['cash_blocked']+=1;queue.append(project);continue
                if not execute(first,'production_cost'):totals['capacity_blocked']+=1;queue.append(project);continue
                totals['attempted_projects']+=1;row['attempted_projects']+=1
                for a in used:a.uses+=1;totals[a.name+'_uses']+=1
                if v[4]<o['admission_abstention']:totals['abstentions']+=1;totals['failed_projects']+=1;continue
                common=v[5]<clip(sc['shared_fault_probability']+(o['burst_shared_error_increment'] if burst else 0))
                semantic=v[6]<clip(sc['semantic_correctness']-(o['burst_semantic_penalty'] if burst else 0)) and not common
                mechanical=v[7]<qualities['R'];checker=v[8]<qualities['V'];correct=semantic and mechanical;passed=False
                for revision in range(o['max_corrections']+1):
                    draw=v[9+revision*3]
                    if correct:passed=draw<sc['validator_specificity']
                    else:
                        miss=sc['shared_fault_miss'] if common else 1-sc['semantic_validator_sensitivity'] if not semantic else 1-sc['mechanical_validator_sensitivity']
                        if not checker:miss=max(miss,.50)
                        passed=draw<miss
                    if passed or revision==o['max_corrections']:break
                    if not execute(extra,'correction_cost'):break
                    totals['correction_rounds']+=1;repair=sc['correction_success']*(.30 if common else 1.)
                    if correct:correct=v[10+revision*3]<.95
                    else:correct=v[10+revision*3]<repair
                    if correct:semantic=mechanical=True;common=False
                if not passed:totals['failed_projects']+=1;continue
                totals['validated_deliveries']+=1;row['validated_deliveries']+=1;spend(o['storage_per_delivery'],'storage_cost')
                if v[24]<c['scope']['ordinary_case_specific_learning_probability']:experience[recipient,domain]=min(10,experience[recipient,domain]+1)
                if correct:totals['true_accepted_projects']+=1;row['true_accepted_projects']+=1
                else:totals['false_passes']+=1;row['false_passes']+=1
                price=project['price'];paid=v[22]<sc['collection_probability'];due=month+sc['collection_lag'];monthly_delivered_revenue+=price
                if paid:
                    if sc['collection_lag']==0:
                        fee=price*o['payment_fraction']+o['payment_fixed'];cash+=price-fee;row['collections']+=price;row['operating_outflow']+=fee;totals['collections']+=price;totals['payment_fees']+=fee
                    else:invoices.setdefault(due,[]).append(price)
                if not correct and v[23]<o['postdelivery_discovery']:
                    incident_notices[month+1]=incident_notices.get(month+1,0)+1
                    if paid:refunds.setdefault(due+1,[]).append(price)
                    recovery=scaled(table['recovery'],activity)
                    if not execute(recovery,'recovery_cost'):recovery_backlog.append(recovery)
                elif not correct and paid:totals['undetected_paid_false_pass_revenue']+=price
            last_delivered.append(monthly_delivered_revenue)
            known_refunds=sum(sum(x) for x in refunds.values());reserve=o['reserve_months']*fixed+known_refunds+o['warranty_reserve_fraction']*sum(last_delivered[-3:])+sum(p['usd'] for p in recovery_backlog);row['reserve']=reserve
            proposal,postprice=choose_campaign(c,sc,table,register,belief,assets,campaign,attempted,month,cash,reserve,policy)
            if proposal and not stopped:
                action=proposal['action'];source=register['investment_campaigns'][action];quantity=sc['activity_quantity_multiplier'];bill=proposal['bill'];available_operating=max(0,cash-c['seed_cash']-reserve-unpaid_fixed-unpaid_refund);operating_funded=min(bill,available_operating);seed_funded=bill-operating_funded
                if spend(bill,'investment_cost',True):
                    totals['research_campaigns']+=1;totals['research_operating_funded']+=operating_funded;totals['research_seed_funded']+=seed_funded;attempted.update(proposal['components']);total_tokens=sum(source[f'{m}_{k}'] for m in ('astra','terra') for k in ('input','output'))*quantity
                    campaign=Campaign(action,month,proposal['components'],source['resource_minutes']*quantity,total_tokens,source['resource_minutes']*quantity,total_tokens,bill,seed_funded,operating_funded,proposal['expected_incremental_terminal_cash'])
                    events.append({'kind':'research_purchase','month':month,**proposal,'seed_funded':seed_funded,'operating_funded':operating_funded,'cash_after':cash,'known_future_refunds_before':known_refunds,'unpaid_obligations_before':unpaid_fixed+unpaid_refund,'available_operating_after_reserve_before':available_operating,'source_budget':source['derived_budget_usd'],'quantity_multiplier':quantity});row['research_action']=action
            minutes+=reserved_research['minutes'];tokens+=reserved_research['tokens'];container_minutes+=reserved_research['container_minutes']
            if campaign:
                capminutes=min(minutes,o['monthly_workbench_minutes']*o['research_fraction_limit']);captokens=min(tokens,o['monthly_token_quota']*o['research_fraction_limit']);source=register['investment_campaigns'][campaign.action];container_total=source['container_sessions_16gb']*20*sc['activity_quantity_multiplier'];remaining_fraction=campaign.remaining_minutes/campaign.total_minutes
                fraction=min(remaining_fraction,capminutes/campaign.total_minutes,captokens/campaign.total_tokens,container_minutes/container_total)
                if fraction>0:
                    activity_plan={'usd':0.,'minutes':campaign.total_minutes*fraction,'tokens':campaign.total_tokens*fraction,'container_minutes':container_total*fraction};execute(activity_plan,'investment_cost',True);campaign.remaining_minutes-=activity_plan['minutes'];campaign.remaining_tokens-=activity_plan['tokens'];campaign.consumed_minutes+=activity_plan['minutes'];campaign.consumed_tokens+=activity_plan['tokens']
                row['research_progress_fraction']=1-campaign.remaining_minutes/campaign.total_minutes
                if campaign.remaining_minutes<1e-6 and campaign.remaining_tokens<1e-6:
                    for name in campaign.components:
                        ac=c['assets'][name];r=rng(seed,world,800+ac['bit']);good=r.random()<sc['asset_build_success'];pilot_truth=sc['retained_component_correctness'] if good else .65;blind=r.random()<sc['pilot_shared_blindspot'];observed_p=.98 if blind else pilot_truth;n=ac['pilot_cases'];passes=int((r.random(n)<observed_p).sum());admitted=passes/n>=ac['pilot_pass_threshold'];pilot_transfer=int((r.random(8)<sc['transfer_success']).sum());estimated_transfer=(2+pilot_transfer)/12
                        graph=make_simulated_record(name,world,month+1,ac['lifetime_months'],ac['domains'],admitted);catalog[name]=graph;check=inspect_graph(graph,month+1,catalog);admitted=admitted and check['admitted'];transfer=r.random(c['scope']['recipient_agents'])<sc['transfer_success'];assets[name]=Asset(name,month+1,good,(2+passes)/(4+n),estimated_transfer,transfer,graph,active=admitted);totals['research_admissions']+=int(admitted)
                        events.append({'kind':'research_evaluation','asset':name,'month':month,'ready_month':month+1,'campaign':campaign.action,'admitted':bool(admitted),'observed_pilot_passes':passes,'observed_pilot_cases':n,'estimated_transfer':estimated_transfer,'latent_campaign_good_for_analysis_only':bool(good),'latent_shared_pilot_blindspot_for_analysis_only':bool(blind),'graph_record':copy.deepcopy(graph),'graph_admission':check,'scope_basis':'Declared supported schema classes, not a claim of empirical market diversity.'})
                    events.append({'kind':'research_complete','action':campaign.action,'month':month,'actual_build_months':month-campaign.starts+1,'paid_cost':campaign.bill,'consumed_minutes':campaign.consumed_minutes,'consumed_tokens':campaign.consumed_tokens});campaign=None
            row['active_assets']=','.join(n for n,a in assets.items() if a.active and month>=a.ready)
        else:
            totals['expired_orders']+=len(queue);queue=[]
        for key in resource_keys:row[key]=totals[key]-resources_before[key]
        for suffix,limit in [('tokens','capacity_tokens'),('workbench_minutes','capacity_workbench_minutes'),('container_minutes','capacity_container_minutes')]:assert row['delivery_'+suffix]+row['research_'+suffix]<=row[limit]+1e-5
        row['pending_recovery_tasks']=len(recovery_backlog)
        row['closing_cash']=cash;row['unpaid_obligations']=unpaid_fixed+unpaid_refund;row['outstanding_receivables']=sum(sum(x) for x in invoices.values());row['known_future_refunds']=sum(sum(x) for x in refunds.values());row['queue_projects']=len(queue);row['available_uncommitted_cash']=max(0,cash-row['reserve']-row['unpaid_obligations']);row['retained_operating_cash_above_seed']=max(0,cash-c['seed_cash']-row['reserve']-row['unpaid_obligations']);row['belief_weights_after']=belief.weights.tolist()
        assert cash>=-1e-7
        assert abs(row['opening_cash']+row['collections']-row['operating_outflow']-row['investment_outflow']-row['refund_outflow']-row['arrears_outflow']-cash)<1e-5
        ledgers.append(row)
    assert not invoices and not refunds and not incident_notices and not recovery_backlog
    unpaid=unpaid_fixed+unpaid_refund;profit=cash-c['seed_cash']-unpaid
    cost_keys=['qualification_cost','unsupported_intake_cost','production_cost','correction_cost','recovery_cost','storage_cost','fixed_cost','investment_cost','maintenance_cost','revalidation_cost','recipient_acquisition_cost','payment_fees','discovery_cost','setup_fixed_cost','arrears_paid']
    full_cost=sum(totals.get(k,0.) for k in cost_keys)+unpaid;direct=sum(totals[k] for k in ['production_cost','correction_cost','recovery_cost','storage_cost','recipient_acquisition_cost']);accepted=totals['true_accepted_projects'];passed=totals['validated_deliveries']
    assert abs(profit-(totals['collections']-totals['refunds']-full_cost))<1e-4
    metrics={**totals,'net_profit':profit,'quality_adjusted_profit':profit-totals['undetected_paid_false_pass_revenue'],'closing_cash':cash,'unpaid_obligations':unpaid,'insolvent':bool(stopped),'fully_allocated_cost_total':full_cost,'direct_cost_total':direct,'fully_allocated_cost_per_true_project':full_cost/accepted if accepted else None,'direct_cost_per_true_project':direct/accepted if accepted else None,'material_error_fraction':totals['false_passes']/passed if passed else 0.,'mean_price_fraction':float(np.mean(price_history)) if price_history else None,'total_calendar_months_including_setup_runoff':c['months']+c['runoff_months']+setup_months,'setup_months':setup_months,'setup_tokens':discovery['tokens'],'setup_workbench_minutes':discovery['minutes'],'world_arrival_multiplier':demand,'R_active_or_used':bool('R' in assets and assets['R'].uses>0),'V_active_or_used':bool('V' in assets and assets['V'].uses>0),'campaign_unfinished_at_horizon':bool(campaign),'transfer_trials':transfer_trials,'transfer_successes':transfer_successes}
    return Result(world,scenario,policy,metrics,ledgers,events,catalog,{'weights':belief.weights.tolist(),'arrival_mean':belief.arrival_shape/belief.arrival_rate,'observation_scope':market['observed_choice']})

def paired(none,optional,fixed):
    incremental=optional.metrics['net_profit']-none.metrics['net_profit'];quality_incremental=optional.metrics['quality_adjusted_profit']-none.metrics['quality_adjusted_profit'];invested=optional.metrics['investment_cost']>0;used=optional.metrics['R_uses']+optional.metrics['V_uses']>0
    return {'optional_incremental_profit':incremental,'optional_quality_adjusted_incremental_profit':quality_incremental,'price_policy_total_effect':optional.metrics['net_profit']-fixed.metrics['net_profit'],'incremental_true_projects':optional.metrics['true_accepted_projects']-none.metrics['true_accepted_projects'],'research_repaid':bool(invested and used and incremental>0),'quality_adjusted_research_repaid':bool(invested and used and quality_incremental>0),'operating_only_research':bool(invested and optional.metrics['research_seed_funded']==0),'positive_delivery_without_research':none.metrics['net_profit']>0}


def summarize(results,comparisons):
    out={'worlds':len(comparisons),'policies':{},'paired':{}}
    for policy in POLICIES:
        rr=[r for r in results if r.policy==policy];ms=[r.metrics for r in rr];p={}
        for key in ['net_profit','quality_adjusted_profit','true_accepted_projects','false_passes','material_error_fraction','mean_price_fraction','fully_allocated_cost_per_true_project','direct_cost_per_true_project','investment_cost','research_seed_funded','research_operating_funded','R_uses','V_uses','capacity_blocked','cash_blocked','expired_orders']:
            values=[m[key] for m in ms if m[key] is not None and (key!='material_error_fraction' or m['validated_deliveries']>0)];p[key]=stats(values) if values else None
        accepted=sum(m['true_accepted_projects'] for m in ms);p['pooled_fully_allocated_cost_per_true_project']=sum(m['fully_allocated_cost_total'] for m in ms)/accepted if accepted else None;p['pooled_direct_cost_per_true_project']=sum(m['direct_cost_total'] for m in ms)/accepted if accepted else None;p['aggregate_true_projects']=accepted
        for name,test in [('probability_profit',lambda m:m['net_profit']>0),('probability_quality_adjusted_profit',lambda m:m['quality_adjusted_profit']>0),('probability_insolvency',lambda m:m['insolvent']),('probability_research',lambda m:m['investment_cost']>0),('probability_seed_funded_research',lambda m:m['research_seed_funded']>0),('probability_unfinished_campaign',lambda m:m['campaign_unfinished_at_horizon'])]:p[name]=sum(bool(test(m)) for m in ms)/len(ms)
        total_delivered=sum(m['validated_deliveries'] for m in ms);p['pooled_material_error_fraction']=sum(m['false_passes'] for m in ms)/total_delivered if total_delivered else None;p['zero_delivery_worlds']=sum(m['validated_deliveries']==0 for m in ms)
        p['zero_output_worlds']=sum(m['true_accepted_projects']==0 for m in ms);p['ratio_distribution_note']='Per-world cost ratios condition on positive output; pooled cost includes every world and zero-output costs.';out['policies'][policy]=p
    for key in ['optional_incremental_profit','optional_quality_adjusted_incremental_profit','price_policy_total_effect','incremental_true_projects']:out['paired'][key]=stats([r[key] for r in comparisons])
    for key in ['research_repaid','quality_adjusted_research_repaid','operating_only_research','positive_delivery_without_research']:out['paired'][f'probability_{key}']=sum(r[key] for r in comparisons)/len(comparisons)
    return out


def run_scenario(c,register,scenario,worlds,seed,output=None,structural_off=False):
    results=[];comparisons=[]
    for world in range(worlds):
        shared=initial_primitives(c,c['scenarios'][scenario],seed,world);triplet=[simulate(c,register,scenario,world,p,seed,shared,structural_off) for p in POLICIES];results.extend(triplet);comparisons.append(paired(*triplet))
    summary=summarize(results,comparisons);summary['scenario']=scenario;summary['seed']=seed;summary['sampling_unit']=c['scope']['sampling_unit']
    if output:
        out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=True)
        with gzip.open(out/f'{scenario}_complete_records.jsonl.gz','wt') as f:
            for r in results:f.write(dumps({'world':r.world,'scenario':r.scenario,'policy':r.policy,'metrics':r.metrics,'ledger':r.ledger,'events':r.events,'graph_records':r.graph_records,'belief':r.belief})+'\n')
        write_csv(out/f'{scenario}_worlds.csv',[{'world':r.world,'scenario':r.scenario,'policy':r.policy,**r.metrics,**(comparisons[r.world] if r.policy=='optimized_optional' else {})} for r in results])
        rep=min((r for r in results if r.policy=='optimized_optional'),key=lambda r:abs(r.metrics['net_profit']-summary['policies']['optimized_optional']['net_profit']['median']));summary['illustrative_world']=rep.world
        for r in results:
            if r.world==rep.world:
                (out/f'{scenario}_illustrative_{r.policy}.json').write_text(dumps({'world':r.world,'metrics':r.metrics,'ledger':r.ledger,'events':r.events,'belief':r.belief},indent=2))
                write_csv(out/f'{scenario}_illustrative_{r.policy}_ledger.csv',[{k:v for k,v in row.items() if k not in ('price_curve','belief_weights_before','belief_weights_after')} for row in r.ledger])
        (out/f'{scenario}_summary.json').write_text(json.dumps(summary,indent=2))
    return summary


def load_inputs(config_path):
    c=json.loads(pathlib.Path(config_path).read_text());register=json.loads((HERE/c['cost_register']).resolve().read_text());return c,register

def freeze(config_path,out):
    c,register=load_inputs(config_path);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    closure={str(p.relative_to(HERE.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list(HERE.glob('*.py'))+[HERE/'config.json',(HERE/c['cost_register']).resolve()]}
    protocol=HERE/'PROTOCOL.md'
    if protocol.exists():closure[str(protocol.relative_to(HERE.parent))]=hashlib.sha256(protocol.read_bytes()).hexdigest()
    record={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'study_id':c['study_id'],'configuration_sha256':sha(c),'workflow_costs_sha256':sha(register),'closure_sha256':closure,'train_seed':c['train_seed'],'test_seed':c['test_seed'],'policy_names':POLICIES,'primary_scenarios':list(c['scenarios']),'status':'Freeze before independent confirmation worlds; development outputs remain separately labeled.'}
    (out/'frozen_config.json').write_text(json.dumps(c,indent=2));(out/'frozen_workflow_costs.json').write_text(json.dumps(register,indent=2));(out/'freeze.json').write_text(json.dumps(record,indent=2));return record

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(HERE/'config.json'));p.add_argument('--output',default=str(HERE.parent/'results/pilot'));p.add_argument('--worlds',type=int,default=20);p.add_argument('--scenarios',nargs='+',default=['conservative','central','favorable']);p.add_argument('--phase',choices=['train','confirm'],default='train');p.add_argument('--freeze',action='store_true');p.add_argument('--structural-off',action='store_true');a=p.parse_args();c,register=load_inputs(a.config);out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if a.freeze:print(json.dumps(freeze(a.config,out),indent=2));return
    if a.phase=='confirm':
        f=json.loads((out/'freeze.json').read_text());assert f['configuration_sha256']==sha(c);assert f['workflow_costs_sha256']==sha(register)
        for path,h in f['closure_sha256'].items():assert hashlib.sha256((HERE.parent/path).read_bytes()).hexdigest()==h,f'Changed frozen file: {path}'
    seed=c['train_seed'] if a.phase=='train' else c['test_seed'];summaries={}
    for scenario in a.scenarios:
        summary=run_scenario(c,register,scenario,a.worlds,seed,out,a.structural_off);summaries[scenario]=summary
        print(json.dumps({'scenario':scenario,'worlds':a.worlds,'profit':summary['policies']['optimized_optional']['net_profit'],'research_probability':summary['policies']['optimized_optional']['probability_research'],'incremental':summary['paired']['optional_incremental_profit']}),flush=True)
    result={'status':'Frozen independent confirmation' if a.phase=='confirm' else 'EXPLORATORY DEVELOPMENT PILOT','config_sha256':sha(c),'workflow_costs_sha256':sha(register),'seed':seed,'worlds_per_scenario':a.worlds,'scenarios':summaries,'sampling_unit':c['scope']['sampling_unit']};(out/'summary.json').write_text(json.dumps(result,indent=2));(out/'run_manifest.json').write_text(json.dumps({'completed_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'numpy':np.__version__,'seed':seed,'worlds':a.worlds,'phase':a.phase},indent=2))

if __name__=='__main__':main()
