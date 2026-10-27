"""Independent synthetic cases and exhaustive oracle, authored before engineer freeze.

The oracle covers the restricted, explicitly generated four-worker/two-child
family. It does not claim to solve every possible instrument input.
"""
from copy import deepcopy
from itertools import product
import random

CATEGORIES = ['primary_care', 'backup_standby', 'backup_activation_reserve', 'worker_compensation', 'coordination_fee']

def make_case(seed):
    rng = random.Random(seed)
    start = 390 + rng.randrange(31)
    duration = 180 + rng.randrange(31)
    gap = 70
    shifts = [dict(id='S0', start_minute=start, end_minute=start+duration),
              dict(id='S1', start_minute=start+duration+gap, end_minute=start+2*duration+gap)]
    workers = []
    for e in range(2):
        for j in range(2):
            current = 'S'+str((e+j)%2)
            permit = ['S0','S1'] if rng.random() > .22 else [current]
            workers.append(dict(id=f'W{e}{j}', employer_id=f'E{e}', current_shift_id=current,
                permitted_shift_ids=permit,
                change_compensation_cents={s['id']:(0 if s['id']==current else rng.randrange(100,1001)) for s in shifts}))
    children = []
    for e in range(2):
        children.append(dict(id=f'C{e}', parent_worker_id=f'W{e}0', acceptable_location_ids=['LP','LB'],
            commute_minutes_by_location={loc:dict(before=rng.randrange(10,31),after=rng.randrange(10,31)) for loc in ['LP','LB']}))
    staff=[]; offers=[]
    for role,pid,loc,prefix in [('primary','P','LP','P'),('backup','B','LB','B')]:
        for i,s in enumerate(shifts):
            window=[s['start_minute']-35,s['end_minute']+35]
            sid=f'{prefix}_staff_{i}'
            staff.append(dict(id=sid,qualification_tags=['Q'],available_windows=[window],
                max_active_minutes=window[1]-window[0],max_reserved_minutes=window[1]-window[0]))
            offers.append(dict(id=f'{prefix}{i}',provider_id=pid,location_id=loc,role=role,window=window,
                staff_ids=[sid],minimum_qualified_staff=1,required_qualification_tags=['Q'],
                declared_child_capacity=2,commitment_required=True,
                fixed_opening_cost_cents=rng.randrange(7000,14001),per_child_cost_cents=rng.randrange(300,1001),
                standby_retainer_cents=(rng.randrange(700,1701) if role=='backup' else 0)))
    return dict(schema='agi-alpha.e1-case.v1',case_id=f'audit_fresh_{seed}',synthetic=True,currency='USD',
        horizon=dict(operating_days=1,start_minute=0,end_minute=1440,
            scenario_semantics='Exactly one mutually exclusive preannounced whole-day world.',maximum_backup_event_worlds_realized=1),
        shifts=shifts,employers=[dict(id=f'E{e}',staffing_quotas={'S0':1,'S1':1}) for e in range(2)],
        workers=workers,children=children,providers=[dict(id=p,declared_offer_acceptance=True) for p in ['P','B']],
        locations=[dict(id=l,opening_windows=[[0,1440]],declared_concurrent_child_capacity=2) for l in ['LP','LB']],
        staff=staff,offers=offers,
        scenarios=[dict(id='normal',announced_minute=0,failed_provider_ids=[],failed_staff_ids=[],closed_location_ids=[]),
                   dict(id='primary_absent',announced_minute=0,failed_provider_ids=['P'],failed_staff_ids=[],closed_location_ids=[]),
                   dict(id='backup_absent',announced_minute=0,failed_provider_ids=['B'],failed_staff_ids=[],closed_location_ids=[])],
        payers=[dict(id='joint_sponsor',kind='employer',beneficiary_worker_ids=[w['id'] for w in workers],
            payment_ceiling_cents=rng.randrange(18000,65001),allowed_cost_categories=CATEGORIES[:])],
        coordinator_fee_cents=rng.randrange(1000,2501),
        limits=dict(maximum_workers=12,maximum_children=8,maximum_offers=8,maximum_scenarios=6,maximum_search_states=500000),
        disclosures=['Independently generated synthetic audit case; no actual consent, price or legal qualification is asserted.'])

def overlaps(a,b):
    return max(a[0],b[0]) < min(a[1],b[1])

def contains(outer,inner):
    return outer[0]<=inner[0] and inner[1]<=outer[1]

def own_oracle(case, fixed_roster=False):
    """Exhaustive oracle for generated cases with one unrestricted joint payer.

    Deliberately independent of the engineer's module and verifier. It enumerates
    every consented exact-quota roster, every normal primary assignment, and
    every admissible original-primary/backup route in every finite world.
    """
    assert len(case['payers']) == 1 and set(case['payers'][0]['allowed_cost_categories'])==set(CATEGORIES)
    assert set(case['payers'][0]['beneficiary_worker_ids'])=={w['id'] for w in case['workers']}
    workers={x['id']:x for x in case['workers']}; shifts={x['id']:x for x in case['shifts']}
    children={x['id']:x for x in case['children']}; providers={x['id']:x for x in case['providers']}
    locations={x['id']:x for x in case['locations']}; staff={x['id']:x for x in case['staff']}
    offers={x['id']:x for x in case['offers']}
    worlds=case['scenarios']; normal=next(x for x in worlds if x['id']=='normal')
    cids=list(children); best=None; best_unfunded=None; enumerated=0

    def interval(cid,oid,roster):
        ch=children[cid]; sh=shifts[roster[ch['parent_worker_id']]]
        travel=ch['commute_minutes_by_location'][offers[oid]['location_id']]
        return [sh['start_minute']-travel['before'],sh['end_minute']+travel['after']]

    def usable(cid,oid,roster,world):
        ch=children[cid]; off=offers[oid]; loc=locations[off['location_id']]
        if off['location_id'] not in ch['acceptable_location_ids']: return False
        if providers[off['provider_id']]['declared_offer_acceptance'] is not True: return False
        if off['provider_id'] in world['failed_provider_ids'] or off['location_id'] in world['closed_location_ids']: return False
        need=interval(cid,oid,roster)
        if need[0]<0 or need[1]>1440 or not contains(off['window'],need): return False
        if world['announced_minute']>need[0]: return False
        if not any(contains(x,off['window']) for x in loc['opening_windows']): return False
        qualified=0
        for sid in off['staff_ids']:
            st=staff[sid]
            if sid in world['failed_staff_ids']: continue
            if not any(contains(x,off['window']) for x in st['available_windows']): continue
            if set(off['required_qualification_tags'])<=set(st['qualification_tags']): qualified+=1
        return qualified>=off['minimum_qualified_staff']

    def routes_ok(route,roster,world):
        if set(route)!=set(cids): return False
        if not all(usable(cid,oid,roster,world) for cid,oid in route.items()): return False
        active=set(route.values())
        for oid in active:
            points=sorted({t for c,o in route.items() if o==oid for t in interval(c,o,roster)})
            for a,b in zip(points,points[1:]):
                n=sum(1 for c,o in route.items() if o==oid and interval(c,o,roster)[0]<=a and b<=interval(c,o,roster)[1])
                if n>offers[oid]['declared_child_capacity']: return False
        for lid,loc in locations.items():
            relevant=[(c,o) for c,o in route.items() if offers[o]['location_id']==lid]
            points=sorted({t for c,o in relevant for t in interval(c,o,roster)})
            for a,b in zip(points,points[1:]):
                if sum(1 for c,o in relevant if interval(c,o,roster)[0]<=a and b<=interval(c,o,roster)[1])>loc['declared_concurrent_child_capacity']:return False
        for sid,st in staff.items():
            commitments=[offers[o]['window'] for o in active if sid in offers[o]['staff_ids']]
            if any(overlaps(x,y) for i,x in enumerate(commitments) for y in commitments[i+1:]):return False
            if sum(x[1]-x[0] for x in commitments)>st['max_active_minutes']:return False
        return True

    options=[[w['current_shift_id']] if fixed_roster else w['permitted_shift_ids'] for w in workers.values()]
    for values in product(*options):
        roster=dict(zip(workers,values))
        if any(roster[w] not in workers[w]['permitted_shift_ids'] for w in workers):continue
        if any(sum(1 for w in workers if workers[w]['employer_id']==e['id'] and roster[w]==sid)!=q for e in case['employers'] for sid,q in e['staffing_quotas'].items()):continue
        prim_opts=[[o for o in offers if offers[o]['role']=='primary' and usable(c,o,roster,normal)] for c in cids]
        for prim_values in product(*prim_opts):
            primary=dict(zip(cids,prim_values))
            if not routes_ok(primary,roster,normal):continue
            alternatives=[]
            for world in worlds:
                if world['id']=='normal':
                    alternatives.append([primary]); continue
                choices=[[o for o in offers if (o==primary[c] or offers[o]['role']=='backup') and usable(c,o,roster,world)] for c in cids]
                valid=[]
                for vals in product(*choices):
                    route=dict(zip(cids,vals))
                    if routes_ok(route,roster,world):valid.append(route)
                alternatives.append(valid)
            for routes in product(*alternatives):
                enumerated+=1
                selected=set(primary.values())|{o for rr in routes for o in rr.values() if offers[o]['role']=='backup'}
                if any(sum(offers[o]['window'][1]-offers[o]['window'][0] for o in selected if sid in offers[o]['staff_ids'])>st['max_reserved_minutes'] for sid,st in staff.items()):continue
                pcost=sum(offers[o]['fixed_opening_cost_cents']+sum(offers[o]['per_child_cost_cents'] for c,z in primary.items() if z==o) for o in set(primary.values()))
                backup={o for o in selected if offers[o]['role']=='backup'}
                standby=sum(offers[o]['standby_retainer_cents'] for o in backup)
                activation=max(sum(offers[o]['fixed_opening_cost_cents']+sum(offers[o]['per_child_cost_cents'] for c,z in rr.items() if z==o) for o in set(rr.values()) if offers[o]['role']=='backup') for rr in routes)
                compensation=sum(workers[w]['change_compensation_cents'][roster[w]] for w in workers)
                cost=pcost+standby+activation+compensation+case['coordinator_fee_cents']
                record=dict(cost_cents=cost,roster=roster,primary=primary,
                    worlds={world['id']:rr for world,rr in zip(worlds,routes)},
                    category_totals=dict(zip(CATEGORIES,[pcost,standby,activation,compensation,case['coordinator_fee_cents']])))
                if best_unfunded is None or cost<best_unfunded['cost_cents']:best_unfunded=deepcopy(record)
                if cost<=case['payers'][0]['payment_ceiling_cents'] and (best is None or cost<best['cost_cents']):best=deepcopy(record)
    return dict(feasible=best is not None,best=best,best_before_budget=best_unfunded,complete_states=enumerated)

def fresh_cases():
    # These seeds were selected by the auditor before seeing the engineer source.
    return [make_case(784103+i*7919) for i in range(48)]

def semantic_cases():
    base=make_case(910271)
    base['payers'][0]['payment_ceiling_cents']=200000
    result=[]
    def emit(label, mutate):
        c=deepcopy(base);c['case_id']='audit_semantic_'+label;mutate(c);result.append((label,c))
    emit('feasible_reference',lambda c:None)
    emit('both_providers_fail',lambda c:c['scenarios'].append(dict(id='common_outage',announced_minute=0,failed_provider_ids=['P','B'],failed_staff_ids=[],closed_location_ids=[])))
    emit('backup_provider_declines',lambda c:c['providers'][1].update(declared_offer_acceptance=False))
    emit('parent_disallows_backup_location',lambda c:c['children'][0].update(acceptable_location_ids=['LP']))
    emit('backup_unqualified',lambda c:[s.update(qualification_tags=[]) for s in c['staff'] if s['id'].startswith('B')])
    emit('backup_site_closed',lambda c:c['scenarios'].append(dict(id='primary_and_backup_site',announced_minute=0,failed_provider_ids=['P'],failed_staff_ids=[],closed_location_ids=['LB'])))
    emit('backup_capacity_zero',lambda c:[o.update(declared_child_capacity=0) for o in c['offers'] if o['role']=='backup'])
    emit('backup_staff_hours_short',lambda c:[s.update(max_active_minutes=1) for s in c['staff'] if s['id'].startswith('B')])
    emit('backup_reservations_short',lambda c:[s.update(max_reserved_minutes=1) for s in c['staff'] if s['id'].startswith('B')])
    emit('unfunded',lambda c:c['payers'][0].update(payment_ceiling_cents=0))
    emit('no_consent',lambda c:c['workers'][0].update(permitted_shift_ids=[]))
    emit('outage_too_late',lambda c:c['scenarios'][1].update(announced_minute=1439))
    emit('primary_intervals_too_short',lambda c:[o.update(window=[o['window'][0]+50,o['window'][1]-50]) for o in c['offers'] if o['role']=='primary'])
    return result

if __name__=='__main__':
    cases=fresh_cases()
    answers=[own_oracle(c) for c in cases]
    print({'fresh_count':len(cases),'feasible':sum(x['feasible'] for x in answers),
           'infeasible':sum(not x['feasible'] for x in answers)})
    print([(name,own_oracle(c)['feasible']) for name,c in semantic_cases()])
