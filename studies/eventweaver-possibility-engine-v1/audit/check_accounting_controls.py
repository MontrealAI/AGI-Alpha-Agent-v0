# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
from pathlib import Path

from accounting_reconstruct import audit_history


def row(day: int, debit: str, credit: str, amount: int, kind: str, buyer: str = 'B0') -> dict:
    return dict(day=day, debit=debit, credit=credit, cents=amount, kind=kind, buyer=buyer)


record = {
    'seed': 'accounting-control', 'scenario': 'synthetic_unit_control',
    'journal': [
        row(0, 'cash', 'equity', 1000000, 'equity', ''),
        row(1, 'restricted_cash', 'deposit_liability', 40000, 'deposit'),
        row(2, 'expense:delivery', 'cash', 50000, 'delivery'),
        row(3, 'receivable', 'revenue', 100000, 'acceptance'),
        row(3, 'deposit_liability', 'receivable', 40000, 'deposit_applied'),
        row(3, 'cash', 'restricted_cash', 40000, 'deposit_released'),
        row(4, 'cash', 'receivable', 60000, 'collection'),
    ],
    'lifecycle': [dict(day=1, buyer='B0', status=status)
                  for status in ['inquiry', 'qualified', 'quotation', 'negotiation', 'contract']]
                 + [dict(day=2, buyer='B0', status='execution'),
                    dict(day=3, buyer='B0', status='acceptance'),
                    dict(day=4, buyer='B0', status='collection'),
                    dict(day=10, buyer='B0', status='warranty_closed')],
    'buyers': [dict(id='B0', price=1000, buyer_ex_ante_gain=50)],
    'net_revenue': 1000, 'expenses': 500, 'full_profit': 500,
    'operating_contribution': 500, 'fixed_cost': 0, 'financing_cost': 0,
    'required_capital': 500, 'peak_restricted_cash': 400, 'peak_debt': 0,
    'funding_shortfall': 0, 'final_cash': 10500, 'final_debt': 0, 'final_day': 10,
}
cases = [('valid_balanced_lifecycle', copy.deepcopy(record), True)]
bad = copy.deepcopy(record)
bad['full_profit'] = 501
cases.append(('inflated_profit', bad, False))
bad = copy.deepcopy(record)
bad['journal'][1] = row(1, 'cash', 'revenue', 40000, 'deposit')
cases.append(('deposit_recognized_as_sales', bad, False))
bad = copy.deepcopy(record)
bad['journal'][2] = row(2, 'expense:delivery', 'restricted_cash', 40000, 'delivery')
cases.append(('restricted_deposit_spent', bad, False))
bad = copy.deepcopy(record)
bad['journal'].pop()
cases.append(('missing_final_collection', bad, False))
bad = copy.deepcopy(record)
bad['journal'][3]['cents'] += 100
cases.append(('changed_acceptance_price', bad, False))
bad = copy.deepcopy(record)
bad['lifecycle'] = [item for item in bad['lifecycle'] if item['status'] != 'execution']
cases.append(('acceptance_without_execution', bad, False))
bad = copy.deepcopy(record)
bad['buyers'][0]['buyer_ex_ante_gain'] = -20
cases.append(('buyer_negative_participation', bad, False))
bad = copy.deepcopy(record)
quote = next(item for item in bad['lifecycle'] if item['status'] == 'quotation')
quote.update(outside_options={'internal': 50, 'competitor': 100},
             outside_choice='internal', outside_utility=50)
cases.append(('inferior_outside_option', bad, False))
observations = []
for name, fixture, expected in cases:
    result = audit_history(fixture)
    passed = not result['errors']
    observations.append(dict(name=name, expected_pass=expected, observed_pass=passed,
                             passed=passed == expected, detected_errors=result['errors']))
output = dict(schema='possibility-engine.accounting-adversarial-controls.v1',
              scope='Synthetic auditor controls; not extra commercial experiments.',
              observations=observations, passed=all(item['passed'] for item in observations))
Path(__file__).with_name('accounting_controls.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps({'passed': output['passed'], 'controls': len(observations)}))
raise SystemExit(0 if output['passed'] else 1)
