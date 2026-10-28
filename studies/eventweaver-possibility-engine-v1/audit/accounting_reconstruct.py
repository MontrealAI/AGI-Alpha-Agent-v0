# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Iterator


def cents(value: Any) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN))


def histories(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        if '.jsonl' in path.name:
            for line in stream:
                if line.strip():
                    yield json.loads(line)
        else:
            value = json.load(stream)
            if isinstance(value, list):
                yield from value
            elif 'histories' in value:
                yield from value['histories']
            else:
                yield value


def audit_history(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: Counter[str] = Counter()
    balances: defaultdict[str, int] = defaultdict(int)
    by_buyer: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    flow = peak_capital = peak_restricted = peak_debt = 0
    initial_equity = rescue_equity = 0
    prior_day = -1

    def require(ok: bool, name: str, message: str) -> None:
        checks[name] += 1
        if not ok:
            errors.append(message)

    journal = record.get('journal')
    if not isinstance(journal, list):
        return {'seed': record.get('seed'), 'errors': ['No detailed journal'], 'checks': {}}
    for index, row in enumerate(journal):
        day, debit, credit, amount = (row.get(k) for k in ['day', 'debit', 'credit', 'cents'])
        kind, buyer = row.get('kind', ''), row.get('buyer', '')
        require(isinstance(day, (int, float)) and day >= prior_day, 'chronology', f'Row{index}: order')
        prior_day = day
        valid = isinstance(amount, int) and not isinstance(amount, bool) and amount > 0
        require(valid, 'positive_integer_cents', f'Row{index}: invalid amount')
        if not valid:
            continue
        require(isinstance(debit, str) and isinstance(credit, str) and debit != credit,
                'account_names', f'Row{index}: malformed accounts')
        balances[debit] += amount
        balances[credit] -= amount
        by_buyer[buyer][debit] += amount
        by_buyer[buyer][credit] -= amount
        if debit == 'cash' and kind not in {'equity', 'rescue_equity', 'loan_draw'}:
            flow += amount
        if credit == 'cash' and kind != 'loan_repay':
            flow -= amount
        if kind in {'equity', 'rescue_equity'}:
            require((debit, credit) == ('cash', 'equity'), 'financing_classification',
                    f'Row{index}: equity misclassified')
            if kind == 'equity':
                initial_equity += amount
            else:
                rescue_equity += amount
        if kind == 'loan_draw':
            require((debit, credit) == ('cash', 'debt'), 'financing_classification',
                    f'Row{index}: borrowing misclassified')
        if kind == 'loan_repay':
            require((debit, credit) == ('debt', 'cash'), 'financing_classification',
                    f'Row{index}: principal repayment expensed')
        peak_capital = max(peak_capital, -flow)
        peak_restricted = max(peak_restricted, balances['restricted_cash'])
        peak_debt = max(peak_debt, -balances['debt'])
        require(sum(balances.values()) == 0, 'double_entry', f'Row{index}: unbalanced journal')
        require(balances['cash'] >= 0, 'unrestricted_cash_nonnegative', f'Row{index}: negative cash')
        require(balances['restricted_cash'] >= 0, 'restricted_cash_nonnegative',
                f'Row{index}: negative restricted cash')
        require(balances['deposit_liability'] <= 0 and balances['restricted_cash'] >= -balances['deposit_liability'],
                'deposit_custody', f'Row{index}: deposit backing mismatch')
        require(balances['receivable'] >= 0, 'receivable_nonnegative',
                f'Row{index}: negative receivable')
        require(balances['debt'] <= 0, 'debt_nonpositive', f'Row{index}: overpaid debt')
        require(by_buyer[buyer]['receivable'] >= 0, 'buyer_receivable_nonnegative',
                f'Row{index}: negative buyer receivable {buyer}')
        if debit == 'restricted_cash':
            require(credit == 'deposit_liability', 'deposit_no_revenue',
                    f'Row{index}: refundable deposit treated as revenue')
        if credit == 'restricted_cash':
            require(debit in {'deposit_liability', 'cash'}, 'restricted_use',
                    f'Row{index}: restricted cash funds expenses')
        if credit == 'revenue':
            require(debit == 'receivable', 'revenue_recognition',
                    f'Row{index}: revenue not tied to receivable milestone')
        if kind in {'collection', 'renewal_collection'}:
            require((debit, credit) == ('cash', 'receivable'), 'collection_not_resale',
                    f'Row{index}: collection recognized twice')

    net_revenue = -balances['revenue'] - balances['contra_revenue']
    expenses = sum(value for name, value in balances.items() if name.startswith('expense:'))
    fixed = sum(value for name, value in balances.items() if name.startswith('expense:fixed_'))
    financing = balances['expense:financing']
    profit = net_revenue - expenses
    reconstructed = {
        'net_revenue': net_revenue, 'expenses': expenses, 'full_profit': profit,
        'fixed_cost': fixed, 'financing_cost': financing,
        'operating_contribution': profit + fixed + financing,
        'required_capital': peak_capital, 'peak_restricted_cash': peak_restricted,
        'peak_debt': peak_debt, 'funding_shortfall': rescue_equity,
        'final_cash': balances['cash'], 'final_debt': -balances['debt'],
    }
    for name, value in reconstructed.items():
        if name in record:
            require(abs(cents(record[name]) - value) <= 1, 'reported_money_reconstruction',
                    f'{name}: reported {record[name]} versus independent {value / 100}')
    if 'accounts' in record:
        for name in set(balances) | set(record['accounts']):
            require(balances[name] == record['accounts'].get(name, 0), 'all_account_reconstruction',
                    f'Account{name}: mismatch')
    for account in ['restricted_cash', 'deposit_liability', 'receivable']:
        require(balances[account] == 0, 'terminal_commercial_closure', f'Unclosed {account}')
    require(balances['cash'] + balances['debt'] - initial_equity - rescue_equity == profit,
            'cash_profit_equity_bridge', 'Cash, debt, capital and profit do not reconcile')
    if balances['debt']:
        warnings.append(f'Terminal debt remains {(-balances["debt"]) / 100:.2f}; financing not closed')
    if rescue_equity:
        warnings.append(f'Emergency equity {rescue_equity / 100:.2f}; fixed capital ceiling exceeded')

    lifecycle: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    counts: Counter[str] = Counter()
    for item in record.get('lifecycle', []):
        lifecycle[item['buyer']].append(item)
        counts[item['status']] += 1
    mapping = {'accepted': 'acceptance', 'contracts': 'contract', 'quotes': 'quotation',
               'inquiries': 'inquiry', 'qualified': 'qualified', 'pool_expired': 'pool_expired',
               'initial_refusals': 'initial_refusal', 'final_refusals': 'final_refusal',
               'defaults': 'default', 'warranty_refunds': 'warranty_refund', 'renewals': 'renewal_acceptance'}
    for output, status in mapping.items():
        if output in record:
            require(record[output] == counts[status], 'lifecycle_count_reconstruction',
                    f'{output}: output not reconstructed from lifecycle')
    buyers = {buyer['id']: buyer for buyer in record.get('buyers', [])}
    for buyer, states in lifecycle.items():
        statuses = {item['status'] for item in states}
        days = {status: min(item['day'] for item in states if item['status'] == status)
                for status in statuses}
        if 'contract' in statuses:
            require({'qualified', 'quotation', 'negotiation'} <= statuses, 'contract_prior_steps',
                    f'{buyer}: contract bypasses qualification/quote/negotiation')
            require(days['contract'] >= days.get('negotiation', math.inf), 'contract_chronology',
                    f'{buyer}: contract predates negotiation')
        if 'acceptance' in statuses:
            require('execution' in statuses and days['acceptance'] >= days.get('execution', math.inf),
                    'acceptance_after_execution', f'{buyer}: accepted before execution')
            require('final_refusal' not in statuses, 'exclusive_terminal_delivery',
                    f'{buyer}: accepted and finally refused')
            rows = [row for row in journal if row['buyer'] == buyer and row['kind'] == 'acceptance']
            require(len(rows) == 1, 'acceptance_invoice_once', f'{buyer}: invoice count')
            if buyer in buyers and rows:
                require(abs(rows[0]['cents'] - cents(buyers[buyer]['price'])) <= 1,
                        'contract_price_preserved', f'{buyer}: invoice changes agreed price')
        if 'renewal_acceptance' in statuses:
            require('renewal_quotation' in statuses and 'acceptance' in statuses,
                    'renewal_basis', f'{buyer}: renewal without original delivery and quote')
            require(days.get('warranty_closed', math.inf) <= days['renewal_acceptance'],
                    'renewal_after_warranty', f'{buyer}: original warranty sold twice')
        for quotation in (item for item in states if item['status'] == 'quotation'):
            options = (quotation.get('outside_options') or quotation.get('outside_utilities')
                       or quotation.get('alternatives'))
            if options:
                selected = quotation['outside_choice']
                require(selected in options and options[selected] >= max(options.values()) - 0.011,
                        'buyer_best_outside_option', f'{buyer}: inferior outside option selected')
                require(abs(options[selected] - quotation['outside_utility']) <= 0.011,
                        'buyer_outside_value', f'{buyer}: wrong selected alternative value')
                required = {'gross_value', 'urgency', 'internal_hours', 'review',
                            'outside_hours_factor', 'competitor_quote', 'buyer_hourly_rate'}
                if required <= quotation.keys():
                    gross, urgency, hours, review = (quotation[key] for key in
                                                    ['gross_value', 'urgency', 'internal_hours', 'review'])
                    factor, competitor, hourly = (quotation[key] for key in
                                                  ['outside_hours_factor', 'competitor_quote', 'buyer_hourly_rate'])
                    computed = {
                        'internal_ai': .94 * gross - hours * factor * hourly - review - 14 * urgency,
                        'free_tools': .91 * gross - (hours + 4) * factor * hourly - review - 21 * urgency,
                        'competitor': .96 * gross - competitor - review - 7 * urgency,
                        'wait': .72 * gross - .8 * min(competitor, hours * factor * hourly) - review - 30 * urgency,
                        'do_nothing': 0.0,
                    }
                    for name, value in computed.items():
                        require(name in options and abs(options[name] - value) < 1e-7,
                                'outside_utility_independent_recomputation', f'{buyer}: utility {name} mismatch')
                else:
                    checks['outside_raw_inputs_unavailable'] += 1
                required = {'gross_value', 'review', 'expected_wait', 'urgency', 'trust',
                            'rights_cost', 'setup_extra', 'reservation_price'}
                if required <= quotation.keys():
                    reserve = (.94 * quotation['gross_value'] - quotation['review']
                               - quotation['expected_wait'] * quotation['urgency'] - quotation['trust']
                               - quotation['rights_cost'] - quotation['setup_extra'] - max(options.values()))
                    require(abs(reserve - quotation['reservation_price']) < 1e-7,
                            'buyer_reservation_price', f'{buyer}: reservation price mismatch')
                    if 'buyer_bid' in quotation:
                        require(quotation['buyer_bid'] <= reserve + 1e-7, 'buyer_bid_feasible',
                                f'{buyer}: buyer bids above private participation limit')
                    if 'offered_price' in quotation and 'posted_price' in quotation and 'buyer_bid' in quotation:
                        expected = (round(quotation['buyer_bid'], 2)
                                    if quotation['buyer_bid'] >= quotation['posted_price'] * .92
                                    else quotation['posted_price'])
                        require(abs(quotation['offered_price'] - expected) < .011,
                                'public_negotiation_policy', f'{buyer}: seller price deviates from stated bid rule')
            else:
                checks['outside_option_recomputation_unavailable'] += 1
        for negotiation in (item for item in states if item['status'] == 'negotiation'):
            if 'seller_minimum_price' in negotiation:
                require(negotiation['price'] >= negotiation['seller_minimum_price'] - .011,
                        'seller_incremental_cost_gate', f'{buyer}: below seller minimum price')
            if 'committed_cost' in negotiation and 'capital_limit' in negotiation:
                require(negotiation['committed_cost'] <= negotiation['capital_limit'] + .011,
                        'prospective_funding_gate', f'{buyer}: commitments exceed declared funding limit')
        if buyer in buyers:
            gain = buyers[buyer].get('buyer_ex_ante_gain')
            if gain is not None:
                require(gain >= -0.011, 'buyer_participation', f'{buyer}: negative declared buyer utility gain')
    if record.get('human_hours_by_task'):
        require(abs(sum(record['human_hours_by_task'].values()) - record['human_hours']) < 1e-7,
                'human_hours_reconstruction', 'Human hours do not match task sums')
    full_last_day = max([prior_day] + [item['day'] for item in record.get('lifecycle', [])])
    if record.get('final_day', full_last_day) < full_last_day:
        warnings.append('Reported final_day precedes last recorded lifecycle obligation')
    return {
        'seed': record.get('seed'), 'scenario': record.get('scenario'), 'journal_entries': len(journal),
        'checks': dict(checks), 'errors': errors, 'warnings': warnings,
        'reconstructed_usd': {name: value / 100 for name, value in reconstructed.items()},
        'initial_equity_usd': initial_equity / 100, 'rescue_equity_usd': rescue_equity / 100,
        'lifecycle_last_day': full_last_day,
    }


def run(paths: list[Path], output: Path, summary: Path | None = None) -> dict[str, Any]:
    total_checks: Counter[str] = Counter()
    errors, warnings, inputs = [], [], []
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    count = entry_count = 0
    for path in paths:
        inputs.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for record in histories(path):
            result = audit_history(record)
            count += 1
            entry_count += result.get('journal_entries', 0)
            total_checks.update(result['checks'])
            groups[str(result.get('scenario'))].append(result)
            context = {'seed': result.get('seed'), 'scenario': result.get('scenario'), 'path': str(path)}
            errors.extend(dict(context, message=message) for message in result['errors'])
            warnings.extend(dict(context, message=message) for message in result.get('warnings', []))
    summaries = {}
    for name, group in groups.items():
        profits = [row['reconstructed_usd']['full_profit'] for row in group if 'reconstructed_usd' in row]
        if profits:
            summaries[name] = {'histories': len(group), 'mean_full_profit': statistics.mean(profits),
                               'loss_probability': sum(profit < 0 for profit in profits) / len(profits)}
    if summary:
        published = json.loads(summary.read_text())
        for name, reconstructed in summaries.items():
            official = published.get('summaries', {}).get(name)
            if official and official.get('runs') == reconstructed['histories']:
                total_checks['scenario_mean_reconstruction'] += 1
                if abs(official['full_profit']['mean'] - reconstructed['mean_full_profit']) > 0.011:
                    errors.append({'scenario': name, 'message': 'Scenario mean profit mismatch'})
                total_checks['scenario_loss_probability_reconstruction'] += 1
                if abs(official['loss_probability']['estimate'] - reconstructed['loss_probability']) > 1e-12:
                    errors.append({'scenario': name, 'message': 'Scenario loss frequency mismatch'})
            else:
                warnings.append({'scenario': name, 'message': 'Incomplete scenario coverage; summary not certified'})
    result = {
        'schema': 'possibility-engine.independent-accounting-audit.v1',
        'method': 'Independent integer-cent journal reconstruction; no business.py import or simulator execution.',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'input_files': inputs, 'histories_audited': count, 'journal_entries_audited': entry_count,
        'checks': dict(total_checks), 'errors': errors, 'warnings': warnings,
        'scenario_reconstruction': summaries, 'passed': not errors,
        'limits': 'Arithmetic/lifecycle audit does not validate demand, WTP, costs, causality or physical performance.',
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('inputs', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args()
    result = run(args.inputs, args.output, args.summary)
    print(json.dumps({'passed': result['passed'], 'histories': result['histories_audited'],
                      'journal_entries': result['journal_entries_audited'], 'errors': len(result['errors']),
                      'warnings': len(result['warnings'])}))
    raise SystemExit(0 if result['passed'] else 1)
