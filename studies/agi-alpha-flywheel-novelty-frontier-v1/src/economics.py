# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, hashlib, json, math, random, statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

def read(path: Path) -> Any:
    return json.loads(path.read_text())

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')

def spread(values: list[float]) -> dict[str, float]:
    v = sorted(values)
    def percentile(p: float) -> float:
        at = (len(v) - 1) * p
        lo = int(at)
        return v[lo] + (v[min(lo + 1, len(v) - 1)] - v[lo]) * (at - lo)
    return {'mean': statistics.fmean(v), 'p05': percentile(.05), 'p50': percentile(.5), 'p95': percentile(.95),
            'minimum': v[0], 'maximum': v[-1], 'negative_worlds': sum(x < 0 for x in v), 'worlds': len(v)}

def worlds(cfg: dict, amendment: dict, scenario: str, seed: int, count: int) -> list[dict]:
    rng = random.Random(seed + list(cfg['scenario']).index(scenario) * 100003)
    s = cfg['scenario'][scenario]
    def factor(sigma: float) -> float:
        return rng.lognormvariate(-sigma * sigma / 2, sigma)
    output = []
    for ident in range(count):
        demand = factor(amendment['world_demand_lognormal_sigma'])
        unit_cost = s['unit_cost'] * factor(amendment['unit_cost_lognormal_sigma'])
        buyers = []
        for _ in range(s['potential_buyers']):
            loss = s['exposure_rate'] * s['avoidable_loss'] * factor(amendment['loss_value_lognormal_sigma'])
            value = loss * cfg['performance_conditional']['prevented_loss_fraction'] + s['staff_saving'] - s['false_alarm_rate'] * s['false_alarm_cost']
            manual = amendment['manual_outside_option']
            outside = max(0, loss * manual['loss_avoidance_fraction'] + s['staff_saving'] * manual['staff_saving_fraction'] - manual['cost_per_unit_usd'])
            volume = max(0, round(s['annual_units_per_buyer'] * demand * factor(amendment['buyer_volume_lognormal_sigma'])))
            buyers.append({'incremental_value': max(0, value - outside), 'device_value': value, 'outside_value': outside,
                           'volume': volume, 'reachable': rng.random() < amendment['buyer_reachability_probability']})
        output.append({'id': ident, 'buyers': buyers, 'unit_cost': unit_cost,
                       'qualified': rng.random() < s['qualified_device_probability']})
    return output

def rd(cfg: dict, amendment: dict, band: str, reduction: float | None) -> dict:
    wage = cfg['wage_cad_hour'][band] * cfg['loaded_multiplier'][band] / cfg['fx_cad_per_usd']
    hours = cfg['human_engineering_hours'][band] * (1 - (reduction or 0))
    engineering = hours * wage
    testing = cfg['physical_test_hours'][band] * cfg['technician_usd_hour'][band]
    external = cfg['prototype_tooling_external_tests_usd'][band]
    plan = cfg['inference_plan']
    inference = 0 if reduction is None else plan['input_mtokens'] * plan['input_usd_per_mtoken'] + plan['output_mtokens'] * plan['output_usd_per_mtoken'] + plan['tool_compute_usd']
    direct = engineering + testing + external + inference
    finance = direct * cfg['finance_annual_rate'] * amendment['development_months'][band] / 24
    return {'band': band, 'engineering_hour_reduction_assumed': reduction, 'loaded_engineer_usd_hour': wage,
            'engineering_hours': hours, 'engineering_cost': engineering, 'physical_test_hours': cfg['physical_test_hours'][band],
            'physical_test_cost': testing, 'external_prototype_tooling_tests': external, 'inference_tools': inference,
            'research_finance': finance, 'A_originating_research_total': direct + finance,
            'failed_screen_cost_already_inside_engineering': engineering * amendment['engineering_hours_included_failed_screen_fraction'],
            'duration_months_assumed': amendment['development_months'][band], 'paid_customer_learning': False}

def operate(cfg: dict, amendment: dict, scenario: str, world: dict, listed_price: float, policy: str,
            demand_multiplier: float = 1, cost_multiplier: float = 1) -> dict:
    s = cfg['scenario'][scenario]
    deposit = .2 if policy == 'deposit20_discount5' else 0
    price = listed_price * (.95 if deposit else 1)
    financing_burden = price * deposit * amendment['buyer_discount_rate'] * amendment['deposit_lead_days'] / 365
    cap = cfg['performance_conditional']['participation_value_share_cap']
    eligible = [b for b in world['buyers'] if b['reachable'] and b['incremental_value'] * cap >= price + financing_burden]
    quantities = [max(0, round(b['volume'] * demand_multiplier)) for b in eligible]
    total_requested = sum(quantities)
    scale = min(1, cfg['annual_capacity'] / total_requested) if total_requested else 0
    allocations = [math.floor(q * scale) for q in quantities]
    units = sum(allocations)
    customers = sum(q > 0 for q in allocations)
    revenue = price * units
    production = world['unit_cost'] * cost_multiplier * units
    acquisition = customers * s['acquisition_per_buyer']
    overhead = s['fixed_overhead']
    warranty = revenue * amendment['expected_warranty_expense_fraction_of_sales']
    reserve = revenue * cfg['warranty_reserve_fraction_of_sales']
    credit_loss = revenue * (1 - deposit) * cfg['credit_loss_fraction']
    collected = revenue - credit_loss
    cash = debt = max_debt = interest = restricted = accrued_warranty = pending_credit = 0.0
    months = cfg['months']
    for month in range(1, months + 2):
        finance_charge = debt * cfg['finance_annual_rate'] / 12
        interest += finance_charge
        cash -= finance_charge
        cash += pending_credit * (1 - cfg['credit_loss_fraction'])
        pending_credit = 0
        if month <= months:
            sales = revenue / months
            deposit_liability = sales * deposit
            cash += deposit_liability
            cash -= production / months + overhead / months + (acquisition if month == 1 else 0)
            deposit_liability = 0
            pending_credit = sales * (1 - deposit)
            current_warranty = warranty / months
            cash -= current_warranty * amendment['warranty_payment_fraction_during_delivery']
            accrued_warranty += current_warranty * (1 - amendment['warranty_payment_fraction_during_delivery'])
            restricted += reserve / months
        else:
            cash -= accrued_warranty
            accrued_warranty = 0
        available = cash - restricted - accrued_warranty
        if available < 0:
            draw = -available
            debt += draw
            cash += draw
            max_debt = max(max_debt, debt)
        elif debt:
            repay = min(debt, available)
            debt -= repay
            cash -= repay
    costs = production + acquisition + overhead + warranty + credit_loss + interest
    profit = revenue - costs
    buyer_surplus = sum(q * (b['incremental_value'] - price - financing_burden) for b, q in zip(eligible, allocations))
    buyer_value = sum(q * b['incremental_value'] for b, q in zip(eligible, allocations))
    if abs((cash - debt) - profit) > 1e-6:
        raise AssertionError('Cash, debt and profit do not reconcile')
    if units > cfg['annual_capacity'] or buyer_surplus < -1e-6:
        raise AssertionError('Capacity or buyer participation violated')
    return {'world_id': world['id'], 'physically_qualified_sample': world['qualified'], 'listed_price': listed_price,
            'effective_price': price, 'payment_policy': policy, 'customers': customers, 'units': units,
            'demand_before_capacity': total_requested, 'gross_recognized_revenue': revenue, 'collections': collected,
            'production_cost': production, 'cost_components': {k: production * v for k, v in cfg['cost_components'].items()},
            'acquisition': acquisition, 'overhead': overhead, 'warranty_expense': warranty, 'warranty_cash_reserve': reserve,
            'credit_loss': credit_loss, 'finance_expense': interest, 'contribution_before_overhead_finance': revenue - production - acquisition - warranty - credit_loss,
            'qualified_annual_operating_profit': profit, 'cash_after_runoff': cash, 'credit_debt_after_runoff': debt,
            'peak_revolving_credit': max_debt, 'available_after_reserve_and_debt': cash - reserve - debt,
            'customer_incremental_value': buyer_value, 'customer_surplus_after_outside_option_price_and_prepayment': buyer_surplus,
            'same_offering_quality_assumption': 'All delivered units accepted conditional on physical qualification; warranty costs remain explicit, acceptance is unobserved'}

def summarise(rows: list[dict]) -> dict:
    keys = ['units', 'customers', 'gross_recognized_revenue', 'collections', 'production_cost', 'acquisition', 'overhead',
            'warranty_expense', 'warranty_cash_reserve', 'credit_loss', 'finance_expense', 'contribution_before_overhead_finance',
            'qualified_annual_operating_profit', 'peak_revolving_credit', 'available_after_reserve_and_debt',
            'customer_incremental_value', 'customer_surplus_after_outside_option_price_and_prepayment']
    return {key: spread([r[key] for r in rows]) for key in keys}

def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['develop', 'confirm'], required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'results')
    args = parser.parse_args()
    cfg_path = ROOT / 'config/economics.json'
    amendment_path = ROOT / 'results/economics-amendment-v1.json'
    cfg, amendment = read(cfg_path), read(amendment_path)
    hashes = {'config': digest(cfg_path), 'amendment': digest(amendment_path), 'source': digest(Path(__file__))}
    out = args.output_dir
    band = amendment['primary_rd_band']
    a0 = rd(cfg, amendment, band, 0)['A_originating_research_total']
    if abs(sum(cfg['cost_components'].values()) - 1) > 1e-12:
        raise ValueError('Cost-component fractions must sum to one')
    if args.phase == 'develop':
        candidates, selected = {}, {}
        for scenario, s in cfg['scenario'].items():
            draws = worlds(cfg, amendment, scenario, cfg['development_seed'], amendment['development_worlds'])
            table = []
            for price in cfg['price_grid']:
                for policy in cfg['policies']:
                    observations = [operate(cfg, amendment, scenario, w, price, policy) for w in draws]
                    mean = statistics.fmean(r['qualified_annual_operating_profit'] for r in observations)
                    table.append({'price': price, 'policy': policy, 'mean_qualified_operating_profit': mean,
                                  'mean_units': statistics.fmean(r['units'] for r in observations),
                                  'expected_predevelopment_profit': s['qualified_device_probability'] * mean - a0})
            best = max(table, key=lambda r: (r['mean_qualified_operating_profit'], -r['price'], r['policy']))
            candidates[scenario] = table
            selected[scenario] = {**best, 'conditional_investment_decision': 'LAUNCH_IF_ASSUMPTIONS_HOLD' if best['expected_predevelopment_profit'] > 0 else 'HOLD',
                                  'actual_decision': 'HOLD_UNQUALIFIED_PHYSICAL_OFFERING_AND_FAILED_NOVELTY'}
        save(out / 'economics-development.json', {'hashes': hashes, 'seed': cfg['development_seed'], 'worlds_per_candidate': amendment['development_worlds'], 'candidates': candidates})
        save(out / 'economics-policy-freeze.json', {'freeze_utc': datetime.now(timezone.utc).isoformat(), 'hashes': hashes,
             'ordering': 'Saved before independent-seed confirmation', 'selected': selected, 'research_cost_primary': rd(cfg, amendment, band, 0)})
        print(json.dumps(selected, indent=2))
        return
    freeze = read(out / 'economics-policy-freeze.json')
    if freeze['hashes'] != hashes:
        raise ValueError('Frozen source/config/amendment changed; preserve history and create a new prospective edition')
    results, raw, sensitivities = {}, {}, {}
    maximum_reconciliation_error = 0.0
    for scenario, s in cfg['scenario'].items():
        policy = freeze['selected'][scenario]
        draws = worlds(cfg, amendment, scenario, cfg['confirmation_seed'], cfg['confirmation_worlds'])
        rows = [operate(cfg, amendment, scenario, w, policy['price'], policy['policy']) for w in draws]
        q = s['qualified_device_probability']
        prof = statistics.fmean(r['qualified_annual_operating_profit'] for r in rows)
        comparisons = []
        for rd_band in ['low', 'central', 'high']:
            for reduction in [None, *amendment['engineering_hour_reduction_fractions']]:
                rdc = rd(cfg, amendment, rd_band, reduction)
                a = rdc['A_originating_research_total']
                label = 'H_human_led' if reduction is None else 'E_no_benefit' if reduction == 0 else f'E_hypothetical_{int(reduction*100)}pct_engineering_hours_saved'
                comparisons.append({'configuration': label, 'rd': rdc, 'expected_predevelopment_profit': q * prof - a,
                                    'q_break_even': a / prof if prof > 0 else None,
                                    'q_break_even_feasible': prof > a,
                                    'sampled_project_profit': spread([(r['qualified_annual_operating_profit'] if r['physically_qualified_sample'] else 0) - a for r in rows])})
        for r in rows:
            expected = r['gross_recognized_revenue'] - math.fsum([r['production_cost'], r['acquisition'], r['overhead'], r['warranty_expense'], r['credit_loss'], r['finance_expense']])
            maximum_reconciliation_error = max(maximum_reconciliation_error, abs(expected-r['qualified_annual_operating_profit']), abs(sum(r['cost_components'].values())-r['production_cost']))
        rows_sensitivity = []
        for dm in amendment['demand_multipliers']:
            for cm in amendment['unit_cost_multipliers']:
                stress = [operate(cfg, amendment, scenario, w, policy['price'], policy['policy'], dm, cm) for w in draws]
                annual = statistics.fmean(r['qualified_annual_operating_profit'] for r in stress)
                rows_sensitivity.append({'demand_multiplier': dm, 'unit_cost_multiplier': cm, 'mean_qualified_operating_profit': annual,
                                         'expected_predevelopment_profit_E0_central': q * annual - a0,
                                         'annual_profit_p05': spread([r['qualified_annual_operating_profit'] for r in stress])['p05'],
                                         'mean_units': statistics.fmean(r['units'] for r in stress)})
        sensitivities[scenario] = rows_sensitivity
        raw[scenario] = rows
        results[scenario] = {'frozen_policy': policy, 'qualification_probability_assumed': q, 'conditional_qualified_operation': summarise(rows),
                             'research_pathways': comparisons, 'conditional_predevelopment_E0_central': q * prof - a0,
                             'sampled_physical_failures': sum(not r['physically_qualified_sample'] for r in rows),
                             'all_active_worlds_retained': len(rows), 'zero_sales_worlds': sum(r['units'] == 0 for r in rows),
                             'forward_HOLD_avoids_future_costs_only': True,
                             'capital_required_E0_central': spread([a0 + r['peak_revolving_credit'] for r in rows]),
                             'robust_tested_cells': [r for r in rows_sensitivity if r['expected_predevelopment_profit_E0_central'] > 0 and r['annual_profit_p05'] > 0]}
    b = cfg['extra_retention_usd'] + cfg['extra_maintenance_annual_usd']
    output = {'schema': 'agi-alpha.novelty-frontier.economics-results.v1', 'hashes': hashes, 'freeze': freeze,
              'actual': cfg['actual'], 'actual_decision': 'HOLD_UNQUALIFIED_PHYSICAL_OFFERING_AND_FAILED_NOVELTY',
              'currency': cfg['currency'], 'scenario_spreads_are_not_empirical_confidence_intervals': True,
              'confirmation_seed': cfg['confirmation_seed'], 'worlds_per_scenario': cfg['confirmation_worlds'], 'results': results,
              'retention': {'observed_incremental_gain': 0, 'ordinary_identical_library_incremental_gain': 0,
                            'B_extra_extraction_validation_retention': cfg['extra_retention_usd'], 'B_annual_maintenance': cfg['extra_maintenance_annual_usd'],
                            'B_total': b, 'modeled_net_increment_at_observed_gain': -b, 'decision': 'REJECT',
                            'required_saving_per_future_mission': b/amendment['retention_future_missions'], 'assumed_future_missions': amendment['retention_future_missions'],
                            'C_optional_Gym': cfg['optional_gym_usd']},
              'arithmetic_checks': {'maximum_float_reconciliation_error_usd': maximum_reconciliation_error,
                                    'passed': maximum_reconciliation_error < 1e-6, 'worlds_checked': sum(len(v) for v in raw.values()),
                                    'independent_checks': ['Revenue minus separately summed expenses', 'Cash minus outstanding credit equals operating profit', 'Production subcomponents sum to production cost', 'Capacity bound', 'Every participating customer has nonnegative incremental surplus', 'All A/B/C costs charged once', 'No actual receipt created']},
              'equations': {'value': 'device = exposure * avoidable_loss * .7 + staff_saving - false_alarm_rate * false_alarm_cost',
                            'participation': 'effective_price + deposit_opportunity_cost <= .7 * max(0, device_value - max(0, manual_value))',
                            'profit': 'gross accepted sales - production - acquisition - overhead - warranty expense - credit loss - finance',
                            'predevelopment': 'q * mean qualified annual operating profit - A originating research including finance',
                            'qualification_threshold': 'q_break_even = A / mean qualified annual operating profit, feasible only below one',
                            'retention': 'incremental mission savings - additional B cost; C optional investment stays separate'},
              'methods_note': ['All economics concern the same hypothetical physically qualified four-event chronology device. Abstract pairwise/parity success supplies no physical qualification, demand, or expected-loss calibration.',
                               'A contains originating research, including an assumed 15% engineering share for failed screens; it is unpaid construction, not paid-job learning. Low/central/high pathways preserve physical test work and external tooling.',
                               'Prices and payment policies were selected on 128 development worlds and frozen before 512 independent-seed confirmation worlds per scenario. Both actual HOLD and hypothetical active-offer losses remain visible.',
                               'The H/E quality and commercial distributions are identical. E0 adds inference expense with no assumed labor gain. 25% and 50% engineer-hour savings are sensitivity assumptions only; physical work is unchanged.',
                               'Credit funding is an assumed available revolving facility. Principal is not revenue; outstanding debt and reserve restrictions are retained. Deposit cash is a liability until acceptance, which is only assumed in the qualified-offering branch.',
                               'The 2% expected warranty expense reduces profit; the separate 3% warranty cash reserve restricts liquidity but is not charged again as expense. Runoff collects final receivables and pays accrued expected warranty liabilities.',
                               'All physical failures and economic losses are retained. Spreads measure uncertainty inside constructed scenarios, not statistical confidence about real customers.',
                               'The smallest useful next step is a rights-cleared physical realization and order-recovery test, then one scoped buyer value/price interview; neither is established by this model.']}
    save(out/'economics-worlds.json', {'evidence_class': 'simulated conditional offering worlds', 'worlds': raw})
    save(out/'economics-sensitivity.json', {'frozen_prices': freeze['selected'], 'grid': sensitivities})
    save(out/'economics-results.json', output)
    print(json.dumps({s: {'price': v['frozen_policy']['price'], 'policy': v['frozen_policy']['policy'],
                         'annual_operating_mean': v['conditional_qualified_operation']['qualified_annual_operating_profit']['mean'],
                         'predevelopment_E0_central': v['conditional_predevelopment_E0_central'],
                         'robust_cells': len(v['robust_tested_cells'])} for s,v in results.items()},indent=2))

if __name__ == '__main__':
    run()
