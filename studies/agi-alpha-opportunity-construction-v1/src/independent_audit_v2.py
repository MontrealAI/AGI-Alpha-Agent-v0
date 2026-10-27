"""Independent post-freeze V2 confirmation; preserves all V1 evidence.

The original exhaustive oracle and minute-occupancy purpose checker are reused
unchanged. New case identities/parameters and tamper certificates are selected
only after the V2 source pins are final. Disclosed V1 inputs are regression only.
"""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
import random
import secrets
import sys
import time
from collections import Counter
from pathlib import Path

from independent_audit import own_acceptance
from independent_audit_cases import make_case, own_oracle, semantic_cases

BASE = Path(__file__).resolve().parents[1]
DIRECTORY = BASE / 'technical/independent_audit'
SNAPSHOT = DIRECTORY / 'v2_snapshot'
PINS = {
    'e1_instrument_v2.py': '4a57ec8f74c72c85c6209b4123692af5c95ac63ca15e856a3626bfdf5c3d1406',
    'e1_verify_v2.py': 'aa673747ebca69ea44d5ce70c251216705d103f39c4ae85c7e120d1be226cd51',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def fresh_case(seed, index):
    """New parameters and complete consistent renaming in the same small family."""
    rng = random.Random(seed ^ 0xBC19D462)
    case = make_case(seed)
    case['currency'] = 'CAD'
    case['case_id'] = f'v2_fresh_{index}_{seed:016x}'
    offset = rng.randrange(-90, 121)
    for shift in case['shifts']:
        shift['start_minute'] += offset
        shift['end_minute'] += offset
    for offer in case['offers']:
        offer['window'] = [x + offset for x in offer['window']]
    for person in case['staff']:
        person['available_windows'] = [[x + offset for x in w] for w in person['available_windows']]
    for child in case['children']:
        for commute in child['commute_minutes_by_location'].values():
            commute.update(before=rng.randrange(8, 35), after=rng.randrange(8, 35))
    purpose = 'independent randomized prices, permission, budgets and changed time/commute'
    if index == 0:
        # Prespecified positive anchor supplies a valid certificate for corruptions.
        case['payers'][0]['payment_ceiling_cents'] = 100000
        for worker in case['workers']:
            worker['permitted_shift_ids'] = [s['id'] for s in case['shifts']]
        purpose = 'positive anchor with full declared shift choice and sufficient ceiling'
    elif index == 8:
        case['children'][0]['commute_minutes_by_location']['LB']['before'] = 36
        purpose = 'backup commute extends beyond every backup offer window'
    elif index == 9:
        case['payers'][0]['payment_ceiling_cents'] = 0
        purpose = 'zero funding ceiling'
    elif index == 10:
        for person in case['staff']:
            if person['id'].startswith('B'):
                person['qualification_tags'] = []
        purpose = 'no qualified backup staff'
    elif index == 11:
        case['providers'][1]['declared_offer_acceptance'] = False
        purpose = 'backup provider explicitly declines'

    collections = ['shifts', 'employers', 'workers', 'children', 'providers', 'locations', 'staff', 'offers', 'scenarios', 'payers']
    token = f'{rng.getrandbits(48):012x}'
    mapping = {key: {row['id']: f'{key}_{token}_{j}' for j, row in enumerate(case[key])} for key in collections}
    # "normal" is a protocol-defined key, not a freely renameable identity.
    mapping['scenarios']['normal'] = 'normal'
    for employer in case['employers']:
        employer['staffing_quotas'] = {mapping['shifts'][s]: q for s, q in employer['staffing_quotas'].items()}
    for worker in case['workers']:
        worker['employer_id'] = mapping['employers'][worker['employer_id']]
        worker['current_shift_id'] = mapping['shifts'][worker['current_shift_id']]
        worker['permitted_shift_ids'] = [mapping['shifts'][s] for s in worker['permitted_shift_ids']]
        worker['change_compensation_cents'] = {mapping['shifts'][s]: q for s, q in worker['change_compensation_cents'].items()}
    for child in case['children']:
        child['parent_worker_id'] = mapping['workers'][child['parent_worker_id']]
        child['acceptable_location_ids'] = [mapping['locations'][s] for s in child['acceptable_location_ids']]
        child['commute_minutes_by_location'] = {mapping['locations'][s]: q for s, q in child['commute_minutes_by_location'].items()}
    for offer in case['offers']:
        offer['provider_id'] = mapping['providers'][offer['provider_id']]
        offer['location_id'] = mapping['locations'][offer['location_id']]
        offer['staff_ids'] = [mapping['staff'][s] for s in offer['staff_ids']]
    for world in case['scenarios']:
        for key, entity in [('failed_provider_ids', 'providers'), ('failed_staff_ids', 'staff'), ('closed_location_ids', 'locations')]:
            world[key] = [mapping[entity][s] for s in world[key]]
    for payer in case['payers']:
        payer['beneficiary_worker_ids'] = [mapping['workers'][s] for s in payer['beneficiary_worker_ids']]
    for key in collections:
        for row in case[key]:
            row['id'] = mapping[key][row['id']]
    for person in case['staff']:
        person['qualification_tags'] = ['qualification_' + token for _ in person['qualification_tags']]
    for offer in case['offers']:
        offer['required_qualification_tags'] = ['qualification_' + token]
    case['disclosures'].append('V2 confirmation: all entity identities renamed; new monetary/permission parameters, retimed schedules, and changed commute assumptions.')
    return case, {'seed': seed, 'index': index, 'time_offset_minutes': offset, 'purpose': purpose}


def check_case(case, instrument):
    expected = own_oracle(case)
    fixed_expected = own_oracle(case, True)
    comparison = instrument.compare(case)
    joint = comparison['results']['combined']
    conventional = comparison['results']['ordinary_exact_same_formulation']
    fixed = comparison['results']['fixed_roster_pooled_care']
    expected_cost = expected['best']['cost_cents'] if expected['best'] else None
    observed_cost = joint['offer']['maximum_funded_package_cents'] if joint['offer'] else None
    fee = None
    if expected['best_before_budget']:
        operating = expected['best_before_budget']['cost_cents'] - case['coordinator_fee_cents']
        if operating <= case['payers'][0]['payment_ceiling_cents']:
            fee = case['payers'][0]['payment_ceiling_cents'] - operating
    checks = {
        'feasibility': (joint['status'] == 'offered') == expected['feasible'] and joint['status'] in ['offered', 'refused'],
        'optimum_cost': observed_cost == expected_cost,
        'fee_boundary': joint['global_maximum_admissible_coordination_fee_cents'] == fee,
        'same_formulation_conventional_parity': joint['status'] == conventional['status'] and joint['offer'] == conventional['offer'],
        'fixed_roster_reference': (fixed['status'] == 'offered') == fixed_expected['feasible'],
        'without_commitments_refused': comparison['results']['flexible_without_opening_commitment']['status'] == 'refused',
    }
    independent = None
    if joint['offer']:
        independent = own_acceptance(case, joint['offer'])
        checks['independent_purpose_acceptance'] = independent['accepted']
    return {
        'case_id': case['case_id'], 'input_sha256': digest(case),
        'expected_feasible': expected['feasible'], 'observed_status': joint['status'],
        'fixed_roster_expected_feasible': fixed_expected['feasible'],
        'expected_cost_cents': expected_cost, 'observed_cost_cents': observed_cost,
        'expected_fee_boundary_cents': fee, 'checks': checks, 'independent': independent,
    }, joint['offer']


def main():
    started = now()
    elapsed = time.perf_counter()
    for name, pin in PINS.items():
        assert sha(SNAPSHOT / name) == pin, ('snapshot hash changed', name)
        assert sha(BASE / 'src' / name) == pin, ('source hash changed', name)
    policy_path = DIRECTORY / 'FRESH_V2_POLICY.json'
    if policy_path.exists():
        raise RuntimeError('Fresh V2 policy already exists; no silent rerun or seed replacement permitted')
    master_seed = secrets.randbits(64)
    rng = random.Random(master_seed)
    generated = [fresh_case(rng.getrandbits(64), i) for i in range(12)]
    cases = [c for c, metadata in generated]
    save(DIRECTORY / 'v2_fresh_cases.json', cases)
    policy = {
        'schema': 'agi-alpha.independent-v2-fresh-policy.v1',
        'created_at_utc': started, 'master_seed': master_seed,
        'source_pins': PINS, 'snapshot': str(SNAPSHOT.relative_to(BASE)),
        'runner_sha256': sha(__file__),
        'original_oracle_sha256': sha(BASE / 'src/independent_audit_cases.py'),
        'case_file_sha256': sha(DIRECTORY / 'v2_fresh_cases.json'),
        'cases': [metadata for c, metadata in generated],
        'fresh_count': 12, 'tamper_count': 20,
        'selection': 'Twelve seeds drawn once after final V2 source pins; no replacement based on solver outcome. Eight varied cases including one positive anchor; four prespecified refusal mechanisms. All identities except protocol normal key renamed, schedules retimed, commute changed.',
        'limitations': 'Same bounded two-employer four-worker two-child family; no wider-distribution, market, human or live care inference.',
        'disclosure': 'New seeds and full cases withheld from engineer until execution completed; all V1 cases treated as regression.',
    }
    save(policy_path, policy)
    sys.path.insert(0, str(SNAPSHOT))
    import e1_instrument_v2 as instrument
    import e1_verify_v2 as verifier
    report = {
        'schema': 'agi-alpha.independent-v2-confirmation.v1',
        'started_at_utc': started, 'source_pins': PINS,
        'policy': str(policy_path.relative_to(BASE)),
        'fresh': [], 'fresh_witnesses': {}, 'fresh_tamper': [],
        'regression': {'prior_incorrect_acceptances': [], 'prior_fresh_replay': [], 'prior_valid_witnesses': [], 'prior_semantic_replay': []},
    }
    for case in cases:
        row, offer = check_case(case, instrument)
        report['fresh'].append(row)
        if offer:
            report['fresh_witnesses'][case['case_id']] = offer

    anchor = cases[0]
    anchor_offer = report['fresh_witnesses'].get(anchor['case_id'])
    if anchor_offer is None:
        raise RuntimeError('Prespecified positive anchor unexpectedly failed; no alternate anchor selected')
    tamper_pairs = []
    def attack(label, mutate, scope='witness', rebind=False):
        c = copy.deepcopy(anchor)
        offer = copy.deepcopy(anchor_offer)
        before = digest([c, offer])
        mutate(c, offer)
        if rebind:
            offer['transformation_witness']['case_sha256'] = digest(c)
        assert digest([c, offer]) != before, ('mutation changed nothing', label)
        verdict = verifier.verify_offer(c, offer)
        independent = own_acceptance(c, offer) if scope == 'purpose_constraint' else None
        report['fresh_tamper'].append({'case_id': label, 'scope': scope, 'rebound_input_hash': rebind, 'accepted': verdict['valid'], 'errors': verdict['errors'], 'independent_purpose_verdict': independent})
        tamper_pairs.append({'case_id': label, 'input': c, 'witness': offer, 'verdict': verdict})
    def change(collection, identifier, updates):
        next(x for x in collection if x['id'] == identifier).update(updates)
    primary_id = next(iter(anchor_offer['scenario_assignments']['normal'].values()))
    primary = next(x for x in anchor['offers'] if x['id'] == primary_id)
    backup_id = anchor_offer['backup_obligation']['backup_offer_ids'][0]
    backup = next(x for x in anchor['offers'] if x['id'] == backup_id)
    changed_id = anchor_offer['transformation_witness']['changed_worker_ids'][0]
    selected_shift = anchor_offer['worker_roster'][changed_id]
    other_shift = next(x['id'] for x in anchor['shifts'] if x['id'] != selected_shift)
    first_child = anchor['children'][0]
    other_parent = next(x['id'] for x in anchor['workers'] if x['id'] != first_child['parent_worker_id'])
    outage_id = next(x['id'] for x in anchor['scenarios'] if primary['provider_id'] in x['failed_provider_ids'])
    # Twelve new serialized-certificate corruptions; none is a duplicate of the eight V1 accepted pairs.
    attack('future_day_reverification_waived', lambda c,o:o['repeatable_eligible_workload'].update(future_days_require_identical_or_freshly_verified_inputs=False))
    attack('verified_days_inflated', lambda c,o:o['repeatable_eligible_workload'].update(verified_operating_days=365))
    attack('new_commitment_list_erased', lambda c,o:o['transformation_witness'].update(new_commitment_offer_ids=[]))
    attack('changed_worker_list_erased', lambda c,o:o['transformation_witness'].update(changed_worker_ids=[]))
    attack('serialized_parent_reassigned', lambda c,o:o['worlds'][0]['child_care'][0].update(parent_worker_id=other_parent))
    attack('serialized_care_role_changed', lambda c,o:o['worlds'][0]['child_care'][0].update(role='backup'))
    attack('primary_invoice_unit_price_understated', lambda c,o:next(x for x in o['cost_items'] if x['id']=='primary:'+primary_id)['detail'].update(per_child_cost_cents=0))
    attack('backup_reserve_refund_denied', lambda c,o:next(x for x in o['cost_items'] if x['id']=='backup_activation_reserve')['detail'].update(refundable_unused_amount=False))
    attack('staff_opening_plan_erased', lambda c,o:o['worlds'][0]['opening_plan'][0].update(staff_ids=[]))
    attack('provided_care_starts_one_minute_late', lambda c,o:o['worlds'][0]['child_care'][0]['provided_care_interval'].__setitem__(0,o['worlds'][0]['child_care'][0]['provided_care_interval'][0]+1))
    attack('payer_total_omitted', lambda c,o:o['payer_allocation']['payer_totals_cents'].pop(c['payers'][0]['id']))
    attack('employer_output_row_duplicated', lambda c,o:o['employer_output_checks'].append(copy.deepcopy(o['employer_output_checks'][0])))
    # Eight purpose failures on fresh inputs, with matching input hashes.
    attack('fresh_shift_permission_withdrawn', lambda c,o:change(c['workers'],changed_id,{'permitted_shift_ids':[other_shift]}),'purpose_constraint',True)
    attack('fresh_backup_location_permission_withdrawn', lambda c,o:c['children'][0].update(acceptable_location_ids=[primary['location_id']]),'purpose_constraint',True)
    attack('fresh_care_commute_exceeds_window', lambda c,o:c['children'][0]['commute_minutes_by_location'][backup['location_id']].update(before=100),'purpose_constraint',True)
    attack('fresh_backup_qualification_withdrawn', lambda c,o:change(c['staff'],backup['staff_ids'][0],{'qualification_tags':[]}),'purpose_constraint',True)
    attack('fresh_primary_site_capacity_removed', lambda c,o:change(c['locations'],primary['location_id'],{'declared_concurrent_child_capacity':0}),'purpose_constraint',True)
    attack('fresh_payer_ceiling_removed', lambda c,o:c['payers'][0].update(payment_ceiling_cents=0),'purpose_constraint',True)
    attack('fresh_backup_reservation_limit_removed', lambda c,o:change(c['staff'],backup['staff_ids'][0],{'max_reserved_minutes':0}),'purpose_constraint',True)
    attack('fresh_notice_arrives_after_care_start', lambda c,o:change(c['scenarios'],outage_id,{'announced_minute':1439}),'purpose_constraint',True)
    assert len(report['fresh_tamper']) == policy['tamper_count']
    save(DIRECTORY / 'v2_fresh_tamper_pairs.json', tamper_pairs)

    # Known bad certificates are disclosed development/regression cases, never fresh.
    prior_bad = json.loads((DIRECTORY / 'v1_unexpected_acceptances.json').read_text())
    for pair in prior_bad:
        verdict = verifier.verify_offer(pair['input'], pair['witness'])
        report['regression']['prior_incorrect_acceptances'].append({'case_id':pair['case_id'], 'accepted':verdict['valid'], 'errors':verdict['errors']})
    prior_cases = json.loads((DIRECTORY / 'fresh_cases.json').read_text())
    prior_result = json.loads((BASE / 'results/independent_audit_v1_raw.json').read_text())
    for case in prior_cases:
        row, offer = check_case(case, instrument)
        report['regression']['prior_fresh_replay'].append(row)
        previous = prior_result['witnesses'].get(case['case_id'])
        if previous:
            verdict = verifier.verify_offer(case, previous)
            report['regression']['prior_valid_witnesses'].append({'case_id':case['case_id'], 'accepted':verdict['valid'], 'errors':verdict['errors']})
    for label, case in semantic_cases():
        case['currency'] = 'CAD'
        expected = own_oracle(case)
        try:
            result = instrument.solve(case, 'combined')
            status = result['status']
            passed = (status == 'offered') == expected['feasible'] and status in ['offered','refused']
        except Exception as error:
            status = type(error).__name__ + ': ' + str(error)
            passed = not expected['feasible']
        report['regression']['prior_semantic_replay'].append({'case_id':case['case_id'], 'expected_feasible':expected['feasible'], 'observed':status, 'passed':passed})
    large = make_case(910271)
    large['currency'] = 'CAD'
    large['payers'][0]['payment_ceiling_cents'] = 200000
    scale = 10**9
    for worker in large['workers']:
        worker['change_compensation_cents'] = {s:v*scale for s,v in worker['change_compensation_cents'].items()}
    for offer in large['offers']:
        for key in ['fixed_opening_cost_cents','per_child_cost_cents','standby_retainer_cents']:
            offer[key] *= scale
    for payer in large['payers']:
        payer['payment_ceiling_cents'] *= scale
    large['coordinator_fee_cents'] *= scale
    large['case_id'] = 'audit_uniform_large_integer_scaling'
    expected = own_oracle(large)
    result = instrument.solve(large, 'combined')
    actual = result['offer']['maximum_funded_package_cents'] if result['offer'] else None
    report['regression']['large_integer'] = {'expected_cost_cents':expected['best']['cost_cents'], 'observed_cost_cents':actual, 'observed_status':result['status'], 'passed':result['status']=='offered' and actual==expected['best']['cost_cents'], 'acceptance_check':result.get('acceptance_check')}
    origin = json.loads((SNAPSHOT / 'origin_case.json').read_text())
    result = instrument.compare(origin)
    offered = result['results']['combined']['offer']
    report['origin'] = {'statuses':{k:v['status'] for k,v in result['results'].items()}, 'package_cents':offered['maximum_funded_package_cents'], 'independent':own_acceptance(origin,offered), 'control_parity':result['same_formulation_exact_control']['identical_selected_result']}
    groups = Counter((x['expected_feasible'], x['fixed_roster_expected_feasible']) for x in report['fresh'])
    report['summary'] = {
        'fresh_total':len(report['fresh']),
        'fresh_feasible':sum(x['expected_feasible'] for x in report['fresh']),
        'fresh_refused':sum(not x['expected_feasible'] for x in report['fresh']),
        'fresh_all_checks_pass':sum(all(x['checks'].values()) for x in report['fresh']),
        'fresh_conventional_parity':sum(x['checks']['same_formulation_conventional_parity'] for x in report['fresh']),
        'fresh_joint_fixed_comparison':[{'joint_feasible':a,'fixed_feasible':b,'cases':n} for (a,b),n in sorted(groups.items())],
        'fresh_tamper_total':len(report['fresh_tamper']),
        'fresh_tamper_rejected':sum(not x['accepted'] for x in report['fresh_tamper']),
        'fresh_purpose_constraint_changes_independently_rejected':sum(x['independent_purpose_verdict'] is not None and not x['independent_purpose_verdict']['accepted'] for x in report['fresh_tamper']),
        'prior_accepted_bad_rejected':sum(not x['accepted'] for x in report['regression']['prior_incorrect_acceptances']),
        'prior_replay_all_checks_pass':sum(all(x['checks'].values()) for x in report['regression']['prior_fresh_replay']),
        'prior_correct_witnesses_still_accepted':sum(x['accepted'] for x in report['regression']['prior_valid_witnesses']),
        'prior_semantic_replay_pass':sum(x['passed'] for x in report['regression']['prior_semantic_replay']),
        'large_integer_corrected':report['regression']['large_integer']['passed'],
        'elapsed_seconds':time.perf_counter()-elapsed,
    }
    report['finished_at_utc'] = now()
    report['source_pins_unchanged_after_run'] = all(sha(SNAPSHOT / n) == h and sha(BASE / 'src' / n) == h for n,h in PINS.items())
    save(BASE / 'results/independent_audit_v2_raw.json', report)
    print(json.dumps({'summary':report['summary'], 'finished_at_utc':report['finished_at_utc'], 'source_pins_unchanged_after_run':report['source_pins_unchanged_after_run']},indent=2))


if __name__ == '__main__':
    main()
