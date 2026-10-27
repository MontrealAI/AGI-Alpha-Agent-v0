"""Post-selection audit by a separate agent. Does not edit engineer modules.

The fresh case oracle was preregistered before the solver was inspected. This
runner accepts an immutable source snapshot and preserves per-version evidence.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,sys,time
from collections import Counter,defaultdict
from pathlib import Path
from independent_audit_cases import fresh_cases,semantic_cases,make_case,own_oracle,CATEGORIES

BASE=Path(__file__).resolve().parents[1]

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def own_acceptance(case,package):
    """Reconstruct purposes with explicit minute occupancy and direct balances.

    Does not import or call either engineer module. It does not certify actual
    credentials, consent, licensing or legal enforceability.
    """
    errors=[]
    def need(x,message):
        if not x:errors.append(message)
    try:
        workers={x['id']:x for x in case['workers']};children={x['id']:x for x in case['children']}
        shifts={x['id']:x for x in case['shifts']};offers={x['id']:x for x in case['offers']}
        locations={x['id']:x for x in case['locations']};staff={x['id']:x for x in case['staff']}
        providers={x['id']:x for x in case['providers']};payers={x['id']:x for x in case['payers']}
        roster=package['worker_roster']; plans=package['scenario_assignments']
        need(set(roster)==set(workers),'roster completeness')
        for wid,w in workers.items():need(roster[wid] in w['permitted_shift_ids'],'individual shift consent '+wid)
        for employer in case['employers']:
            counts=Counter(roster[wid] for wid,w in workers.items() if w['employer_id']==employer['id'])
            need(all(counts[sid]==q for sid,q in employer['staffing_quotas'].items()),'employer coverage '+employer['id'])
        need(set(plans)=={x['id'] for x in case['scenarios']},'scenario completeness')
        normal=plans['normal']; prim_groups=defaultdict(list);backup_groups=defaultdict(set);activations={}
        for cid,oid in normal.items():
            need(offers[oid]['role']=='primary','normal primary role')
            prim_groups[oid].append(cid)
        for world in case['scenarios']:
            assignment=plans[world['id']];need(set(assignment)==set(children),'every child in '+world['id'])
            occupancy_offer=Counter();occupancy_site=Counter();active=set(assignment.values());active_backup=defaultdict(list)
            for cid,ch in children.items():
                off=offers[assignment[cid]];loc=off['location_id'];sh=shifts[roster[ch['parent_worker_id']]]
                need(loc in ch['acceptable_location_ids'],'individual care-location consent '+cid)
                travel=ch['commute_minutes_by_location'][loc]
                start=sh['start_minute']-travel['before'];end=sh['end_minute']+travel['after']
                need(0<=start<end<=1440,'day bounds')
                need(off['window'][0]<=start and end<=off['window'][1],'full commute-inclusive care '+cid)
                if world['id']!='normal':need(world['announced_minute']<=start,'contingency notice')
                need(providers[off['provider_id']]['declared_offer_acceptance'] is True,'provider acceptance')
                need(off['provider_id'] not in world['failed_provider_ids'],'provider failure respected')
                need(loc not in world['closed_location_ids'],'location failure respected')
                need(not(set(off['staff_ids'])&set(world['failed_staff_ids'])),'staff failure respected')
                primary=offers[normal[cid]]
                healthy=primary['provider_id'] not in world['failed_provider_ids'] and primary['location_id'] not in world['closed_location_ids'] and not(set(primary['staff_ids'])&set(world['failed_staff_ids']))
                need(off['id']==primary['id'] if healthy else off['role']=='backup','permitted whole-interval routing')
                for minute in range(start,end):
                    occupancy_offer[(off['id'],minute)]+=1;occupancy_site[(loc,minute)]+=1
                if off['role']=='backup':
                    active_backup[off['id']].append(cid);backup_groups[off['id']].add(cid)
            need(all(n<=offers[oid]['declared_child_capacity'] for (oid,t),n in occupancy_offer.items()),'offer capacity')
            need(all(n<=locations[lid]['declared_concurrent_child_capacity'] for (lid,t),n in occupancy_site.items()),'site capacity')
            staff_time=Counter();staff_minutes=Counter()
            for oid in active:
                off=offers[oid];a,b=off['window'];loc=locations[off['location_id']]
                need(any(x<=a<b<=y for x,y in loc['opening_windows']),'provider opening window')
                qualified=0
                for sid in off['staff_ids']:
                    st=staff[sid];need(any(x<=a<b<=y for x,y in st['available_windows']),'staff availability')
                    qualified+=set(off['required_qualification_tags'])<=set(st['qualification_tags'])
                    for minute in range(a,b):staff_time[(sid,minute)]+=1
                    staff_minutes[sid]+=b-a
                need(len(off['staff_ids'])==len(set(off['staff_ids'])),'no duplicated credential')
                need(qualified>=off['minimum_qualified_staff'],'qualified staff minimum')
            need(all(n<=1 for n in staff_time.values()),'no concurrent staff reuse')
            need(all(n<=staff[sid]['max_active_minutes'] for sid,n in staff_minutes.items()),'staff work-minute limits')
            activations[world['id']]=sum(offers[oid]['fixed_opening_cost_cents']+len(cids)*offers[oid]['per_child_cost_cents'] for oid,cids in active_backup.items())
        standby_minutes=defaultdict(set)
        obligations={}
        def obligation(i,category,cents,beneficiaries):obligations[i]=(category,cents,set(beneficiaries))
        for oid,cids in prim_groups.items():
            off=offers[oid];obligation('primary:'+oid,'primary_care',off['fixed_opening_cost_cents']+len(cids)*off['per_child_cost_cents'],[children[c]['parent_worker_id'] for c in cids])
        for oid,cids in backup_groups.items():
            off=offers[oid];obligation('standby:'+oid,'backup_standby',off['standby_retainer_cents'],[children[c]['parent_worker_id'] for c in cids])
            for sid in off['staff_ids']:standby_minutes[sid].update(range(*off['window']))
        need(all(len(minutes)<=staff[sid]['max_reserved_minutes'] for sid,minutes in standby_minutes.items()),'finite standby commitment')
        reserve=max(activations.values())
        if reserve:obligation('backup_activation_reserve','backup_activation_reserve',reserve,[children[c]['parent_worker_id'] for cs in backup_groups.values() for c in cs])
        for wid,w in workers.items():
            cents=w['change_compensation_cents'][roster[wid]]
            if cents:obligation('worker:'+wid,'worker_compensation',cents,[wid])
        obligation('coordination_fee','coordination_fee',case['coordinator_fee_cents'],[x['parent_worker_id'] for x in children.values()])
        actual={x['id']:x for x in package['cost_items']};need(set(actual)==set(obligations),'complete funded obligations')
        for iid,(category,cents,beneficiaries) in obligations.items():
            item=actual[iid]
            need(item['category']==category and item['amount_cents']==cents and set(item['beneficiary_worker_ids'])==beneficiaries,'invoice reconstruction '+iid)
        paid_item=Counter();paid_payer=Counter()
        for row in package['payer_allocation']['entries']:
            category,cents,beneficiaries=obligations[row['item_id']];payer=payers[row['payer_id']];amount=row['amount_cents']
            need(type(amount) is int and amount>=0,'integer nonnegative payment')
            need(category in payer['allowed_cost_categories'],'payer category permission')
            need(bool(beneficiaries&set(payer['beneficiary_worker_ids'])),'payer beneficiary eligibility')
            paid_item[row['item_id']]+=amount;paid_payer[row['payer_id']]+=amount
        need(all(paid_item[i]==o[1] for i,o in obligations.items()),'every obligation fully funded')
        need(all(paid_payer[p]<=row['payment_ceiling_cents'] for p,row in payers.items()),'payer ceilings')
        need(package['maximum_funded_package_cents']==sum(o[1] for o in obligations.values()),'full package total')
        need(package['backup_obligation']['maximum_activation_reserve_cents']==reserve,'worst world fully reserved')
        need(package['coordinator_revenue_cents']==case['coordinator_fee_cents'],'pass-through not coordinator revenue')
    except Exception as exc:errors.append(type(exc).__name__+': '+str(exc))
    return {'accepted':not errors,'errors':errors,'method':'direct minute occupancy and independently reconstructed obligations'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--snapshot',required=True);parser.add_argument('--label',required=True)
    args=parser.parse_args();snapshot=Path(args.snapshot).resolve();sys.path.insert(0,str(snapshot))
    import e1_instrument as instrument
    import e1_verify as verifier
    out=BASE/'results';out.mkdir(exist_ok=True)
    start=time.time();report={'label':args.label,'snapshot':str(snapshot),'source_hashes':{n:hashlib.sha256((snapshot/n).read_bytes()).hexdigest() for n in ['e1_instrument.py','e1_verify.py']},'fresh':[],'semantic':[],'tamper':[],'metamorphic':[],'malformed_inputs':[],'witnesses':{}}
    def adapted(case):
        c=copy.deepcopy(case);c['currency']='CAD';return c
    cases=[adapted(c) for c in fresh_cases()]
    case_path=BASE/'technical/independent_audit/fresh_cases.json';case_path.parent.mkdir(parents=True,exist_ok=True)
    if not case_path.exists():case_path.write_text(json.dumps(cases,indent=2)+'\n')
    for case in cases:
        expected=own_oracle(case);fixed_expected=own_oracle(case,True)
        comparison=instrument.compare(case);joint=comparison['results']['combined'];ordinary=comparison['results']['ordinary_exact_same_formulation'];fixed=comparison['results']['fixed_roster_pooled_care']
        actual=joint['status']=='offered';expected_cost=expected['best']['cost_cents'] if expected['best'] else None
        actual_cost=joint['offer']['maximum_funded_package_cents'] if joint['offer'] else None
        oracle_fee=None
        if expected['best_before_budget']:
            base_cost=expected['best_before_budget']['cost_cents']-case['coordinator_fee_cents']
            if base_cost<=case['payers'][0]['payment_ceiling_cents']:oracle_fee=case['payers'][0]['payment_ceiling_cents']-base_cost
        checks={'feasibility':actual==expected['feasible'],'cost':actual_cost==expected_cost,
            'ordinary_parity':joint['status']==ordinary['status'] and ((not joint['offer'] and not ordinary['offer']) or (joint['offer']==ordinary['offer'])),
            'fixed_feasibility':(fixed['status']=='offered')==fixed_expected['feasible'],
            'fee_ceiling':joint['global_maximum_admissible_coordination_fee_cents']==oracle_fee,
            'without_commitments_refused':comparison['results']['flexible_without_opening_commitment']['status']=='refused'}
        independent=None
        if joint['offer']:
            independent=own_acceptance(case,joint['offer']);checks['independent_witness_acceptance']=independent['accepted']
            report['witnesses'][case['case_id']]=joint['offer']
        report['fresh'].append(dict(case_id=case['case_id'],expected_feasible=expected['feasible'],observed_status=joint['status'],expected_cost_cents=expected_cost,observed_cost_cents=actual_cost,checks=checks,independent=independent))
    for label,raw in semantic_cases():
        case=adapted(raw);expected=own_oracle(case)
        try:
            res=instrument.solve(case,'combined');observed=res['status'];ok=(observed=='offered')==expected['feasible'] and observed in ['offered','refused']
        except Exception as exc:observed=type(exc).__name__+': '+str(exc);ok=not expected['feasible']
        report['semantic'].append(dict(case_id=case['case_id'],expected_feasible=expected['feasible'],observed=observed,passed=ok))
    origin=json.loads((snapshot/'origin_case.json').read_text());original=instrument.compare(origin);offer=original['results']['combined']['offer']
    report['origin']={'statuses':{k:v['status'] for k,v in original['results'].items()},'package_cents':offer['maximum_funded_package_cents'],'independent_acceptance':own_acceptance(origin,offer),'ordinary_parity':original['same_formulation_exact_control']['identical_selected_result']}
    report['witnesses']['origin']=offer
    accepted_bad=[]
    def attack(label,mutate,scope='witness',rebind=False):
        c=copy.deepcopy(origin);o=copy.deepcopy(offer);mutate(c,o)
        if rebind:o['transformation_witness']['case_sha256']=digest(c)
        verdict=verifier.verify_offer(c,o)
        report['tamper'].append({'case_id':label,'scope':scope,'accepted':verdict['valid'],'errors':verdict['errors'][:8],'rebound_input_hash':rebind})
        if verdict['valid']:accepted_bad.append({'case_id':label,'input':c,'witness':o,'verdict':verdict})
    changed=next(w for w in origin['workers'] if offer['worker_roster'][w['id']]!=w['current_shift_id'])
    prim=next(x for x in origin['offers'] if x['id'] in offer['transformation_witness']['primary_opened_offer_ids'])
    backup=next(x for x in origin['offers'] if x['id'] in offer['backup_obligation']['backup_offer_ids'])
    outage=next(x for x in origin['scenarios'] if x['failed_provider_ids']==[prim['provider_id']])
    def update_row(collection,key,value,updates):
        next(x for x in collection if x[key]==value).update(updates)
    attack('individual_shift_consent',lambda c,o:update_row(c['workers'],'id',changed['id'],{'permitted_shift_ids':[changed['current_shift_id']]}),'input_constraint',True)
    attack('individual_care_location_consent',lambda c,o:c['children'][0].update(acceptable_location_ids=[backup['location_id']]),'input_constraint',True)
    attack('full_interval_shortened',lambda c,o:update_row(c['offers'],'id',prim['id'],{'window':[prim['window'][0]+1,prim['window'][1]-1]}),'input_constraint',True)
    attack('qualified_staff_removed',lambda c,o:update_row(c['staff'],'id',prim['staff_ids'][0],{'qualification_tags':[]}),'input_constraint',True)
    attack('physical_capacity_removed',lambda c,o:update_row(c['locations'],'id',prim['location_id'],{'declared_concurrent_child_capacity':0}),'input_constraint',True)
    attack('staff_active_limit_removed',lambda c,o:update_row(c['staff'],'id',prim['staff_ids'][0],{'max_active_minutes':0}),'input_constraint',True)
    attack('staff_standby_limit_removed',lambda c,o:update_row(c['staff'],'id',backup['staff_ids'][0],{'max_reserved_minutes':0}),'input_constraint',True)
    attack('provider_acceptance_withdrawn',lambda c,o:update_row(c['providers'],'id',prim['provider_id'],{'declared_offer_acceptance':False}),'input_constraint',True)
    attack('child_omitted',lambda c,o:o['worlds'][0]['child_care'].pop())
    attack('required_world_omitted',lambda c,o:o['scenario_assignments'].pop(outage['id']))
    attack('failed_provider_used',lambda c,o:o['scenario_assignments'][outage['id']].update({c['children'][0]['id']:prim['id']}))
    attack('payment_above_ceiling',lambda c,o:o['payer_allocation']['entries'][0].update(amount_cents=10**8))
    attack('unpaid_backup_reserve',lambda c,o:update_row(o['cost_items'],'id','backup_activation_reserve',{'amount_cents':0}))
    def forbidden_category(c,o):
        row=next(x for x in o['payer_allocation']['entries'] if x['item_id']=='coordination_fee');row['payer_id']=next(p['id'] for p in c['payers'] if 'coordination_fee' not in p['allowed_cost_categories'])
    attack('payer_forbidden_category',forbidden_category)
    attack('integer_payment_boolean',lambda c,o:o['payer_allocation']['entries'][0].update(amount_cents=True))
    attack('fee_ceiling_inflated',lambda c,o:o.update(maximum_admissible_coordinator_fee_cents=10**8))
    attack('actual_delivery_misrepresented',lambda c,o:o['useful_outcome'].update(actual_childcare_delivered=True))
    attack('input_binding_broken',lambda c,o:o['transformation_witness'].update(case_sha256='0'*64))
    attack('backup_offer_summary_erased',lambda c,o:o['backup_obligation'].update(backup_offer_ids=[]),'derived_contract_summary')
    attack('reserved_staff_summary_erased',lambda c,o:o['backup_obligation'].update(reserve_staff_minutes={}),'derived_contract_summary')
    attack('serialized_worker_permission_changed',lambda c,o:o['worker_schedule'][0].update(permitted_shift_ids=[]),'derived_contract_summary')
    attack('serialized_worker_employer_changed',lambda c,o:o['worker_schedule'][0].update(employer_id='invented_employer'),'derived_contract_summary')
    attack('unsupported_two_realized_worlds',lambda c,o:c['horizon'].update(maximum_backup_event_worlds_realized=2),'unsupported_input_domain',True)
    attack('unsupported_two_day_horizon',lambda c,o:c['horizon'].update(operating_days=2),'unsupported_input_domain',True)
    attack('synthetic_flag_removed',lambda c,o:c.update(synthetic=False),'unsupported_input_domain',True)
    attack('unsupported_currency',lambda c,o:c.update(currency='USD'),'unsupported_input_domain',True)
    # Uniform monetary scaling is a same-feasible-set metamorphic check.
    large=adapted(make_case(910271));large['payers'][0]['payment_ceiling_cents']=200000
    scale=10**9
    for w in large['workers']:w['change_compensation_cents']={k:v*scale for k,v in w['change_compensation_cents'].items()}
    for row in large['offers']:
        for k in ['fixed_opening_cost_cents','per_child_cost_cents','standby_retainer_cents']:row[k]*=scale
    for payer in large['payers']:payer['payment_ceiling_cents']*=scale
    large['coordinator_fee_cents']*=scale;large['case_id']='audit_uniform_large_integer_scaling'
    expected=own_oracle(large);observed=instrument.solve(large,'combined')
    report['metamorphic'].append(dict(case_id=large['case_id'],expected_feasible=expected['feasible'],expected_cost_cents=expected['best']['cost_cents'],observed_status=observed['status'],observed_cost_cents=observed['offer']['maximum_funded_package_cents'] if observed['offer'] else None,acceptance_check=observed.get('acceptance_check'),passed=observed['status']=='offered' and observed['offer']['maximum_funded_package_cents']==expected['best']['cost_cents']))
    # Constructor guards and the search boundary are checked separately.
    malformed=[('negative_fee',lambda c:c.update(coordinator_fee_cents=-1)),('boolean_payer_budget',lambda c:c['payers'][0].update(payment_ceiling_cents=True)),('duplicate_worker',lambda c:c['workers'].append(copy.deepcopy(c['workers'][0]))),('two_world_contract',lambda c:c['horizon'].update(maximum_backup_event_worlds_realized=2)),('real_case_not_synthetic',lambda c:c.update(synthetic=False))]
    for label,mutate in malformed:
        case=adapted(make_case(910271));mutate(case)
        try:res=instrument.solve(case,'combined');passed=False;result=res['status']
        except Exception as exc:passed=True;result=type(exc).__name__+': '+str(exc)
        report['malformed_inputs'].append(dict(case_id=label,passed=passed,result=result))
    limited=adapted(make_case(910271));limited['limits']['maximum_search_states']=1
    res=instrument.solve(limited,'combined');report['search_boundary']={'status':res['status'],'exhaustive':res['exhaustive_within_declared_bounds'],'passed':res['status']=='search_limit_not_a_refusal_proof' and res['offer'] is None and not res['exhaustive_within_declared_bounds']}
    report['summary']={'fresh_total':len(report['fresh']),'fresh_all_checks_pass':sum(all(x['checks'].values()) for x in report['fresh']),'fresh_feasible':sum(x['expected_feasible'] for x in report['fresh']),'semantic_total':len(report['semantic']),'semantic_pass':sum(x['passed'] for x in report['semantic']),'tamper_total':len(report['tamper']),'tamper_rejected':sum(not x['accepted'] for x in report['tamper']),'unexpected_acceptances':[x['case_id'] for x in report['tamper'] if x['accepted']],'metamorphic_pass':all(x['passed'] for x in report['metamorphic']),'elapsed_seconds':time.time()-start}
    report['schema_adjustment']='Only currency changed from USD to CAD at the runner boundary after engineer/root changed the frozen schema; original oracle source and expectations are currency-invariant.'
    dest=out/f'independent_audit_{args.label}_raw.json';dest.write_text(json.dumps(report,indent=2)+'\n')
    (BASE/f'technical/independent_audit/{args.label}_unexpected_acceptances.json').write_text(json.dumps(accepted_bad,indent=2)+'\n')
    print(json.dumps({'result_path':str(dest),'summary':report['summary']},indent=2))

if __name__=='__main__':main()
