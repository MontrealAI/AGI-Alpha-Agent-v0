# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from economics import Ledger, option, replay, retention_decision
from run_mechanisms import events_for, run


def reference() -> dict:
    return {'schema': 'historical-invent-economy-regression/v1', 'capital_cents': 90_000_000,
            'reserve_cents': 0, 'capacity_units': 100, 'construction_capacity_units': 20,
            'common_success_probability': '4/5',
            'costs': {'independent_setup_cents': 60_000_000, 'shared_core_cents': 60_000_000,
                      'coordination_cents': 0},
            'buyers': [{'id': f'hypothetical-{i}', 'price_cents': 30_000_000,
                        'value_cap_cents': 36_000_000, 'deposit_cents': 0,
                        'delivery_cents': 7_500_000, 'support_cents': 0,
                        'capacity_units': 10, 'payment_probability': '1', 'payment_day': 7} for i in range(4)]}


def check() -> tuple[dict, dict]:
    controls = []
    def record(name, condition):
        if not condition:
            raise AssertionError(name)
        controls.append({'name': name, 'passed': True})
    config = reference()
    proposal = option(config, True, True)
    paths = run(config)
    success = replay(config, events_for(config, proposal, 'success'))
    failure = replay(config, events_for(config, proposal, 'common-failure'))
    record('original-expected120000-prefunding900000',
           proposal['expected_contribution_cents'] == '12000000' and proposal['conservative_opening_cash_cents'] == 90_000_000)
    record('original-success300000-seed-not-earned', success['final']['collected_basis_profit_cents'] == 30_000_000
           and success['events'][0]['state']['earned_collections_cents'] == 0)
    expected = Fraction(4, 5) * success['final']['cash_cents'] + Fraction(1, 5) * failure['final']['cash_cents']
    record('independent-branch-expectation120000', expected - config['capital_cents'] == 12_000_000)
    route_events = events_for(config, proposal, 'success') + [
        {'day': 8, 'kind': 'cost', 'bucket': 'A', 'activity': 'route', 'amount_cents': 16_000_000}]
    routed = replay(config, route_events)
    expected_route = Fraction(4, 5) * routed['final']['collected_basis_profit_cents'] + Fraction(1, 5) * failure['final']['collected_basis_profit_cents']
    record('original-route-burden-negative8000', expected_route == -800_000)
    insufficient = copy.deepcopy(config)
    insufficient['capital_cents'] = 60_000_000
    record('positive-expectation-is-not-funding', option(insufficient, True, True)['decision'] == 'stop')
    record('cash-prefix-enforced-even-if-plan-forced', replay(insufficient, events_for(insufficient, proposal, 'success'))['refused'] is not None)
    second = copy.deepcopy(config)
    second['buyers'] = second['buyers'][:2]
    second['capital_cents'] = second['costs']['shared_core_cents'] = 30_000_000
    record('successor300000-setup-needs450000', option(second, True, True)['conservative_opening_cash_cents'] == 45_000_000
           and option(second, True, True)['decision'] == 'stop')
    second['costs']['shared_core_cents'] = 15_000_000
    record('successor150000-setup-fits300000', option(second, True, True)['decision'] == 'produce'
           and option(second, True, True)['expected_contribution_cents'] == '21000000')
    record('unrestricted-expert-can-choose-same-package', paths['unrestricted_expert_selection'] == proposal)
    held = Ledger()
    held.post({'day': 0, 'kind': 'deposit', 'party': 'buyer', 'amount_cents': 1000})
    try:
        held.post({'day': 1, 'kind': 'cost', 'bucket': 'A', 'activity': 'improper-spend', 'amount_cents': 1})
        held_refused = False
    except ValueError:
        held_refused = True
    held.post({'day': 2, 'kind': 'refund', 'party': 'buyer', 'amount_cents': 1000})
    record('refundable-deposit-never-finances-work', held_refused and held.cash == 0 and held.state()['collected_basis_profit_cents'] == 0)
    invoice = Ledger()
    invoice.post({'day': 0, 'kind': 'accept', 'party': 'buyer', 'amount_cents': 500})
    record('accepted-invoice-not-cash', invoice.cash == 0 and invoice.earned_collections == 0 and invoice.recognized == 500)
    invoice.post({'day': 1, 'kind': 'collect', 'party': 'buyer', 'amount_cents': 125})
    invoice.post({'day': 2, 'kind': 'default', 'party': 'buyer'})
    record('default-does-not-double-count-loss', invoice.state()['accrual_profit_cents'] == 125
           and invoice.state()['collected_basis_profit_cents'] == 125 and invoice.writeoffs == 375)
    debt = Ledger(100)
    debt.post({'day': 0, 'kind': 'capital', 'amount_cents': 1000})
    debt.post({'day': 1, 'kind': 'cost', 'bucket': 'B', 'activity': 'assess', 'amount_cents': 200,
               'pay_now': False, 'authorized_supplier_credit': True})
    before = debt.state()['available_cents']
    debt.post({'day': 2, 'kind': 'pay_cost', 'activity': 'assess', 'amount_cents': 200})
    record('paying-reserved-obligation-charges-no-second-cost', before == debt.state()['available_cents'] == 700
           and debt.costs['B'] == 200 and debt.paid == 200)
    try:
        debt.post({'day': 3, 'kind': 'cost', 'bucket': 'C', 'activity': 'assess', 'amount_cents': 200})
        duplicate = False
    except ValueError:
        duplicate = True
    record('cross-bucket-double-charge-refused', duplicate and debt.costs['C'] == 0)
    small = copy.deepcopy(config)
    small['capacity_units'] = 25
    record('capacity-exhaustion-preserves-incomplete-work', replay(small, events_for(small, proposal, 'success'))['refused'] is not None)
    deposits = copy.deepcopy(config)
    for buyer in deposits['buyers']:
        buyer['deposit_cents'] = 100_000
    withdrawn = replay(deposits, events_for(deposits, proposal, 'withdrawal'))
    record('withdrawal-refunds-and-does-not-erase-common-cost', withdrawn['final']['refunds_cents'] == 100_000
           and withdrawn['final']['earned_collections_cents'] == 90_000_000
           and withdrawn['final']['costs_cents']['A'] == 82_500_000)
    delayed = replay(config, events_for(config, proposal, 'delay'))
    record('delay-distinct-from-default', delayed['events'][-1]['event']['day'] == 37
           and delayed['final'] == success['final'])
    for path in paths['paths']:
        result = path['ledger']
        for item in result['events']:
            state = item['state']
            assert state['cash_cents'] == state['capital_cents'] + state['gross_collections_cents'] - state['refunds_cents'] - state['paid_costs_cents']
            assert state['cash_cents'] >= state['refundable_liability_cents']
    record('all24-scenario-cash-prefixes-conserve-and-protect-refunds', len(paths['paths']) == 24)
    same_content = replay(config, events_for(config, proposal, 'success'))
    record('identical-content-library-accounting-parity', same_content == success)
    costs = []
    for extra in (100, 200):
        events = events_for(config, proposal, 'success') + [{'day': 8, 'kind': 'cost', 'bucket': 'B',
                   'activity': 'retention-and-distribution', 'amount_cents': extra}]
        costs.append(replay(config, events)['final']['collected_basis_profit_cents'])
    record('sharing-cost-is-not-assigned-a-free-benefit', costs[0] - costs[1] == 100)
    spec = {'maximum_delta_cents': '100', 'forecast_uses': '10', 'assessment_cents': 1000,
            'additional_lifecycle_cents': 1}
    record('impossible-admission-skips-new-assessment', retention_decision(spec)['decision'] == 'reject-before-assessment')
    spec['assessment_cents'] = 100
    record('reachable-is-not-admitted', retention_decision(spec)['decision'] == 'assess')
    spec.update(lower_delta_cents='80', fresh_correctness_passed=True)
    record('retention-possible-with-fresh-positive-evidence', retention_decision(spec)['decision'] == 'retain')
    spec.update(lower_delta_cents='-20')
    record('failed-assessment-remains-charged', retention_decision(spec) == {'decision': 'reject-after-assessment', 'charge_cents': 100, 'authority_granted': False})
    return ({'schema': 'economic-conservation-controls/v1', 'passed': len(controls), 'total': len(controls),
             'controls': controls, 'scope': 'Mechanical and historical synthetic controls, not flagship economics'}, paths)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    summary, paths = check()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'controls.json').write_text(json.dumps(summary, indent=2) + '\n')
    (args.out / 'historical-reference-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
    print(json.dumps({'passed': summary['passed'], 'total': summary['total']}))
