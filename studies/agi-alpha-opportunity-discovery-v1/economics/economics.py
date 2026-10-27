# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from typing import Any


class Ledger:
    def __init__(self, reserve_cents: int = 0, capacity_units: int = 0):
        self.cash = self.capital = self.gross_collections = self.refunds = self.paid = 0
        self.recognized = self.writeoffs = self.earned_collections = 0
        self.reserve = reserve_cents
        self.capacity = capacity_units
        self.used_capacity = 0
        self.costs = {k: 0 for k in 'ABC'}
        self.deposits: dict[str, int] = {}
        self.receivables: dict[str, int] = {}
        self.payables: dict[str, int] = {}
        self.activities: set[str] = set()
        self.accepted: set[str] = set()
        self.history: list[dict[str, Any]] = []
        self.day = -10**9
        if type(reserve_cents) is not int or type(capacity_units) is not int or min(reserve_cents, capacity_units) < 0:
            raise ValueError('Invalid reserve or capacity')

    def state(self) -> dict[str, Any]:
        refundable = sum(self.deposits.values())
        payable = sum(self.payables.values())
        return {'cash_cents': self.cash, 'capital_cents': self.capital,
                'gross_collections_cents': self.gross_collections,
                'earned_collections_cents': self.earned_collections,
                'recognized_revenue_cents': self.recognized, 'writeoffs_cents': self.writeoffs,
                'receivables_cents': sum(self.receivables.values()),
                'refundable_liability_cents': refundable, 'payables_cents': payable,
                'reserve_cents': self.reserve, 'available_cents': self.cash - refundable - payable - self.reserve,
                'costs_cents': self.costs.copy(), 'paid_costs_cents': self.paid, 'refunds_cents': self.refunds,
                'collected_basis_profit_cents': self.earned_collections - sum(self.costs.values()),
                'accrual_profit_cents': self.recognized - self.writeoffs - sum(self.costs.values()),
                'used_capacity_units': self.used_capacity, 'capacity_units': self.capacity}

    def post(self, event: dict[str, Any]) -> None:
        saved = copy.deepcopy(self.__dict__)
        try:
            day, kind, amount = event['day'], event['kind'], event.get('amount_cents', 0)
            if type(day) is not int or day < self.day or type(amount) is not int or amount < 0:
                raise ValueError('Invalid amount or nonchronological event')
            self.day = day
            who = event.get('party', '')
            activity = event.get('activity', '')
            if kind == 'capital':
                self.cash += amount
                self.capital += amount
            elif kind == 'deposit':
                if not who or who in self.accepted:
                    raise ValueError('Deposit requires an unaccepted contract')
                self.deposits[who] = self.deposits.get(who, 0) + amount
                self.cash += amount
                self.gross_collections += amount
            elif kind == 'cost':
                if not activity or activity in self.activities or event['bucket'] not in self.costs:
                    raise ValueError('Duplicate or invalid cost activity')
                pay = event.get('pay_now', True)
                if pay and self.state()['available_cents'] < amount:
                    raise ValueError('Cash needed before payment; refundable funds and reserves unavailable')
                if not pay and not event.get('authorized_supplier_credit', False):
                    raise ValueError('Unapproved supplier credit')
                self.activities.add(activity)
                self.costs[event['bucket']] += amount
                if pay:
                    self.cash -= amount
                    self.paid += amount
                else:
                    self.payables[activity] = amount
            elif kind == 'pay_cost':
                if amount > self.payables.get(activity, 0) or self.cash - sum(self.deposits.values()) - self.reserve < amount:
                    raise ValueError('Unfunded or nonexistent payable')
                self.payables[activity] -= amount
                self.cash -= amount
                self.paid += amount
            elif kind == 'accept':
                deposit = self.deposits.get(who, 0)
                if not who or who in self.accepted or deposit > amount:
                    raise ValueError('Duplicate acceptance or deposit above contract price')
                self.accepted.add(who)
                self.recognized += amount
                self.earned_collections += deposit
                self.deposits[who] = 0
                self.receivables[who] = amount - deposit
            elif kind == 'collect':
                if who not in self.accepted or amount > self.receivables.get(who, 0):
                    raise ValueError('Collection lacks accepted milestone or exceeds invoice')
                self.receivables[who] -= amount
                self.cash += amount
                self.gross_collections += amount
                self.earned_collections += amount
            elif kind == 'refund':
                if amount > self.deposits.get(who, 0) or self.cash < amount:
                    raise ValueError('Refund exceeds held deposit')
                self.deposits[who] -= amount
                self.cash -= amount
                self.refunds += amount
            elif kind == 'default':
                self.writeoffs += self.receivables.pop(who, 0)
            elif kind == 'work':
                units = event['capacity_units']
                if type(units) is not int or units < 0 or self.used_capacity + units > self.capacity:
                    raise ValueError('Insufficient declared campaign capacity')
                self.used_capacity += units
            else:
                raise ValueError('Unknown event type')
            state = self.state()
            if self.cash != self.capital + self.gross_collections - self.refunds - self.paid:
                raise AssertionError('Cash conservation failed')
            if self.earned_collections != self.gross_collections - self.refunds - sum(self.deposits.values()):
                raise AssertionError('Earned collection reconciliation failed')
            if self.cash < sum(self.deposits.values()) or self.cash < 0:
                raise ValueError('Customer refund custody violated')
            self.history.append({'event': event, 'state': state})
        except Exception:
            self.__dict__ = saved
            raise


def option(config: dict[str, Any], technical_reuse: bool, coordinated: bool) -> dict[str, Any]:
    costs = config['costs']
    if any(v is None for v in costs.values()):
        return {'decision': 'unpriced', 'reason': 'Measured work/cost conversion inputs pending'}
    buyers = [b for b in config['buyers'] if b['price_cents'] <= b['value_cap_cents']]
    participants = buyers if coordinated else buyers[:1]
    p = Fraction(config['common_success_probability'])
    if not 0 <= p <= 1:
        raise ValueError('Invalid qualification probability')
    risk_inputs = []
    for buyer in participants:
        paid = Fraction(buyer['payment_probability'])
        survives = 1 - Fraction(buyer.get('withdrawal_probability', '0'))
        delivered = Fraction(buyer.get('delivery_success_probability', '1'))
        if not all(0 <= probability <= 1 for probability in (paid, survives, delivered)):
            raise ValueError('Invalid payment, withdrawal or delivery probability')
        if not 0 <= buyer['deposit_cents'] <= buyer['price_cents']:
            raise ValueError('Invalid deposit')
        if min(buyer['price_cents'], buyer['delivery_cents'], buyer['support_cents']) < 0:
            raise ValueError('Negative quoted price or delivery cost')
        risk_inputs.append((buyer, paid, survives, delivered))
    fixed = costs['shared_core_cents'] if technical_reuse else costs['independent_setup_cents'] * len(participants)
    delivery = sum(b['delivery_cents'] + b['support_cents'] for b in participants)
    receipts = sum(survives * delivered * (b['deposit_cents'] + paid * (b['price_cents'] - b['deposit_cents']))
                   for b, paid, survives, delivered in risk_inputs)
    expected_delivery = sum(survives * (b['delivery_cents'] + delivered * b['support_cents'])
                            for b, _, survives, delivered in risk_inputs)
    extra = costs['coordination_cents'] if coordinated else 0
    expected = p * (receipts - expected_delivery) - fixed - extra
    prefund = fixed + extra + delivery + config['reserve_cents']
    capacity = config['construction_capacity_units'] + sum(b['capacity_units'] for b in participants)
    admitted = bool(participants) and expected > 0 and config['capital_cents'] >= prefund and config['capacity_units'] >= capacity
    return {'decision': 'produce' if admitted else 'stop', 'technical_reuse': technical_reuse,
            'coordinated': coordinated, 'participants': [b['id'] for b in participants],
            'expected_contribution_cents': str(expected), 'conservative_opening_cash_cents': prefund,
            'required_capacity_units': capacity,
            'construction_cents': fixed, 'coordination_cents': extra,
            'restriction': 'Single binding commitment versus coordinated commitments; diagnostic only',
            'expected_values_are_assumptions': True}


def retention_decision(spec: dict[str, Any]) -> dict[str, Any]:
    cap, uses = Fraction(spec['maximum_delta_cents']), Fraction(spec['forecast_uses'])
    assessment, upkeep = spec['assessment_cents'], spec['additional_lifecycle_cents']
    if min(uses, assessment, upkeep) < 0:
        raise ValueError('Invalid retention input')
    upper = cap * uses - assessment - upkeep
    if cap <= 0 or upper < 1:
        return {'decision': 'reject-before-assessment', 'upper_net_cents': str(upper), 'charge_cents': 0}
    if spec.get('available_cents') is not None and spec['available_cents'] < assessment:
        return {'decision': 'stop-unfunded-assessment', 'charge_cents': 0}
    if spec.get('lower_delta_cents') is None:
        return {'decision': 'assess', 'upper_net_cents': str(upper), 'charge_cents': assessment}
    lower = Fraction(spec['lower_delta_cents'])
    if lower > cap:
        raise ValueError('Evidence lower bound exceeds declared support cap')
    admit = lower > 0 and lower * uses - assessment - upkeep >= 1 and spec.get('fresh_correctness_passed') is True
    return {'decision': 'retain' if admit else 'reject-after-assessment',
            'charge_cents': assessment + (upkeep if admit else 0), 'authority_granted': False}


def replay(config: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    ledger = Ledger(config['reserve_cents'], config['capacity_units'])
    refused = None
    for event in events:
        try:
            ledger.post(event)
        except ValueError as error:
            refused = {'event': event, 'reason': str(error)}
            break
    return {'schema': 'opportunity-economics-ledger/v1', 'evidence_type': 'SIMULATED_SCENARIO',
            'events': ledger.history, 'refused': refused, 'final': ledger.state(),
            'actual_customer_revenue_usd': 0, 'actual_research_profit': None,
            'opportunity_cost_cents': config.get('opportunity_cost_cents'),
            'opportunity_cost_added_to_cash_profit': False,
            'unknowns': ['Real demand', 'Willingness to pay', 'Human-equivalent scope and price',
                         'Realized model and operator cost', 'Contract acceptance', 'Collection behavior']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.scenario.read_text())
    result = replay(config, config['events'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['final'], indent=2))
