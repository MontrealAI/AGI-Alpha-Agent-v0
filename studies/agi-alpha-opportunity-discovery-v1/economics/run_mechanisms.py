# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import json
from fractions import Fraction
from pathlib import Path
from typing import Any
from economics import option, replay


def events_for(config: dict[str, Any], proposal: dict[str, Any], shock: str) -> list[dict[str, Any]]:
    events = [{'day': 0, 'kind': 'capital', 'amount_cents': config['capital_cents']}]
    if proposal['decision'] != 'produce':
        return events
    buyers = [b for b in config['buyers'] if b['id'] in proposal['participants']]
    events += [{'day': 1, 'kind': 'deposit', 'party': b['id'], 'amount_cents': b['deposit_cents']} for b in buyers]
    events += [{'day': 2, 'kind': 'cost', 'bucket': 'A', 'activity': 'construction',
                'amount_cents': proposal['construction_cents']},
               {'day': 2, 'kind': 'cost', 'bucket': 'A', 'activity': 'coordination',
                'amount_cents': proposal['coordination_cents']}]
    events.append({'day': 2, 'kind': 'work', 'capacity_units': config['construction_capacity_units']})
    for i, buyer in enumerate(buyers):
        who = buyer['id']
        if shock == 'common-failure' or (shock == 'withdrawal' and i == 0):
            events.append({'day': 3, 'kind': 'refund', 'party': who, 'amount_cents': buyer['deposit_cents']})
            continue
        events += [{'day': 4, 'kind': 'work', 'capacity_units': buyer['capacity_units']},
                   {'day': 4, 'kind': 'cost', 'bucket': 'A', 'activity': who + '-delivery',
                    'amount_cents': buyer['delivery_cents']}]
        if shock == 'partial-delivery-failure' and i == 0:
            events.append({'day': 5, 'kind': 'refund', 'party': who, 'amount_cents': buyer['deposit_cents']})
            continue
        events += [{'day': 5, 'kind': 'accept', 'party': who, 'amount_cents': buyer['price_cents']},
                   {'day': 5, 'kind': 'cost', 'bucket': 'A', 'activity': who + '-support',
                    'amount_cents': buyer['support_cents'], 'pay_now': False, 'authorized_supplier_credit': True},
                   {'day': 6, 'kind': 'pay_cost', 'activity': who + '-support', 'amount_cents': buyer['support_cents']}]
        payment_day = max(7, buyer['payment_day']) + (30 if shock == 'delay' else 0)
        events.append({'day': payment_day, 'kind': 'default' if shock == 'default' and i == 0 else 'collect',
                       'party': who, 'amount_cents': buyer['price_cents'] - buyer['deposit_cents']})
    return sorted(events, key=lambda event: event['day'])


def run(config: dict[str, Any]) -> dict[str, Any]:
    options = [option(config, technical, coordinated) for technical in (False, True) for coordinated in (False, True)]
    eligible = [x for x in options if x['decision'] == 'produce']
    selected = max(eligible, key=lambda x: Fraction(x['expected_contribution_cents'])) if eligible else None
    paths = []
    for proposal in options:
        if proposal['decision'] == 'unpriced':
            continue
        for shock in ('success', 'common-failure', 'withdrawal', 'partial-delivery-failure', 'default', 'delay'):
            result = replay(config, events_for(config, proposal, shock))
            paths.append({'proposal': proposal, 'realization': shock, 'ledger': result})
    return {'schema': 'capability-arrangement-mechanisms/v1', 'evidence_type': 'SIMULATED_CONDITIONAL_SCENARIOS',
            'options': options, 'unrestricted_expert_selection': selected, 'paths': paths,
            'economic_frontier_established': False, 'actual_customer_revenue_usd': 0,
            'comparison_scope': 'Restricted2x2 identifies assumptions; unrestricted expert may choose same package.',
            'retention_scope': 'Private/shared/same-content library must supply measured cost and access inputs separately.',
            'no_prescribed_advantage': True, 'source_of_prices_and_demand': 'Scenario assumptions, not market observations'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(json.loads(args.scenario.read_text()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'options': result['options'], 'paths': len(result['paths'])}, indent=2))
