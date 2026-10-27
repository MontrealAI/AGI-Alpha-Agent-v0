# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, copy, csv, gzip, hashlib, json, math, pathlib, sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np
from graph_admission import make_simulated_record, inspect as inspect_graph
from graph_lifecycle import LifecycleGraph, simulated_authorities, create_assessed_record, reassess_record, default_policy, digest as graph_digest

HERE=pathlib.Path(__file__).resolve().parent
POLICIES=('optimized_beta','optimized_private','optimized_network','fixed_network')

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
    for name in ['correction','revalidation','recovery','asset_construction_unit','asset_evaluation_unit','asset_integration_unit','asset_revalidation_unit','asset_maintenance_month','recipient_acquisition','network_access','network_distribution','network_composition','beta_version_reevaluation','graph_revocation_propagation']:out[name]=unit(register[name],register)
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
    lifecycle_id:str=''
    creator:int=0
    beta_version:str=''

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
    identifier:str=''
    beta_version:str=''

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
    lifecycle:dict=field(default_factory=dict)
    project_sets:dict=field(default_factory=dict)

def beta_epoch(c,month):
    return max((e for e in c['network']['beta_epochs'] if e['month']<=month),key=lambda e:e['month'])

def current_table(c,base,month):
    table=copy.deepcopy(base);epoch=beta_epoch(c,month)
    for s in c['_stages']:
        if s['potentially_reusable_by'] in ('R','V'):table[s['id']]=scaled(table[s['id']],epoch['reconstruction_quantity_factor'])
    return table

def recipient_weights(c,domain):
    n=c['scope']['recipient_agents'];specialists=[i for i in range(n) if domain in c['scope']['recipient_specialties'][i%len(c['scope']['recipient_specialties'])]];p=np.full(n,(1-c['scope']['specialist_routing_fraction'])/n)
    if specialists:p[specialists]+=c['scope']['specialist_routing_fraction']/len(specialists)
    else:p+=c['scope']['specialist_routing_fraction']/n
    return p


def initial_primitives(c,sc,seed,world):
    r=rng(seed,world,999);n=c['scope']['recipient_agents'];d=c['scope']['domains'];equivalent={};partial={}
    for a in ('R','V'):
        draws=r.random((n,d));equivalent[a]=draws<c['scope'][f'existing_equivalent_{a}'];partial[a]=(draws>=c['scope'][f'existing_equivalent_{a}'])&(draws<c['scope'][f'existing_equivalent_{a}']+c['scope']['partial_equivalent_probability'])
    multiplier=math.exp(r.normal(-sc['world_arrival_log_sigma']**2/2,sc['world_arrival_log_sigma']));months=[]
    for month in range(1,c['months']+1):
        r=rng(seed,world,month,10);n=int(r.poisson(sc['arrivals_month']*(1+sc['arrival_growth'])**(month-1)*multiplier));u=r.random((n,40));values=np.exp(r.normal(math.log(sc['buyer_value_multiplier'])-c['market']['value_log_sigma']**2/2,c['market']['value_log_sigma'],n));taste=r.gumbel(size=(n,4));burst=r.random()<c['operations']['monthly_common_burst_probability'];months.append((u,values,taste,burst))
    return equivalent,partial,months,multiplier


def expected_delivery(c,sc,table,coverage_R=0.,coverage_V=0.,component_quality=None,checker_quality=None):
    stages=resource_sum(table[s['id']] for s in c['_stages'])
    for label,coverage in [('R',coverage_R),('V',coverage_V)]:
        removable=resource_sum(table[s['id']] for s in c['_stages'] if s['potentially_reusable_by']==label)
        for k in stages:stages[k]-=removable[k]*coverage
    stages=scaled(stages,sc['activity_quantity_multiplier'])
    richmix=c['scope']['base_share']+(1-c['scope']['base_share'])*c['scope']['rich_activity_multiplier']
    stages=scaled(stages,richmix)
    component=component_quality if component_quality is not None else sc['reconstruction_correctness']+(sc['retained_component_correctness']-sc['reconstruction_correctness'])*coverage_R
    good=sc['semantic_correctness']*component*(1-sc['shared_fault_probability']);bad=1-good;truepasses=falsepasses=corrections=0.
    sensitivity=.5*(sc['semantic_validator_sensitivity']+sc['mechanical_validator_sensitivity']);checker=checker_quality if checker_quality is not None else sc['reconstruction_correctness']+(sc['retained_component_correctness']-sc['reconstruction_correctness'])*coverage_V;ordinary_miss=(1-checker)*.5+checker*(1-sensitivity);miss=ordinary_miss*(1-sc['shared_fault_probability'])+sc['shared_fault_miss']*sc['shared_fault_probability']
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
        existing=c.get('_known_coverage',{}).get(name,c['scope'][f'existing_equivalent_{name}']+c['scope']['partial_equivalent_probability']*c['scope']['partial_reconstruction_saving'])
        quality=c['_scenario']['reconstruction_correctness']+(c['_scenario']['retained_component_correctness']-c['_scenario']['reconstruction_correctness'])*existing
        if name in assets and assets[name].active and month>=assets[name].ready:
            a=assets[name];fraction=a.estimated_transfer*sum(c['scope']['domain_weights'][d] for d in c['assets'][name]['domains'])
            if c.get('_private'):fraction*=sum(c['scope']['domain_weights'][d]*recipient_weights(c,d)[a.creator] for d in range(5))
            additional=(1-existing)*fraction;existing+=additional*c['network']['alpha_activity_effect_fraction'];quality+=(a.estimated_correctness-c['_scenario']['reconstruction_correctness'])*additional*c['network']['alpha_quality_effect_fraction']
        out[name]=clip(existing)
        out[name+'_quality']=clip(quality)
    return out


def price_plan(c,sc,table,belief,assets,month,policy,mask=0):
    c['_scenario']=sc;c['_private']=policy=='optimized_private'
    cov=coverage(c,assets,month)
    for name in ('R','V'):
        if mask&c['assets'][name]['bit']:
            prior=cov[name];scope=sum(c['scope']['domain_weights'][d] for d in c['assets'][name]['domains']);share=sum(c['scope']['domain_weights'][d]*recipient_weights(c,d)[c['network']['creator_recipient']] for d in range(5)) if c.get('_private') else 1.;additional=(1-prior)*scope*share*sc['transfer_success']*sc['asset_build_success'];cov[name]=prior+additional*c['network']['alpha_activity_effect_fraction'];cov[name+'_quality']+=(sc['retained_component_correctness']-sc['reconstruction_correctness'])*additional*c['network']['alpha_quality_effect_fraction']
    delivery=expected_delivery(c,sc,table,cov['R'],cov['V'],cov['R_quality'],cov['V_quality'])
    extra_access=sum(max(0,cov[n]-c.get('_known_coverage',{}).get(n,c['scope'][f'existing_equivalent_{n}']+c['scope']['partial_equivalent_probability']*c['scope']['partial_reconstruction_saving'])) for n in ('R','V'))
    graph_resources=scaled(table['network_access'],extra_access*sc['activity_quantity_multiplier'])
    for key in graph_resources:delivery[key]+=graph_resources[key]
    fractions=[c['fixed_price_ablation']] if policy=='fixed_network' else c['price_fractions'];prob=belief.weights@buyer_probabilities(c,fractions,queue_days=belief.queue_days,incident_penalty=belief.incident_penalty)
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
    if policy=='optimized_beta' or campaign:return None,base
    actions=[]
    epoch=beta_epoch(c,month)
    missing=[n for n in ('R','V') if (n,epoch['version']) not in attempted and not (n in assets and assets[n].active)]
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
        survival=sum((1-max(c['assets'][n]['obsolescence_probability'] for n in components))**a/(1+c['policy']['financial_monthly_discount_rate'])**(a+duration)*beta_epoch(c,min(c['months'],month+duration+a))['reconstruction_quantity_factor']/epoch['reconstruction_quantity_factor'] for a in range(horizon))
        monthly_maintenance=len(components)*table['asset_maintenance_month']['usd']*quantity
        revalidation=(horizon//c['network']['periodic_reassessment_months'])*table['beta_version_reevaluation']['usd']*quantity
        receivers=1 if c.get('_private') else c['scope']['recipient_agents'];acquisition=max(0,receivers-1)*len(components)*(table['recipient_acquisition']['usd']+table['network_distribution']['usd'])*quantity
        composition=(receivers*table['network_composition']['usd']*quantity) if len(components)==2 else 0.
        incremental=(after['expected_monthly_net']-base['expected_monthly_net']-monthly_maintenance)*survival-bill-revalidation-acquisition-composition
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

def alpha_assessment_inputs(c,sc,table,belief,assets,names,truth,seed,world,month,identifier,bill,policy,reevaluation=False):
    """Paid synthetic paired evidence; only these observed trials enter admission.

    ``truth`` generates assessment observations. It is never copied into the
    lifecycle assessment or the controller forecast; future transfer draws are
    separate and inaccessible here.
    """
    epoch=beta_epoch(c,month);number=c['network']['reassessment_cases'] if reevaluation else max(c['assets'][n]['pilot_cases'] for n in names)
    stream=rng(seed,world,6000,month,sum(c['assets'][n]['bit'] for n in names),int(reevaluation));creator=c['network']['creator_recipient'];private=policy=='optimized_private'
    scopes=sorted(set(d for n in names for d in c['assets'][n]['domains']));eligible=[];eligible_mass=0.;missing_recipients=set()
    for d in scopes:
        for recipient,p in enumerate(recipient_weights(c,d)):
            if private and recipient!=creator:continue
            missing=[n for n in names if d in c['assets'][n]['domains'] and not c['_equiv'][n][recipient,d]]
            if not missing:continue
            mass=c['scope']['domain_weights'][d]*p;eligible.append((recipient,d,mass));eligible_mass+=mass;missing_recipients.add(recipient)
    probabilities=np.asarray([x[2] for x in eligible]);probabilities=probabilities/probabilities.sum() if len(probabilities) else probabilities
    observations=[];component_passes={n:0 for n in names};transfer_passes=int((stream.random(8)<sc['transfer_success']).sum());transfer_estimate=(2+transfer_passes)/12
    for case in range(number):
        component_draw={n:stream.random() for n in ('R','V')}
        for name in names:component_passes[name]+=int(component_draw[name]<(sc['retained_component_correctness'] if truth[name] else .65))
        if eligible:recipient,domain,_=eligible[int(stream.choice(len(eligible),p=probabilities))]
        else:recipient,domain=creator,scopes[0]
        base_savings={};candidate_savings={};base_quality={};candidate_quality={}
        for name in ('R','V'):
            existing=1. if c['_equiv'][name][recipient,domain] else c['scope']['partial_reconstruction_saving'] if c['_partial'][name][recipient,domain] else 0.
            quality=sc['reconstruction_correctness']+(sc['retained_component_correctness']-sc['reconstruction_correctness'])*existing
            retained=assets.get(name)
            if retained and retained.lifecycle_id!=identifier and retained.active and month>=retained.ready and domain in c['assets'][name]['domains'] and recipient in retained.acquisition_done and retained.transfer[recipient] and (not private or recipient==retained.creator):
                existing=1.;quality=sc['retained_component_correctness'] if retained.good else .65
            base_savings[name]=candidate_savings[name]=existing;base_quality[name]=candidate_quality[name]=quality
            if name in names and domain in c['assets'][name]['domains'] and existing<1:
                candidate_savings[name]=existing+(1-existing)*c['network']['alpha_activity_effect_fraction'];candidate_quality[name]=quality+((sc['retained_component_correctness'] if truth[name] else .65)-quality)*c['network']['alpha_quality_effect_fraction']
        local=copy.deepcopy(c);local['scope']['base_share']=1.;local_sc=copy.deepcopy(sc);local_sc['semantic_correctness']=clip(sc['semantic_correctness']-c['scope']['domain_semantic_penalties'][domain]);rich=stream.random()>c['scope']['base_share'];local_sc['activity_quantity_multiplier']*=c['scope']['rich_activity_multiplier'] if rich else 1.
        beta_test={n:component_draw[n]<base_quality[n] for n in ('R','V')};alpha_test={n:component_draw[n]<candidate_quality[n] for n in ('R','V')}
        beta=expected_delivery(local,local_sc,table,base_savings['R'],base_savings['V'],float(beta_test['R']),float(beta_test['V']));alpha=expected_delivery(local,local_sc,table,candidate_savings['R'],candidate_savings['V'],float(alpha_test['R']),float(alpha_test['V']))
        value=sc['human_reference']*(c['scope']['rich_human_reference_multiplier'] if rich else 1.)*price_plan(c,sc,table,belief,assets,month,policy)['fraction']
        def observed_net(work,accepted):
            ancillary=work['false_pass']*c['operations']['postdelivery_discovery']*table['recovery']['usd']*local_sc['activity_quantity_multiplier']+(work['true_pass']+work['false_pass'])*(c['operations']['storage_per_delivery']+c['operations']['payment_fixed']*sc['collection_probability'])
            return value*sc['collection_probability']*(1-c['operations']['payment_fraction'])*accepted-work['usd']-ancillary
        beta_value=observed_net(beta,beta['true_pass']);alpha_value=observed_net(alpha,alpha['true_pass'])
        observations.append({'case_id':f'{identifier}:assessment:{month}:{case}','scope':c['scope']['domain_names'][domain],'beta_version':epoch['version'],'candidate_net_value':float(alpha_value),'beta_net_value':float(beta_value),'equivalent_net_values':[float(beta_value)] if all(base_savings[n]==1 for n in names if domain in c['assets'][n]['domains']) else [],'component_test_passed':bool(all(alpha_test[n] for n in names if domain in c['assets'][n]['domains'])),'beta_component_tests':{n:bool(v) for n,v in beta_test.items()},'candidate_component_tests':{n:bool(v) for n,v in alpha_test.items()},'acceptance_unit':'component_test','project_value_basis':'MODEL_EXTRAPOLATION_FROM_COMPONENT_TESTS','evidence_basis':'SIMULATED_PAIRED_ASSESSMENT','group_id':f'{identifier}:domain{domain}'})
    horizon=max(0,min(c['network']['alpha_forecast_horizon_months'],c['months']-month,min(c['assets'][n]['lifetime_months'] for n in names)))
    projected=price_plan(c,sc,table,belief,assets,month,policy);survival=sum((1-max(c['assets'][n]['obsolescence_probability'] for n in names))**a*beta_epoch(c,min(c['months'],month+a+1))['reconstruction_quantity_factor']/epoch['reconstruction_quantity_factor']/(1+c['policy']['financial_monthly_discount_rate'])**a for a in range(horizon));uses=projected['expected_started']*eligible_mass*transfer_estimate*survival
    acquisition=sum(recipient!=creator for recipient in missing_recipients)*len(names)*table['recipient_acquisition']['usd']*sc['activity_quantity_multiplier'];access=uses*len(names)*table['network_access']['usd']*sc['activity_quantity_multiplier'];distribution=0. if private else sum(recipient!=creator for recipient in missing_recipients)*len(names)*table['network_distribution']['usd']*sc['activity_quantity_multiplier']
    costs={'sunk_construction':bill,'sunk_assessment':table['beta_version_reevaluation']['usd']*sc['activity_quantity_multiplier'] if reevaluation else 0.,'remaining_acquisition':acquisition,'remaining_integration':0.,'remaining_maintenance':len(names)*table['asset_maintenance_month']['usd']*horizon*sc['activity_quantity_multiplier'],'remaining_revalidation':(horizon//c['network']['periodic_reassessment_months'])*table['beta_version_reevaluation']['usd']*sc['activity_quantity_multiplier'],'remaining_composition':len(missing_recipients)*table['network_composition']['usd']*sc['activity_quantity_multiplier'] if len(names)>1 else 0.,'remaining_privacy':distribution+access,'remaining_risk':0.}
    forecast={'expected_uses':float(uses),'recipients_missing_equivalent':len(missing_recipients),'basis':'ASSUMED_FROM_OBSERVED_STATE','forecast_id':f'{identifier}:forecast:{month}','horizon_months':horizon,'eligible_project_fraction':eligible_mass,'prior_mean_gain':c['network']['admission_mean_gain_prior'],'prior_effective_cases':c['network']['admission_prior_effective_cases'],'assumed_transfer_probability':transfer_estimate,'beta_erosion_included':True}
    estimate={n:(2+component_passes[n])/(4+number) for n in names};valid=all(component_passes[n]/number>=c['assets'][n]['pilot_pass_threshold'] for n in names)
    evidence={'paid_receipt_id':f'{identifier}:paid:{month}','paid_amount':table['beta_version_reevaluation']['usd']*sc['activity_quantity_multiplier'] if reevaluation else bill,'payment_basis':'SIMULATED_LEDGER_RECEIPT','evidence_basis':'SIMULATED_PAIRED_ASSESSMENT','beta_qualified':True,'equivalents_checked':True,'evidence_hash':sha(observations),'beta_version':epoch['version'],'policy_hash':sha(c['network']),'observed_month':month,'independent_checks_passed':bool(valid),'actual_paired_component_cases':number,'complete_project_test_executions':0,'acceptance_unit':'component_test','project_value_basis':'MODEL_EXTRAPOLATION_FROM_COMPONENT_TESTS','component_passes':component_passes,'transfer_pilot_cases':8,'transfer_pilot_passes':transfer_passes,'composition_checks_passed':bool(valid),'composition_receipt_id':f'{identifier}:joint-paid:{month}' if len(names)>1 else None,'dependency_manifest_hash':graph_digest([]),'validation_scope':'Modeled bounded synthetic component and compatibility tests with known labels. Project-dollar effects are conditional model extrapolation; no complete project trials or future customer outcomes are observed.'}
    return observations,costs,forecast,evidence,estimate,transfer_estimate

def simulate(c,register,scenario,world,policy,seed,shared=None,structural_off=False):
    c=copy.deepcopy(c);c['_stages']=register['stages'];sc=c['scenarios'][scenario];c['_scenario']=sc;c['_private']=policy=='optimized_private';o=c['operations'];market=c['market'];base_table=cost_table(register);table=current_table(c,base_table,1)
    equiv,partial,months,demand=shared or initial_primitives(c,sc,seed,world);equiv={k:v.copy() for k,v in equiv.items()};partial={k:v.copy() for k,v in partial.items()};experience=np.zeros((c['scope']['recipient_agents'],c['scope']['domains']))
    discovery=resource_sum(scaled(table[k],n) for k,n in c['discovery_budget_counts'].items());setup_months=math.ceil(max(discovery['minutes']/o['monthly_workbench_minutes'],discovery['tokens']/o['monthly_token_quota']))
    fixed=o['monthly_control_cost']+o['monthly_business_automation_cost'];cash=c['seed_cash']-discovery['usd']-setup_months*fixed;assert cash>=0
    totals={k:0. for k in ['collections','payment_fees','qualified_opportunities','qualification_cost','unsupported_intake_cost','orders','human_choices','retain_choices','decline_choices','attempted_projects','true_accepted_projects','false_passes','validated_deliveries','failed_projects','abstentions','expired_orders','correction_rounds','production_cost','correction_cost','recovery_cost','storage_cost','fixed_cost','refunds','investment_cost','maintenance_cost','revalidation_cost','recipient_acquisition_cost','research_seed_funded','research_operating_funded','delivery_tokens','delivery_workbench_minutes','delivery_container_minutes','research_tokens','research_workbench_minutes','research_container_minutes','cash_blocked','capacity_blocked','observed_incidents','undetected_paid_false_pass_revenue','R_uses','V_uses','existing_equivalent_uses','graph_rejections','research_campaigns','research_admissions','price_boundary_months']}
    totals['discovery_cost']=discovery['usd'];totals['setup_fixed_cost']=setup_months*fixed
    for k in ['network_access_cost','network_distribution_cost','network_composition_cost','beta_reevaluation_cost','revocation_cost','alpha_candidates','alpha_admissions','alpha_rejections','alpha_reassessments','alpha_retirements','alpha_inventory_erosion','new_admitted_expected_alpha','recipient_adoptions','rich_true_projects','offered_price_total','delivered_price_total','offered_projects']:totals[k]=0.
    belief=Belief(np.asarray(market['prior_weights'],float)/sum(market['prior_weights']),market['arrival_prior_shape'],market['arrival_prior_rate']);assets={};catalog={};attempted=set();campaign=None;events=[];ledgers=[];invoices={};refunds={};incident_notices={};queue=[];recovery_backlog=[];stopped=False;unpaid_fixed=0.;unpaid_refund=0.;transfer_trials=0;transfer_successes=0;price_history=[];last_delivered=[]
    member_names=[f'agent{i}.agent.agi.eth' for i in range(c['scope']['recipient_agents'])];creator=c['network']['creator_recipient'];registry,actors=simulated_authorities(member_names[creator],member_names,f'world{world}');lpolicy=default_policy(version=c['study_id'],evidence_max_age=c['network']['evidence_max_age_months'],minimum_paired_cases=c['network']['assessment_minimum_cases'],prior_mean_gain=c['network']['admission_mean_gain_prior'],prior_effective_cases=c['network']['admission_prior_effective_cases']);lifecycle=LifecycleGraph(lpolicy,registry,beta_epoch(c,1)['version']);nodes={};composition_done=set();true_project_ids=set();rich_project_ids=set();capacity_project_ids=set();recipient_user_ids=set();completed_domains=set()
    for month in range(1,c['months']+c['runoff_months']+1):
        epoch=beta_epoch(c,min(month,c['months']));table=current_table(c,base_table,min(month,c['months']));c['_equiv']=equiv;c['_partial']=partial;c['_known_coverage']={n:float(sum(c['scope']['domain_weights'][d]*np.dot(recipient_weights(c,d),equiv[n][:,d]+(~equiv[n][:,d])*partial[n][:,d]*c['scope']['partial_reconstruction_saving']) for d in range(5))) for n in ('R','V')}
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
        row['reserve']=reserve;row['beta_version']=epoch['version'];row['beta_reconstruction_quantity_factor']=epoch['reconstruction_quantity_factor']
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
            if not execute(recovery_plan,recovery_plan.get('_cost_key','recovery_cost')):
                if cash<recovery_plan['usd']:
                    unpaid_fixed+=recovery_plan['usd'];stopped=True;active_month=False
                else:remaining_recovery.append(recovery_plan)
        recovery_backlog=remaining_recovery
        if active_month:
            u,values,taste,burst=months[month-1]
            changed_beta=epoch['version']!=lifecycle.beta_version
            if changed_beta:
                lifecycle.beta_update(epoch['version'],actors['governance'],month)
                events.append({'kind':'beta_update','month':month,'beta_version':epoch['version'],'reconstruction_quantity_factor':epoch['reconstruction_quantity_factor'],'basis':'ASSUMED_MOVING_BETA_SCENARIO'})
            public=rng(seed,world,month,30)
            for name in ('R','V'):
                available=(public.random(equiv[name].shape)<epoch['public_equivalent_probability_per_month'])&(~equiv[name]);available[:,5]=False
                for receiver,domain_copy in zip(*np.nonzero(available)):
                    acq=scaled(table['recipient_acquisition'],sc['activity_quantity_multiplier'])
                    if cash-acq['usd']>=reserve and execute(acq,'recipient_acquisition_cost'):equiv[name][receiver,domain_copy]=True
            c['_known_coverage']={n:float(sum(c['scope']['domain_weights'][d]*np.dot(recipient_weights(c,d),equiv[n][:,d]+(~equiv[n][:,d])*partial[n][:,d]*c['scope']['partial_reconstruction_saving']) for d in range(5))) for n in ('R','V')}
            def retire_node(identifier,reason):
                node=nodes[identifier]
                if node.get('retired'):return
                before=lifecycle.snapshot(identifier);value=max(0,(before.get('assessment') or {}).get('expected_prospective_net_alpha',0.));lifecycle.revoke(identifier,actors['governance'],month,reason,retire=True);node['retired']=True;totals['alpha_retirements']+=1
                if changed_beta:totals['alpha_inventory_erosion']+=value
                for name in node['components']:
                    if name in assets and assets[name].lifecycle_id==identifier:assets[name].active=False;assets[name].graph['revoked']=True
                plan=scaled(table['graph_revocation_propagation'],sc['activity_quantity_multiplier']);plan['_cost_key']='revocation_cost'
                if not execute(plan,'revocation_cost'):recovery_backlog.append(plan)
                events.append({'kind':'alpha_retirement','month':month,'id':identifier,'reason':reason,'previous_expected_inventory_value':value,'beta_version':epoch['version']})
            for identifier,node in list(nodes.items()):
                if node.get('retired') or not node['ever_admitted'] or month<node['ready']:continue
                names=node['components'];age=month-node['ready'];old=lifecycle.snapshot(identifier);old_value=max(0,(old.get('assessment') or {}).get('expected_prospective_net_alpha',0.));a0=assets.get(names[0]);draw=rng(seed,world,month,500+sum(c['assets'][n]['bit'] for n in names)).random()
                if age>=min(c['assets'][n]['lifetime_months'] for n in names) or draw<max(c['assets'][n]['obsolescence_probability'] for n in names):retire_node(identifier,'expired_or_obsolete');continue
                due=changed_beta or month-node['last_assessment']>=c['network']['periodic_reassessment_months'] or old['status']=='STALE'
                if due:
                    reevaluation=scaled(table['beta_version_reevaluation'],sc['activity_quantity_multiplier'])
                    if cash-reevaluation['usd']<reserve or not execute(reevaluation,'beta_reevaluation_cost'):
                        for name in names:
                            if name in assets and assets[name].lifecycle_id==identifier:assets[name].active=False
                        events.append({'kind':'alpha_reassessment_hold','month':month,'id':identifier,'beta_version':epoch['version']});continue
                    obs,costs,forecast,evidence,estimate,transfer_estimate=alpha_assessment_inputs(c,sc,table,belief,assets,names,node['truth'],seed,world,month,identifier,node['bill'],policy,True)
                    evidence['dependency_manifest_hash']=graph_digest(old['dependencies']);result=reassess_record(lifecycle,identifier,evidence,obs,costs,forecast,actors,month);totals['alpha_reassessments']+=1;node['last_assessment']=month
                    new_value=max(0,(result['record'].get('assessment') or {}).get('expected_prospective_net_alpha',0.)) if result['record'] else 0.
                    if changed_beta:totals['alpha_inventory_erosion']+=max(0,old_value-new_value)
                    events.append({'kind':'alpha_reassessment','month':month,'id':identifier,'beta_version':epoch['version'],'admitted':result['admitted'],'assessment':(result['record'] or {}).get('assessment'),'paid_cost':reevaluation['usd'],'evidence':evidence})
                    if not result['admitted']:retire_node(identifier,'nonpositive_or_failed_current_beta_assessment');continue
                    for name in names:
                        if name in assets and assets[name].lifecycle_id==identifier:assets[name].active=True;assets[name].beta_version=epoch['version'];assets[name].estimated_correctness=estimate[name];assets[name].estimated_transfer=transfer_estimate
                maintenance=scaled(table['asset_maintenance_month'],len(names)*sc['activity_quantity_multiplier'])
                if cash-maintenance['usd']<reserve or not execute(maintenance,'maintenance_cost'):retire_node(identifier,'unfunded_complete_maintenance')
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
                supported=u[j,0]<c['scope']['supported_domain_fraction'];domain=min(4,int(np.searchsorted(np.cumsum(c['scope']['domain_weights']),u[j,1]))) if supported else 5
                if not supported:
                    execute(scaled(table['intake_clarification'],sc['activity_quantity_multiplier']),'unsupported_intake_cost');continue
                rich=u[j,2]>c['scope']['base_share'];scope=c['scope']['rich_activity_multiplier'] if rich else 1.;human=sc['human_reference']*(c['scope']['rich_human_reference_multiplier'] if rich else 1.);price=fraction*human;value=values[j]*human
                own=value*market['our_quality_belief']-price-human*(market['our_review_fraction']+market['integration_fraction']+sc['buyer_trust_fraction']+belief.incident_penalty+(market['base_delivery_days']+belief.queue_days)*market['delay_cost_fraction_per_day'])
                incumbent=value*market['human_quality_belief']-human*(1+market['human_review_fraction']+market['human_delivery_days']*market['delay_cost_fraction_per_day'])
                utility=np.asarray([own,incumbent,human*market['postpone_utility_fraction'],0.])+human*market['taste_scale_fraction']*taste[j];choice=int(np.argmax(utility));offered+=1;totals['offered_price_total']+=price;totals['offered_projects']+=1
                if choice==0:
                    purchased+=1;recipient=min(c['scope']['recipient_agents']-1,int(np.searchsorted(np.cumsum(recipient_weights(c,domain)),u[j,3])));queue.append({'origin':month,'project':f'{world}:{month}:{j}','u':u[j],'recipient':recipient,'domain':domain,'scope':scope,'human_reference':human,'price':price,'estimated_minutes':1660*scope*sc['activity_quantity_multiplier']})
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
                    if a and a.active and month>=a.ready and not structural_off and not equiv[name][recipient,domain] and not (recipient in a.acquisition_done and not a.transfer[recipient]):
                        domain_name=c['scope']['domain_names'][domain];rights=lifecycle.inspect_use(a.lifecycle_id,member_names[recipient],domain_name,epoch['version'],month,operation='execute');review=inspect_graph(a.graph,month,catalog,domain)
                        if not rights['allowed'] or not review['admitted']:totals['graph_rejections']+=1
                        else:
                            reconstruction=sum(table[s['id']]['usd'] for s in register['stages'] if s['potentially_reusable_by']==name)*(1-saving)*activity
                            expected_quality_gain=(a.estimated_correctness-quality)*sc['semantic_correctness']*(1-sc['correction_success'])*project['price']*sc['collection_probability'];per_use_gain=reconstruction+expected_quality_gain-table['network_access']['usd']*sc['activity_quantity_multiplier']
                            node_record=lifecycle.snapshot(a.lifecycle_id);expected_recipient_uses=max(1,(node_record.get('forecast') or {}).get('expected_uses',0)/max(1,(node_record.get('forecast') or {}).get('recipients_missing_equivalent',1)))
                            acq=scaled(table['recipient_acquisition'],sc['activity_quantity_multiplier']);distribution=scaled(table['network_distribution'],sc['activity_quantity_multiplier']);acquisition_bill=acq['usd']+(distribution['usd'] if not c['_private'] else 0.)
                            adoption_positive=per_use_gain>0 and (recipient in a.acquisition_done or per_use_gain*expected_recipient_uses>acquisition_bill)
                            access=scaled(table['network_access'],sc['activity_quantity_multiplier'])
                            if adoption_positive and cash-access['usd']>=reserve+unpaid_fixed+unpaid_refund and execute(access,'network_access_cost'):
                                if recipient not in a.acquisition_done:
                                    acquire=lifecycle.inspect_use(a.lifecycle_id,member_names[recipient],domain_name,epoch['version'],month,operation='acquire')
                                    if acquire['allowed'] and cash-acquisition_bill>=reserve+unpaid_fixed+unpaid_refund and acq['minutes']+distribution['minutes']<=minutes and acq['tokens']+distribution['tokens']<=tokens and acq['container_minutes']+distribution['container_minutes']<=container_minutes:
                                        if execute(acq,'recipient_acquisition_cost'):
                                            if not c['_private']:assert execute(distribution,'network_distribution_cost')
                                            a.acquisition_done.add(recipient);transfer_trials+=1;transfer_successes+=int(a.transfer[recipient]);totals['recipient_adoptions']+=1;a.estimated_transfer=(2+sum(int(a.transfer[z]) for z in a.acquisition_done if z!=a.creator))/(4+len(a.acquisition_done-{a.creator}))
                                            lifecycle.use(a.lifecycle_id,member_names[recipient],domain_name,month,operation='acquire');events.append({'kind':'recipient_acquisition','month':month,'id':a.lifecycle_id,'component':name,'recipient':member_names[recipient],'successful':bool(a.transfer[recipient]),'paid_cost':acquisition_bill})
                                if recipient in a.acquisition_done and a.transfer[recipient]:
                                    saving=saving+(1-saving)*c['network']['alpha_activity_effect_fraction'];quality=quality+((sc['retained_component_correctness'] if a.good else .65)-quality)*c['network']['alpha_quality_effect_fraction'];used.append(a);lifecycle.use(a.lifecycle_id,member_names[recipient],domain_name,month,operation='execute')
                    savings[name]=saving;qualities[name]=quality
                if len(used)>1:
                    composition_key=(recipient,domain,epoch['version'],tuple(sorted(a.lifecycle_id for a in used)))
                    if composition_key not in composition_done:
                        composition=scaled(table['network_composition'],activity);allowed=all(lifecycle.inspect_use(a.lifecycle_id,member_names[recipient],c['scope']['domain_names'][domain],epoch['version'],month,operation='compose')['allowed'] for a in used)
                        if allowed and cash-composition['usd']>=reserve+unpaid_fixed+unpaid_refund and execute(composition,'network_composition_cost'):
                            composition_done.add(composition_key);events.append({'kind':'composition_checked','month':month,'recipient':member_names[recipient],'domain':domain,'components':[a.lifecycle_id for a in used],'beta_version':epoch['version'],'paid_cost':composition['usd']})
                        else:
                            for name in ('R','V'):
                                established=1. if equiv[name][recipient,domain] else c['scope']['partial_reconstruction_saving'] if partial[name][recipient,domain] else 0.;savings[name]=established;qualities[name]=sc['reconstruction_correctness']+(sc['retained_component_correctness']-sc['reconstruction_correctness'])*established
                            used=[]
                first=resource_sum(scaled(table[s['id']],1-savings.get(s['potentially_reusable_by'],0.)) for s in register['stages']);first=scaled(first,activity)
                extra=scaled(resource_sum([table['correction'],table['revalidation']]),activity)
                worst_cash=first['usd']+o['max_corrections']*extra['usd']+table['recovery']['usd']*activity+o['storage_per_delivery']
                protected=o['reserve_months']*fixed+sum(sum(x) for x in refunds.values())+unpaid_fixed+unpaid_refund+o['warranty_reserve_fraction']*(sum(last_delivered[-2:])+monthly_delivered_revenue)+sum(p['usd'] for p in recovery_backlog)
                if cash-worst_cash<protected:totals['cash_blocked']+=1;queue.append(project);continue
                if not execute(first,'production_cost'):totals['capacity_blocked']+=1;capacity_project_ids.add(project['project']);queue.append(project);continue
                totals['attempted_projects']+=1;row['attempted_projects']+=1
                for a in used:a.uses+=1;totals[a.name+'_uses']+=1;recipient_user_ids.add(recipient)
                if v[4]<o['admission_abstention']:totals['abstentions']+=1;totals['failed_projects']+=1;continue
                common=v[5]<clip(sc['shared_fault_probability']+(o['burst_shared_error_increment'] if burst else 0))
                semantic=v[6]<clip(sc['semantic_correctness']-c['scope']['domain_semantic_penalties'][domain]-(o['burst_semantic_penalty'] if burst else 0)) and not common
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
                if correct:
                    totals['true_accepted_projects']+=1;row['true_accepted_projects']+=1;true_project_ids.add(project['project']);completed_domains.add(domain)
                    if scope>1:totals['rich_true_projects']+=1;rich_project_ids.add(project['project'])
                else:totals['false_passes']+=1;row['false_passes']+=1
                price=project['price'];totals['delivered_price_total']+=price;paid=v[22]<sc['collection_probability'];due=month+sc['collection_lag'];monthly_delivered_revenue+=price
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
                    totals['research_campaigns']+=1;totals['research_operating_funded']+=operating_funded;totals['research_seed_funded']+=seed_funded;attempted.update((name,epoch['version']) for name in proposal['components']);totals['alpha_candidates']+=1;total_tokens=sum(source[f'{m}_{k}'] for m in ('astra','terra') for k in ('input','output'))*quantity
                    campaign=Campaign(action,month,proposal['components'],source['resource_minutes']*quantity,total_tokens,source['resource_minutes']*quantity,total_tokens,bill,seed_funded,operating_funded,proposal['expected_incremental_terminal_cash'],identifier=f'{action}:world{world}:{epoch["version"]}:month{month}',beta_version=epoch['version'])
                    events.append({'kind':'research_purchase','month':month,**proposal,'seed_funded':seed_funded,'operating_funded':operating_funded,'cash_after':cash,'known_future_refunds_before':known_refunds,'unpaid_obligations_before':unpaid_fixed+unpaid_refund,'available_operating_after_reserve_before':available_operating,'source_budget':source['derived_budget_usd'],'quantity_multiplier':quantity});row['research_action']=action
            minutes+=reserved_research['minutes'];tokens+=reserved_research['tokens'];container_minutes+=reserved_research['container_minutes']
            if campaign:
                capminutes=min(minutes,o['monthly_workbench_minutes']*o['research_fraction_limit']);captokens=min(tokens,o['monthly_token_quota']*o['research_fraction_limit']);source=register['investment_campaigns'][campaign.action];container_total=source['container_sessions_16gb']*20*sc['activity_quantity_multiplier'];remaining_fraction=campaign.remaining_minutes/campaign.total_minutes
                fraction=min(remaining_fraction,capminutes/campaign.total_minutes,captokens/campaign.total_tokens,container_minutes/container_total)
                if fraction>0:
                    activity_plan={'usd':0.,'minutes':campaign.total_minutes*fraction,'tokens':campaign.total_tokens*fraction,'container_minutes':container_total*fraction};execute(activity_plan,'investment_cost',True);campaign.remaining_minutes-=activity_plan['minutes'];campaign.remaining_tokens-=activity_plan['tokens'];campaign.consumed_minutes+=activity_plan['minutes'];campaign.consumed_tokens+=activity_plan['tokens']
                row['research_progress_fraction']=1-campaign.remaining_minutes/campaign.total_minutes
                if campaign.remaining_minutes<1e-6 and campaign.remaining_tokens<1e-6:
                    names=campaign.components;truth={};transfers={}
                    for name in names:
                        ac=c['assets'][name];r=rng(seed,world,800+ac['bit'],beta_epoch(c,campaign.starts)['month']);truth[name]=bool(r.random()<sc['asset_build_success']);transfers[name]=r.random(c['scope']['recipient_agents'])<sc['transfer_success'];transfers[name][creator]=True
                    identifier=campaign.identifier;observations,costs,forecast,evidence,estimate,transfer_estimate=alpha_assessment_inputs(c,sc,table,belief,assets,names,truth,seed,world,month,identifier,campaign.bill,policy)
                    domains=sorted(set(d for name in names for d in c['assets'][name]['domains']));candidate={'id':identifier,'version':'1','creator':member_names[creator],'scope':[c['scope']['domain_names'][d] for d in domains],'components':names,'dependencies':[],'shareable':not c['_private'],'sanitized':True,'valid_until':month+1+min(c['assets'][name]['lifetime_months'] for name in names),'capsule_commitment':sha({'id':identifier,'components':names,'synthetic_scope':domains}),'model_config':{'producer':'gpt-6-astra','execution':'gpt-6.1-terra','reasoning_mode':'pro','version_basis':'rolling aliases observed 2026-10-26; future Beta epochs are assumptions'}}
                    result=create_assessed_record(lifecycle,candidate,evidence,observations,costs,forecast,actors,month);admitted=result['admitted'];record=result['record'];assessment=(record or {}).get('assessment')
                    nodes[identifier]={'components':names,'truth':truth,'bill':campaign.bill,'ready':month+1,'last_assessment':month,'ever_admitted':admitted,'retired':False,'initial_assessment':assessment,'research_seed_funded':campaign.seed_funded,'research_operating_funded':campaign.operating_funded}
                    totals['alpha_admissions']+=int(admitted);totals['alpha_rejections']+=int(not admitted)
                    if admitted:totals['new_admitted_expected_alpha']+=max(0,assessment['expected_prospective_net_alpha'])
                    for name in names:
                        ac=c['assets'][name];graph=make_simulated_record(name,world,month+1,ac['lifetime_months'],ac['domains'],admitted);catalog[name]=graph;check=inspect_graph(graph,month+1,catalog);component_admitted=admitted and check['admitted'];assets[name]=Asset(name,month+1,truth[name],estimate[name],transfer_estimate,transfers[name],graph,active=component_admitted,acquisition_done={creator},lifecycle_id=identifier,creator=creator,beta_version=epoch['version']);totals['research_admissions']+=int(component_admitted)
                    events.append({'kind':'alpha_assessment','id':identifier,'month':month,'ready_month':month+1,'campaign':campaign.action,'components':names,'admitted':bool(admitted),'assessment':assessment,'costs':costs,'forecast':forecast,'evidence':evidence,'lifecycle_stage_results':result['stages'],'latent_component_truth_for_analysis_only':truth,'sharing_mode':'private' if c['_private'] else 'authenticated_network','beta_version':epoch['version']})
                    events.append({'kind':'research_complete','id':identifier,'action':campaign.action,'month':month,'actual_build_months':month-campaign.starts+1,'paid_cost':campaign.bill,'consumed_minutes':campaign.consumed_minutes,'consumed_tokens':campaign.consumed_tokens});campaign=None
            row['active_assets']=','.join(n for n,a in assets.items() if a.active and month>=a.ready)
        else:
            totals['expired_orders']+=len(queue);queue=[]
        for key in resource_keys:row[key]=totals[key]-resources_before[key]
        for suffix,limit in [('tokens','capacity_tokens'),('workbench_minutes','capacity_workbench_minutes'),('container_minutes','capacity_container_minutes')]:assert row['delivery_'+suffix]+row['research_'+suffix]<=row[limit]+1e-5
        current_records=lifecycle.records;eligible_records=[r for r in current_records.values() if r['status']=='ADMITTED' and month<r['valid_until'] and month<(r.get('evidence') or {}).get('observed_month',-100)+lpolicy['evidence_max_age']]
        row['alpha_eligible_records']=len(eligible_records);row['alpha_expected_inventory_value']=sum(max(0,(r.get('assessment') or {}).get('expected_prospective_net_alpha',0.)) for r in eligible_records);row['alpha_retired_records']=sum(r['status']=='RETIRED' for r in current_records.values());row['alpha_rejected_records']=sum(r['status']=='REJECTED' for r in current_records.values());row['active_recipient_count']=len(recipient_user_ids)
        row['pending_recovery_tasks']=len(recovery_backlog)
        row['closing_cash']=cash;row['unpaid_obligations']=unpaid_fixed+unpaid_refund;row['outstanding_receivables']=sum(sum(x) for x in invoices.values());row['known_future_refunds']=sum(sum(x) for x in refunds.values());row['queue_projects']=len(queue);row['available_uncommitted_cash']=max(0,cash-row['reserve']-row['unpaid_obligations']);row['retained_operating_cash_above_seed']=max(0,cash-c['seed_cash']-row['reserve']-row['unpaid_obligations']);row['belief_weights_after']=belief.weights.tolist()
        assert cash>=-1e-7
        assert abs(row['opening_cash']+row['collections']-row['operating_outflow']-row['investment_outflow']-row['refund_outflow']-row['arrears_outflow']-cash)<1e-5
        ledgers.append(row)
    assert not invoices and not refunds and not incident_notices and not recovery_backlog
    unpaid=unpaid_fixed+unpaid_refund;profit=cash-c['seed_cash']-unpaid
    cost_keys=['qualification_cost','unsupported_intake_cost','production_cost','correction_cost','recovery_cost','storage_cost','fixed_cost','investment_cost','maintenance_cost','revalidation_cost','recipient_acquisition_cost','payment_fees','discovery_cost','setup_fixed_cost','arrears_paid','network_access_cost','network_distribution_cost','network_composition_cost','beta_reevaluation_cost','revocation_cost']
    full_cost=sum(totals.get(k,0.) for k in cost_keys)+unpaid;direct=sum(totals[k] for k in ['production_cost','correction_cost','recovery_cost','storage_cost','recipient_acquisition_cost','network_access_cost','network_distribution_cost','network_composition_cost']);accepted=totals['true_accepted_projects'];passed=totals['validated_deliveries']
    assert abs(profit-(totals['collections']-totals['refunds']-full_cost))<1e-4
    metrics={**totals,'net_profit':profit,'quality_adjusted_profit':profit-totals['undetected_paid_false_pass_revenue'],'closing_cash':cash,'unpaid_obligations':unpaid,'insolvent':bool(stopped),'fully_allocated_cost_total':full_cost,'direct_cost_total':direct,'fully_allocated_cost_per_true_project':full_cost/accepted if accepted else None,'direct_cost_per_true_project':direct/accepted if accepted else None,'material_error_fraction':totals['false_passes']/passed if passed else 0.,'mean_price_fraction':float(np.mean(price_history)) if price_history else None,'total_calendar_months_including_setup_runoff':c['months']+c['runoff_months']+setup_months,'setup_months':setup_months,'setup_tokens':discovery['tokens'],'setup_workbench_minutes':discovery['minutes'],'world_arrival_multiplier':demand,'R_active_or_used':bool('R' in assets and assets['R'].uses>0),'V_active_or_used':bool('V' in assets and assets['V'].uses>0),'campaign_unfinished_at_horizon':bool(campaign),'transfer_trials':transfer_trials,'transfer_successes':transfer_successes}
    metrics.update(offered_price_mean=totals['offered_price_total']/totals['offered_projects'] if totals['offered_projects'] else None,delivered_price_mean=totals['delivered_price_total']/passed if passed else None,alpha_expected_inventory_value=ledgers[c['months']-1]['alpha_expected_inventory_value'],alpha_eligible_records=ledgers[c['months']-1]['alpha_eligible_records'],distinct_recipient_users=len(recipient_user_ids),distinct_completed_domains=len(completed_domains),unique_true_projects=len(true_project_ids),graph_overhead_total=sum(totals[k] for k in ['network_access_cost','network_distribution_cost','network_composition_cost','beta_reevaluation_cost','revocation_cost']),total_research_graph_upkeep_cost=sum(totals[k] for k in ['investment_cost','maintenance_cost','revalidation_cost','network_access_cost','network_distribution_cost','network_composition_cost','beta_reevaluation_cost','revocation_cost','recipient_acquisition_cost']))
    return Result(world,scenario,policy,metrics,ledgers,events,catalog,{'weights':belief.weights.tolist(),'arrival_mean':belief.arrival_shape/belief.arrival_rate,'observation_scope':market['observed_choice']},lifecycle={'records':lifecycle.records,'events':lifecycle.events,'policy':lpolicy,'authority_registry':registry,'basis':'SIMULATED_IDENTITY_AUTHORITY_AND_ECONOMIC_ASSESSMENT'},project_sets={'true':sorted(true_project_ids),'rich_true':sorted(rich_project_ids),'capacity_deferred':sorted(capacity_project_ids)})

def paired(beta,private,network,fixed):
    incremental=network.metrics['net_profit']-beta.metrics['net_profit'];quality_incremental=network.metrics['quality_adjusted_profit']-beta.metrics['quality_adjusted_profit'];invested=network.metrics['investment_cost']>0;used=network.metrics['R_uses']+network.metrics['V_uses']>0
    return {'network_incremental_profit':incremental,'private_incremental_profit':private.metrics['net_profit']-beta.metrics['net_profit'],'sharing_incremental_profit':network.metrics['net_profit']-private.metrics['net_profit'],'network_quality_adjusted_incremental_profit':quality_incremental,'price_policy_total_effect':network.metrics['net_profit']-fixed.metrics['net_profit'],'network_incremental_true_projects':network.metrics['true_accepted_projects']-beta.metrics['true_accepted_projects'],'network_incremental_rich_projects':network.metrics['rich_true_projects']-beta.metrics['rich_true_projects'],'capacity_unblocked_projects':len(set(network.project_sets['true'])&set(beta.project_sets['capacity_deferred'])-set(beta.project_sets['true'])),'research_repaid':bool(invested and used and incremental>0),'quality_adjusted_research_repaid':bool(invested and used and quality_incremental>0),'operating_only_research':bool(invested and network.metrics['research_seed_funded']==0),'positive_beta_delivery':bool(beta.metrics['net_profit']>0),'positive_network_advantage':bool(invested and used and incremental>0),'positive_sharing_advantage':bool(used and network.metrics['net_profit']>private.metrics['net_profit'])}


def summarize(results,comparisons):
    out={'worlds':len(comparisons),'policies':{},'paired':{}}
    for policy in POLICIES:
        rr=[r for r in results if r.policy==policy];ms=[r.metrics for r in rr];p={}
        for key in ['net_profit','quality_adjusted_profit','true_accepted_projects','false_passes','material_error_fraction','mean_price_fraction','fully_allocated_cost_per_true_project','direct_cost_per_true_project','investment_cost','research_seed_funded','research_operating_funded','R_uses','V_uses','capacity_blocked','cash_blocked','expired_orders','offered_price_mean','delivered_price_mean','alpha_candidates','alpha_admissions','alpha_rejections','alpha_reassessments','alpha_retirements','alpha_inventory_erosion','new_admitted_expected_alpha','alpha_expected_inventory_value','alpha_eligible_records','recipient_adoptions','distinct_recipient_users','distinct_completed_domains','unique_true_projects','rich_true_projects','graph_overhead_total','total_research_graph_upkeep_cost']:
            values=[m[key] for m in ms if m[key] is not None and (key!='material_error_fraction' or m['validated_deliveries']>0)];p[key]=stats(values) if values else None
        accepted=sum(m['true_accepted_projects'] for m in ms);p['pooled_fully_allocated_cost_per_true_project']=sum(m['fully_allocated_cost_total'] for m in ms)/accepted if accepted else None;p['pooled_direct_cost_per_true_project']=sum(m['direct_cost_total'] for m in ms)/accepted if accepted else None;p['aggregate_true_projects']=accepted
        for name,test in [('probability_profit',lambda m:m['net_profit']>0),('probability_quality_adjusted_profit',lambda m:m['quality_adjusted_profit']>0),('probability_insolvency',lambda m:m['insolvent']),('probability_research',lambda m:m['investment_cost']>0),('probability_seed_funded_research',lambda m:m['research_seed_funded']>0),('probability_unfinished_campaign',lambda m:m['campaign_unfinished_at_horizon'])]:p[name]=sum(bool(test(m)) for m in ms)/len(ms)
        total_delivered=sum(m['validated_deliveries'] for m in ms);p['pooled_material_error_fraction']=sum(m['false_passes'] for m in ms)/total_delivered if total_delivered else None;p['zero_delivery_worlds']=sum(m['validated_deliveries']==0 for m in ms)
        p['zero_output_worlds']=sum(m['true_accepted_projects']==0 for m in ms);p['ratio_distribution_note']='Per-world cost ratios condition on positive output; pooled cost includes every world and zero-output costs.';out['policies'][policy]=p
    for key in ['network_incremental_profit','private_incremental_profit','sharing_incremental_profit','network_quality_adjusted_incremental_profit','price_policy_total_effect','network_incremental_true_projects','network_incremental_rich_projects','capacity_unblocked_projects']:out['paired'][key]=stats([r[key] for r in comparisons])
    for key in ['research_repaid','quality_adjusted_research_repaid','operating_only_research','positive_beta_delivery','positive_network_advantage','positive_sharing_advantage']:out['paired'][f'probability_{key}']=sum(r[key] for r in comparisons)/len(comparisons)
    return out


def run_scenario(c,register,scenario,worlds,seed,output=None,structural_off=False):
    results=[];comparisons=[]
    for world in range(worlds):
        shared=initial_primitives(c,c['scenarios'][scenario],seed,world);triplet=[simulate(c,register,scenario,world,p,seed,shared,structural_off) for p in POLICIES];results.extend(triplet);comparisons.append(paired(*triplet))
    summary=summarize(results,comparisons);summary['scenario']=scenario;summary['seed']=seed;summary['sampling_unit']=c['scope']['sampling_unit']
    if output:
        out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=True)
        with gzip.open(out/f'{scenario}_complete_records.jsonl.gz','wt') as f:
            for r in results:f.write(dumps({'world':r.world,'scenario':r.scenario,'policy':r.policy,'metrics':r.metrics,'ledger':r.ledger,'events':r.events,'graph_records':r.graph_records,'belief':r.belief,'lifecycle':r.lifecycle,'project_sets':r.project_sets})+'\n')
        write_csv(out/f'{scenario}_worlds.csv',[{'world':r.world,'scenario':r.scenario,'policy':r.policy,**r.metrics,**(comparisons[r.world] if r.policy=='optimized_network' else {})} for r in results])
        rep=min((r for r in results if r.policy=='optimized_network'),key=lambda r:abs(r.metrics['net_profit']-summary['policies']['optimized_network']['net_profit']['median']));summary['illustrative_world']=rep.world
        for r in results:
            if r.world==rep.world:
                (out/f'{scenario}_illustrative_{r.policy}.json').write_text(dumps({'world':r.world,'metrics':r.metrics,'ledger':r.ledger,'events':r.events,'belief':r.belief,'lifecycle':r.lifecycle,'project_sets':r.project_sets},indent=2))
                write_csv(out/f'{scenario}_illustrative_{r.policy}_ledger.csv',[{k:v for k,v in row.items() if k not in ('price_curve','belief_weights_before','belief_weights_after')} for row in r.ledger])
        (out/f'{scenario}_summary.json').write_text(json.dumps(summary,indent=2))
    return summary


def load_inputs(config_path):
    c=json.loads(pathlib.Path(config_path).read_text());register=json.loads((HERE/c['cost_register']).resolve().read_text());return c,register

def freeze(config_path,out):
    c,register=load_inputs(config_path);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    closure={str(p.relative_to(HERE.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list(HERE.glob('*.py'))+[HERE/'config_v2.json',(HERE/c['cost_register']).resolve()]}
    protocol=HERE/'PROTOCOL_v2.md'
    if protocol.exists():closure[str(protocol.relative_to(HERE.parent))]=hashlib.sha256(protocol.read_bytes()).hexdigest()
    record={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'study_id':c['study_id'],'configuration_sha256':sha(c),'workflow_costs_sha256':sha(register),'closure_sha256':closure,'train_seed':c['train_seed'],'test_seed':c['test_seed'],'policy_names':POLICIES,'primary_scenarios':list(c['scenarios']),'status':'Freeze before independent confirmation worlds; development outputs remain separately labeled.'}
    (out/'frozen_config.json').write_text(json.dumps(c,indent=2));(out/'frozen_workflow_costs.json').write_text(json.dumps(register,indent=2));(out/'freeze.json').write_text(json.dumps(record,indent=2));return record

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(HERE/'config_v2.json'));p.add_argument('--output',default=str(HERE.parent/'results/beyond_beta_pilot'));p.add_argument('--worlds',type=int,default=20);p.add_argument('--scenarios',nargs='+',default=['conservative','central','favorable']);p.add_argument('--phase',choices=['train','confirm'],default='train');p.add_argument('--freeze',action='store_true');p.add_argument('--structural-off',action='store_true');a=p.parse_args();c,register=load_inputs(a.config);out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if a.freeze:print(json.dumps(freeze(a.config,out),indent=2));return
    if a.phase=='confirm':
        f=json.loads((out/'freeze.json').read_text());assert f['configuration_sha256']==sha(c);assert f['workflow_costs_sha256']==sha(register)
        for path,h in f['closure_sha256'].items():assert hashlib.sha256((HERE.parent/path).read_bytes()).hexdigest()==h,f'Changed frozen file: {path}'
    seed=c['train_seed'] if a.phase=='train' else c['test_seed'];summaries={}
    for scenario in a.scenarios:
        summary=run_scenario(c,register,scenario,a.worlds,seed,out,a.structural_off);summaries[scenario]=summary
        print(json.dumps({'scenario':scenario,'worlds':a.worlds,'profit':summary['policies']['optimized_network']['net_profit'],'research_probability':summary['policies']['optimized_network']['probability_research'],'incremental':summary['paired']['network_incremental_profit']}),flush=True)
    result={'status':'Frozen independent confirmation' if a.phase=='confirm' else 'EXPLORATORY DEVELOPMENT PILOT','config_sha256':sha(c),'workflow_costs_sha256':sha(register),'seed':seed,'worlds_per_scenario':a.worlds,'scenarios':summaries,'sampling_unit':c['scope']['sampling_unit']};(out/'summary.json').write_text(json.dumps(result,indent=2));(out/'run_manifest.json').write_text(json.dumps({'completed_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'numpy':np.__version__,'seed':seed,'worlds':a.worlds,'phase':a.phase},indent=2))

if __name__=='__main__':main()
