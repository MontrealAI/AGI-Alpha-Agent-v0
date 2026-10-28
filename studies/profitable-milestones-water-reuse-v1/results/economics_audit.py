# SPDX-License-Identifier: Apache-2.0
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

root = Path(__file__).resolve().parent
D = Decimal
book = defaultdict(lambda: {'cash': D('10000'), 'expense': D(0), 'revenue': D(0), 'receivable': D(0), 'rows': 0})
checks = 0
with (root / 'economics_cash_ledgers.csv').open(newline='') as handle:
    for row in csv.DictReader(handle):
        state = book[(row['scenario'], row['world_id'])]
        for key, delta, total in [('cash', 'cash_delta_usd', 'cash_usd'), ('expense', 'expense_delta_usd', 'expenses_usd'),
                                  ('revenue', 'earned_revenue_delta_usd', 'earned_revenue_usd'),
                                  ('receivable', 'receivable_delta_usd', 'receivables_usd')]:
            state[key] += D(row[delta])
            assert state[key] == D(row[total]), (row['scenario'], row['world_id'], row['event_index'], key)
            checks += 1
        restricted = sum(D(row[key]) for key in ['refundable_deposits_usd', 'payables_usd',
                         'completion_support_reserve_usd', 'remaining_fixed_obligations_usd',
                         'operating_buffer_usd', 'module_maintenance_reserve_usd'])
        assert D(row['cash_usd']) - restricted == D(row['available_funds_usd'])
        assert D(row['available_funds_usd']) >= 0
        checks += 2
        state['rows'] += 1
for state in book.values():
    assert state['cash'] - D(10000) == state['revenue'] - state['expense']
    assert state['receivable'] == 0
    checks += 2
with (root / 'economics_worlds.csv').open(newline='') as handle:
    for row in csv.DictReader(handle):
        state = book[(row['scenario'], row['world_id'])]
        assert state['revenue'] - state['expense'] == D(row['full_project_profit_usd'])
        assert state['cash'] == D(row['terminal_cash_usd'])
        checks += 2
annuity = sum(D('1.12') ** -t for t in range(1, 11))
npv = D(53370) * annuity - D(180000)
report = {'independent_implementation': 'Decimal recomputation from CSV events; no imports from producer',
          'worlds': len(book), 'ledger_rows': sum(state['rows'] for state in book.values()),
          'exact_decimal_checks': checks, 'all_passed': True,
          'plant_npv_eur_decimal': str(npv), 'same_controller_not_institutional_independence': True}
(root / 'economics_audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
