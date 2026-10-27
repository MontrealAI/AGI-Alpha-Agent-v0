# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import random
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parents[1] / 'agi-alpha-opportunity-discovery-v1' / 'economics' / 'economics.py'
SPEC = importlib.util.spec_from_file_location('preserved_economic_ledger', PRIOR)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError('Preserved ledger is unavailable')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
Ledger = MODULE.Ledger


def cents(minutes: int, rate: int) -> int:
    return int((Decimal(minutes) * Decimal(rate) / 60).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def packet_cost(p: dict, config: str, rate: int | None = None, gain: int | None = None,
                human_minutes: int | None = None, ordinary_gain: int | None = None) -> dict:
    ref = p['reference']
    rate = rate or ref['labor_rate_cents_per_hour']
    stages = copy.deepcopy(p['labor_stages_minutes'][config])
    if config == 'H' and human_minutes is not None:
        stages['extraction'] += human_minutes - sum(stages.values())
    if config in ('E+', 'library'):
        stages = copy.deepcopy(p['labor_stages_minutes']['E'])
        stages['extraction'] -= ref['expert_minutes'] - ref['retained_minutes'] if gain is None else gain
    if config == 'U' and ordinary_gain is not None:
        stages = copy.deepcopy(p['labor_stages_minutes']['E'])
        stages['extraction'] += ordinary_gain
    if min(stages.values()) < 0:
        raise ValueError('Unsupported negative task stage')
    labor = {k: cents(v, rate) for k, v in stages.items()}
    nonlabor = dict(p['nonlabor_cents'])
    if config == 'H':
        nonlabor['model'] = 0
    support = cents(ref['support_minutes'], rate)
    return {'labor_minutes': sum(stages.values()), 'stage_minutes': stages,
            'stage_cents': labor, 'nonlabor_cents': nonlabor, 'support_cents': support,
            'total_cents': sum(labor.values()) + sum(nonlabor.values()) + support}


def prices(p: dict) -> dict:
    human = packet_cost(p, 'H')['total_cents']
    expert = packet_cost(p, 'E')['total_cents']
    probability = Fraction(p['reference']['assumed_acceptance_probability']) * Fraction(p['reference']['assumed_collection_probability'])
    caps = [min(v, human, p['acceptance']['maximum_buyer_budget_cents']) for v in p['buyer_wtp_cents']]
    rows = []
    for price in p['price_grid_cents']:
        buyers = [f'b{i+1}' for i, cap in enumerate(caps) if cap >= price]
        expected = len(buyers) * (probability * price - expert)
        rows.append({'price_cents': price, 'buyers': buyers, 'expected_E_contribution_cents': str(expected),
                     'expected_C_inclusive_contribution_cents': str(expected - p['reference']['C_discovery_cents'])})
    best = max(rows, key=lambda x: (Fraction(x['expected_E_contribution_cents']), -x['price_cents']))
    if Fraction(best['expected_E_contribution_cents']) <= 0:
        return {'decision': 'stop', 'grid': rows, 'human_outside_option_cents': human}
    return {'decision': 'quote', 'selected_price_cents': best['price_cents'], 'selected_buyers': best['buyers'],
            'human_outside_option_cents': human, 'buyer_caps_cents': caps, 'grid': rows,
            'selection_uses': 'Frozen E cost, frozen participation and success/collection assumptions only',
            'future_worlds_used': False}


def run_path(p: dict, chosen: dict, config: str, shock: str = 'success', overrides: dict | None = None) -> dict:
    ref = p['reference']
    o = overrides or {}
    rate = o.get('rate', ref['labor_rate_cents_per_hour'])
    gain = o.get('gain', ref['expert_minutes'] - ref['retained_minutes'])
    if shock in ('no-transfer-gain', 'model-obsolescence'):
        gain = 0
    if shock == 'negative-transfer':
        gain = -10
    cap = 25000 if shock == 'underfunded' else ref['capital_cents']
    capacity = o.get('capacity_minutes', 100 if shock == 'capacity-shortage' else ref['capacity_minutes'])
    ledger = Ledger(ref['reserve_cents'], capacity)
    events: list[dict] = []
    decisions: list[dict] = []
    refused = None

    def post(e: dict) -> bool:
        nonlocal refused
        try:
            ledger.post(e)
            events.append(e)
            return True
        except ValueError as error:
            refused = {'event': e, 'reason': str(error)}
            return False

    def charge(day: int, activity: str, bucket: str, amount: int) -> bool:
        return post({'day': day, 'kind': 'cost', 'activity': activity, 'bucket': bucket, 'amount_cents': amount})

    def delivery_cost(day: int, name: str, cost: dict) -> bool:
        if not post({'day': day, 'kind': 'work', 'capacity_units': cost['labor_minutes'] + ref['support_minutes']}):
            return False
        for category, amount in cost['stage_cents'].items():
            if not charge(day, name + ':labor:' + category, 'A', amount):
                return False
        for category, amount in cost['nonlabor_cents'].items():
            if not charge(day, name + ':' + category, 'A', amount):
                return False
        return charge(day, name + ':support', 'A', cost['support_cents'])

    post({'day': 0, 'kind': 'capital', 'amount_cents': cap})
    discovery = o.get('C', ref['C_discovery_cents'])
    if not charge(0, 'bounded-unpaid-opportunity-investigation', 'C', discovery):
        raise ValueError('Initial discovery exceeds authorized capital')
    quote = chosen['selected_price_cents']
    human_cost = packet_cost(p, 'H', rate, human_minutes=o.get('human_minutes'))['total_cents']
    buyers = [f'b{i+1}' for i, v in enumerate(p['buyer_wtp_cents']) if min(v, human_cost, 45000) >= quote]
    if shock == 'buyer-decline' or o.get('customer_minutes', ref['customer_minutes']) > p['acceptance']['maximum_customer_minutes']:
        buyers = []
    cost_config = 'E+' if config == 'library' else config
    cost = packet_cost(p, cost_config, rate, gain, ordinary_gain=o.get('ordinary_gain'))
    core = cents(ref['initial_core_minutes'], rate) if config in ('E+', 'library') else 0
    required = discovery + core + len(buyers) * cost['total_cents'] + ref['reserve_cents']
    required_minutes = (ref['initial_core_minutes'] if core else 0) + len(buyers) * (cost['labor_minutes'] + ref['support_minutes'])
    expected_per_order = Fraction(ref['assumed_acceptance_probability']) * Fraction(ref['assumed_collection_probability']) * quote - cost['total_cents']
    if not buyers or required > cap or required_minutes > capacity or expected_per_order * len(buyers) <= core:
        decisions.append({'stage': 'initial', 'decision': 'stop-before-contract', 'buyers': buyers,
                          'required_cash_cents': required, 'required_minutes': required_minutes,
                          'expected_initial_contribution_before_C_cents': str(expected_per_order * len(buyers) - core)})
        return summarize(ledger, events, decisions, refused, config, shock, quote, cost, core, required, o)
    deposit = min(ref['deposit_cents'], quote)
    for buyer in buyers:
        post({'day': 0, 'kind': 'deposit', 'party': buyer, 'amount_cents': deposit})
    if core:
        post({'day': 1, 'kind': 'work', 'capacity_units': ref['initial_core_minutes']})
        charge(1, 'first-delivery-required-generic-core', 'A', core)
    served = []
    for i, buyer in enumerate(buyers):
        if shock == 'withdrawal' and i == len(buyers) - 1:
            post({'day': 1, 'kind': 'refund', 'party': buyer, 'amount_cents': deposit})
            continue
        if not delivery_cost(1, buyer, cost):
            break
        served.append(buyer)
    support_incomplete = set()
    if shock == 'support-overrun':
        for buyer in served:
            extra_minutes = 30
            if ledger.used_capacity + extra_minutes > capacity:
                support_incomplete.add(buyer)
                decisions.append({'stage': buyer, 'decision': 'cancel-unaccepted-contract',
                                  'reason': 'insufficient-provider-capacity-for-extra-support',
                                  'requested_minutes': extra_minutes, 'performed_minutes': 0,
                                  'additional_fee_paid_cents': 0})
                post({'day': 2, 'kind': 'refund', 'party': buyer, 'amount_cents': deposit})
            else:
                post({'day': 2, 'kind': 'work', 'capacity_units': extra_minutes})
                charge(2, buyer + ':extra-support', 'A', cents(extra_minutes, rate))
    accepted = []
    for i, buyer in enumerate(served):
        if buyer in support_incomplete:
            continue
        fail = shock == 'common-failure' or shock == 'partial-delivery' and i == len(served) - 1
        if fail:
            extra_minutes = 15
            if ledger.used_capacity + extra_minutes > capacity:
                decisions.append({'stage': buyer, 'decision': 'cancel-unaccepted-contract',
                                  'reason': 'insufficient-provider-capacity-for-failed-correction',
                                  'requested_minutes': extra_minutes, 'performed_minutes': 0,
                                  'additional_fee_paid_cents': 0})
            else:
                post({'day': 2, 'kind': 'work', 'capacity_units': extra_minutes})
                charge(2, buyer + ':failed-semantic-correction', 'A', cents(extra_minutes, rate))
            post({'day': 2, 'kind': 'refund', 'party': buyer, 'amount_cents': deposit})
        else:
            post({'day': 2, 'kind': 'accept', 'party': buyer, 'amount_cents': quote})
            accepted.append(buyer)
    for i, buyer in enumerate(accepted):
        if shock == 'one-default' and i == len(accepted) - 1 or buyer in o.get('defaulted_buyers', []):
            post({'day': 2, 'kind': 'default', 'party': buyer})
        elif shock != 'payment-delay':
            post({'day': 2, 'kind': 'collect', 'party': buyer, 'amount_cents': quote - deposit})
    initial_profit = ledger.state()['collected_basis_profit_cents']
    decisions.append({'stage': 'initial-delivery', 'accepted': len(accepted), 'source_bindings': p['source_bindings']['initial'],
                      'collected_campaign_profit_cents': initial_profit, 'actual_customer_acceptance': False})
    retain = False
    if config in ('E+', 'library'):
        upper = cents(ref['prescreen_upper_saving_minutes'], rate) * ref['forecast_eligible_uses']
        total_B = ref['B_assessment_cents'] + ref['B_packaging_cents'] + ref['B_upkeep_cents']
        lower_minutes = ref['assessment_lower_saving_minutes']
        if shock == 'model-obsolescence' or o.get('compatible') is False:
            lower_minutes = 0
        lower = cents(lower_minutes, rate)
        compatible_forecast = ref['forecast_eligible_uses']
        if upper <= total_B:
            reason = 'impossible-bound-reject-before-assessment'
        elif initial_profit < total_B + cost['total_cents']:
            reason = 'preserve-seed-insufficient-earned-funds-for-assessment-and-next-order'
        else:
            charge(3, 'additional-independent-retention-assessment', 'B', ref['B_assessment_cents'])
            retain = lower > 0 and lower * compatible_forecast > total_B
            reason = 'conditional-retain' if retain else 'reject-after-assessment'
            if retain:
                charge(3, 'additional-rights-packaging-and-transfer', 'B', ref['B_packaging_cents'])
                charge(3, 'reserved-upkeep-paid', 'B', ref['B_upkeep_cents'])
        decisions.append({'stage': 'retention', 'decision': reason, 'conditional_retained': retain,
                          'assumed_lower_saving_minutes': lower_minutes, 'forecast_uses': compatible_forecast,
                          'assumed_lower_net_cents': lower * compatible_forecast - total_B,
                          'empirical_admission': False, 'production_authority': False})
    fresh_config = cost_config if retain or config not in ('E+', 'library') else 'E'
    fresh_cost = packet_cost(p, fresh_config, rate, gain, ordinary_gain=o.get('ordinary_gain'))
    for i in range(ref['fresh_orders']):
        day, buyer = 4 + 3*i, 'fresh-' + str(i+1)
        earned = ledger.state()['collected_basis_profit_cents']
        if shock in ('common-failure', 'partial-delivery') or earned < fresh_cost['total_cents'] or len(accepted) == 0:
            decisions.append({'stage': buyer, 'decision': 'stop', 'reason': 'quality-remediation-or-earned-funding',
                              'earned_funds_cents': earned, 'required_cents': fresh_cost['total_cents']})
            break
        if ledger.used_capacity + fresh_cost['labor_minutes'] + ref['support_minutes'] > capacity:
            decisions.append({'stage': buyer, 'decision': 'stop', 'reason': 'remaining-capacity'})
            break
        post({'day': day, 'kind': 'deposit', 'party': buyer, 'amount_cents': deposit})
        if not delivery_cost(day, buyer, fresh_cost):
            break
        post({'day': day+1, 'kind': 'accept', 'party': buyer, 'amount_cents': quote})
        if buyer in o.get('defaulted_buyers', []):
            post({'day': day+1, 'kind': 'default', 'party': buyer})
        else:
            post({'day': day+1, 'kind': 'collect', 'party': buyer, 'amount_cents': quote-deposit})
        decisions.append({'stage': buyer, 'decision': 'deliver', 'configuration': fresh_config,
                          'source_binding': p['source_bindings']['fresh'][i], 'earned_funds_before_cents': earned,
                          'cost_cents': fresh_cost['total_cents'], 'actual_buyer': False})
    if shock == 'payment-delay':
        for buyer in accepted:
            post({'day': 20, 'kind': 'collect', 'party': buyer, 'amount_cents': quote-deposit})
    return summarize(ledger, events, decisions, refused, config, shock, quote, cost, core, required, o)


def summarize(ledger: Any, events: list, decisions: list, refused: Any, config: str,
              shock: str, quote: int, cost: dict, core: int, required: int, overrides: dict) -> dict:
    return {'schema': 'connected-conditional-cash-path/v1.1', 'evidence_type': 'SIMULATED_ASSUMED_WORLD',
            'capacity_scope': 'Declared A provider labor including support/correction; B/C are assumed outsourced fees with no internal provider minutes; not total social labor.',
            'configuration': config, 'shock': shock, 'overrides': overrides, 'quote_cents': quote,
            'per_packet_cost': cost, 'required_core_cents': core, 'required_opening_cash_cents': required,
            'accepted_packets': len(ledger.accepted), 'fresh_deliveries': sum(x.get('stage', '').startswith('fresh-') and x.get('decision') == 'deliver' for x in decisions),
            'events': ledger.history, 'decisions': decisions, 'refused': refused, 'final': ledger.state(),
            'minimum_available_cents': min(x['state']['available_cents'] for x in ledger.history),
            'actual_customer_revenue_cents': 0, 'actual_complete_research_cost_cents': None,
            'actual_profit_cents': None, 'actual_economic_admission': False,
            'opportunity_cost_added_to_cash_cost': False,
            'limitations': ['All market/time/cost/quality inputs assumed', 'Placeholder artifact IDs are not receipts',
                            'Scenario acceptance is not a real buyer decision', 'No live identity, settlement or paid model call']}


def factorial(p: dict, price: int) -> dict:
    e, ep = packet_cost(p, 'E'), packet_cost(p, 'E+')
    core = cents(p['reference']['initial_core_minutes'], p['reference']['labor_rate_cents_per_hour'])
    rows = []
    for shared in (False, True):
        for coordinated in (False, True):
            n = 3 if coordinated else 1
            a = (ep if shared else e)['total_cents']*n + (core if shared else 0)
            coordination = p['coordination_cents'] if coordinated else 0
            contribution = n*price-a-coordination
            rows.append({'shared_core': shared, 'coordinated': coordinated, 'buyers': n,
                         'A_cents': a+coordination, 'success_contribution_before_common_C_cents': contribution,
                         'positive_without_retention': contribution > 0})
    return {'rows': rows, 'unrestricted_expert_available_options': rows,
            'finding': 'All four reference packages are profitable conditionally; neither complementarity nor novel market creation is required. Same shared package is available to unrestricted E.',
            'supplied_core_compatibility_and_demand': True, 'autonomous_invention': False}


def stress_worlds(p: dict, selected: dict) -> list:
    rng = random.Random(p['fresh_seed'])
    r = p['fresh_ranges']
    rows = []
    for i in range(p['fresh_worlds']):
        rate = rng.choice(r['labor_rate_cents_per_hour'])
        human = rng.choice(r['human_minutes'])
        ordinary_gain = rng.choice(r['ordinary_to_expert_gain_minutes'])
        transfer = rng.choice(r['transfer_gain_minutes'])
        payment = Fraction(rng.choice(r['collection_probability']))
        discovery = rng.choice(r['C_discovery_cents'])
        compatible = rng.choice(r['compatible_reuse'])
        customer = rng.choice(r['customer_minutes'])
        defaulted = [buyer for buyer in ['b1','b2','b3','b4','b5','fresh-1','fresh-2'] if rng.random() >= float(payment)]
        shock = 'success'
        o = {'rate': rate, 'human_minutes': human, 'ordinary_gain': ordinary_gain, 'gain': transfer,
             'C': discovery, 'compatible': compatible, 'customer_minutes': customer, 'defaulted_buyers': defaulted}
        arms = {x: run_path(p, selected, x, shock, o) for x in ('U', 'E', 'E+')}
        rows.append({'world': i, 'draw': o, 'assumed_payment_probability': str(payment), 'shock': shock,
                     'arms': {k: {'accepted_packets': v['accepted_packets'], 'fresh_deliveries': v['fresh_deliveries'],
                                  'profit_cents': v['final']['collected_basis_profit_cents'],
                                  'costs_cents': v['final']['costs_cents'], 'cash_cents': v['final']['cash_cents'],
                                  'available_cents': v['final']['available_cents'], 'refused': v['refused']} for k,v in arms.items()},
                     'E_minus_U_cents': arms['E']['final']['collected_basis_profit_cents']-arms['U']['final']['collected_basis_profit_cents'],
                     'Eplus_minus_E_cents': arms['E+']['final']['collected_basis_profit_cents']-arms['E']['final']['collected_basis_profit_cents']})
    return rows


def controls(p: dict, selected: dict, paths: dict) -> dict:
    rows = []
    def check(name: str, passed: bool) -> None:
        if not passed:
            raise AssertionError(name)
        rows.append({'name': name, 'passed': True})
    check('preserved-ledger-bytes', hashlib.sha256(PRIOR.read_bytes()).hexdigest() == p['ledger_source']['sha256'])
    for path in paths.values():
        for item in path['events']:
            s = item['state']
            check_id = s['cash_cents'] == s['capital_cents'] + s['gross_collections_cents'] - s['refunds_cents'] - s['paid_costs_cents']
            if not check_id or s['cash_cents'] < s['refundable_liability_cents']:
                raise AssertionError('cash-prefix')
    check('all-cash-prefixes-conserve-and-protect-refunds', True)
    check('capital-not-revenue', paths['E+success']['events'][0]['state']['earned_collections_cents'] == 0)
    check('all-nine-complete-cost-domains-covered', set(p['nonlabor_cents']) == {'model','tools','compute','storage','network','overhead'} and bool(p['labor_stages_minutes']['E']))
    check('price-grid-frozen-not-future-optimized', selected['future_worlds_used'] is False)
    eq = copy.deepcopy(paths['E+success'])
    eq['configuration'] = 'library'
    check('ordinary-library-identical-content-cost-parity', eq == paths['librarysuccess'])
    e, ep = paths['Esuccess'], paths['E+success']
    check('E-and-Eplus-both-qualify-no-new-offering-claim', e['accepted_packets'] == ep['accepted_packets'] == 5)
    check('earnings-finance-fresh-work-without-seed-erosion', all(x.get('earned_funds_before_cents', 0) >= x.get('cost_cents', 0) for x in ep['decisions'] if x.get('decision') == 'deliver'))
    check('no-transfer-gain-can-lose-versus-expert', paths['E+no-transfer-gain']['final']['collected_basis_profit_cents'] < e['final']['collected_basis_profit_cents'])
    check('negative-transfer-not-waived', paths['E+negative-transfer']['final']['collected_basis_profit_cents'] < paths['E+no-transfer-gain']['final']['collected_basis_profit_cents'])
    check('delayed-collection-stops-surplus-funded-next-order', paths['E+payment-delay']['fresh_deliveries'] == 0)
    check('default-keeps-loss-and-invoice-separate', paths['E+one-default']['final']['writeoffs_cents'] > 0)
    check('common-failure-no-accepted-sale', paths['E+common-failure']['accepted_packets'] == 0 and paths['E+common-failure']['final']['refunds_cents'] > 0)
    check('withdrawal-retains-common-cost', paths['E+withdrawal']['final']['refunds_cents'] > 0 and paths['E+withdrawal']['final']['costs_cents']['A'] >= ep['required_core_cents'])
    check('insufficient-opening-cash-stops-before-deposit', paths['E+underfunded']['final']['gross_collections_cents'] == 0)
    check('capacity-shortage-stops-before-contract', paths['E+capacity-shortage']['accepted_packets'] == 0)
    check('rejected-demand-does-not-refund-research-cost', paths['E+buyer-decline']['final']['collected_basis_profit_cents'] == -p['reference']['C_discovery_cents'])
    check('new-defaults-remove-admission', all(not x.get('conditional_retained', False) for x in paths['E+model-obsolescence']['decisions']))
    ledger = Ledger()
    ledger.post({'day':0,'kind':'capital','amount_cents':1000})
    ledger.post({'day':1,'kind':'cost','activity':'same','bucket':'A','amount_cents':100})
    try:
        ledger.post({'day':1,'kind':'cost','activity':'same','bucket':'B','amount_cents':100})
        duplicate = False
    except ValueError:
        duplicate = ledger.costs == {'A':100,'B':0,'C':0}
    check('A-B-C-double-charge-is-atomic-refusal', duplicate)
    check('conditional-events-never-create-actual-revenue', all(x['actual_customer_revenue_cents'] == 0 for x in paths.values()))
    return {'passed': len(rows), 'total': len(rows), 'controls': rows}


def urgent_frontier(p: dict, quote: int) -> dict:
    support = p['reference']['support_minutes']
    rows = []
    for label, delivery in [('expert',90),('negative-transfer',100),('no-transfer',90),('partial-transfer',70),('sufficient-transfer',50),('ordinary-library-same-50min-content',50),('expert-with-equivalent-available-tool',50)]:
        cost = packet_cost(p, 'E+', gain=90-delivery)
        total = delivery + support
        rows.append({'configuration':label,'delivery_labor_minutes':delivery,'support_minutes':support,
                     'total_provider_minutes':total,'provider_limit_minutes':60,'quote_cents':quote,
                     'complete_variable_cost_cents':cost['total_cents'],'customer_minutes':8,
                     'all_critical_facts_checked':'ASSUMED_TRUE_REQUIRED_FOR_ACCEPTANCE',
                     'conditionally_feasible':total <= 60 and quote <= 45000})
    return {'schema':'prospective-urgent-frontier/v1','evidence_type':'CONDITIONAL_ASSUMED_LABOR_NOT_MEASURED_GAIN',
            'required_transfer_saving_minutes':36,'rows':rows,
            'scope':'Fresh compatible packet after retained core construction and qualification; all fresh verification/correction and support retained',
            'baseline_can_use_equivalent_tools':True,
            'finding':'A50-minute delivery plus6-minute support fits60;70 and90 do not. If E already has an equivalent50-minute workflow it also qualifies. No observed new offering is established.'}


def run(out: Path, protocol: Path) -> dict:
    p = json.loads(protocol.read_text())
    selected = prices(p)
    paths = {c+s: run_path(p, selected, c, s) for c in ('H','U','E','E+','library') for s in (['success'] if c != 'E+' else p['path_names'])}
    checks = controls(p, selected, paths)
    fresh = stress_worlds(p, selected)
    gains = [x['Eplus_minus_E_cents'] for x in fresh]
    result = {'schema':'connected-economic-results/v1','protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
              'price_selection':selected,'reference':{k:v['final'] | {'accepted_packets':v['accepted_packets'],'fresh_deliveries':v['fresh_deliveries']} for k,v in paths.items() if k.endswith('success')},
              'factorial':factorial(p,selected['selected_price_cents']), 'controls':checks,
              'urgent_frontier':urgent_frontier(p,selected['selected_price_cents']),
              'fresh_summary':{'worlds':len(fresh),'Eplus_better':sum(x>0 for x in gains),'Eplus_equal':sum(x==0 for x in gains),'Eplus_worse':sum(x<0 for x in gains),'minimum_delta_cents':min(gains),'maximum_delta_cents':max(gains),'confidence_intervals_validate_assumptions':False},
              'retention_required_minutes_at_reference_rate_and_four_uses':60*6000/(12500*4),
              'whole_five_order_campaign_required_transfer_minutes':60*(12500+6000)/(12500*5),
              'actual_customer_revenue_cents':0,'actual_complete_research_cost_cents':None,'actual_profit_cents':None,'actual_economic_admission':False}
    out.mkdir(parents=True, exist_ok=False)
    for name, data in [('results.json',result),('paths.json',paths),('fresh-worlds.json',fresh)]:
        (out/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=ROOT/'confirmation-protocol.json')
    args=parser.parse_args()
    run(args.out, args.protocol)
