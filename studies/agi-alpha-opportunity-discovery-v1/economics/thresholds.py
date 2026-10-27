# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import json
from fractions import Fraction
from pathlib import Path
from economics import replay, retention_decision


def run() -> dict:
    scenarios = []
    for n in [0, 1, 2, 4, 6]:
        for price in [50000, 80000, 120000]:
            for delivered_cost in [10000, 32500, 70000]:
                for probability in ['1', '9/10', '7/10']:
                    p, pay, stay = Fraction(probability), Fraction(19, 20), Fraction(9, 10)
                    extra = 20000
                    ceiling = p * stay * n * (pay * price - delivered_cost) - extra
                    scenarios.append({'assumed_participants': n, 'assumed_price_cents': price,
                                      'assumed_complete_delivery_cents': delivered_cost,
                                      'assumed_common_success_probability': probability,
                                      'assumed_final_payment_probability': str(pay),
                                      'assumed_participation_survival': str(stay),
                                      'assumed_coordination_cents': extra,
                                      'maximum_fixed_construction_and_extra_retention_cents': str(ceiling),
                                      'interpretation': 'A strictly smaller full fixed cost is needed for positive expected contribution.'})
    illustrative = {'reserve_cents': 50000, 'capacity_units': 1000, 'opportunity_cost_cents': None}
    paths = []
    for shock in ['success', 'default', 'common-failure', 'delay', 'one-withdrawal', 'underfunded']:
        capital = 400000 if shock != 'underfunded' else 100000
        ev = [{'day': 0, 'kind': 'capital', 'amount_cents': capital}]
        for i in range(4):
            ev.append({'day': 1, 'kind': 'deposit', 'party': str(i), 'amount_cents': 10000})
        ev += [{'day': 2, 'kind': 'cost', 'bucket': 'A', 'activity': 'paid-baseline-construction', 'amount_cents': 150000},
               {'day': 2, 'kind': 'cost', 'bucket': 'A', 'activity': 'coordination', 'amount_cents': 20000}]
        for i in range(4):
            who = str(i)
            if shock == 'common-failure' or (shock == 'one-withdrawal' and i == 0):
                ev.append({'day': 3, 'kind': 'refund', 'party': who, 'amount_cents': 10000})
                continue
            ev += [{'day': 4, 'kind': 'cost', 'bucket': 'A', 'activity': who + '-delivery', 'amount_cents': 25000},
                   {'day': 4, 'kind': 'cost', 'bucket': 'A', 'activity': who + '-support', 'amount_cents': 7500},
                   {'day': 5, 'kind': 'accept', 'party': who, 'amount_cents': 80000},
                   {'day': 40 if shock == 'delay' else 10, 'kind': 'default' if shock == 'default' and i == 0 else 'collect',
                    'party': who, 'amount_cents': 70000}]
        paths.append({'shock': shock, 'result': replay(illustrative, sorted(ev, key=lambda x: x['day']))})
    retention = []
    for per_use in [0, 2500, 10000]:
        for uses in [1, 5, 20]:
            spec = {'maximum_delta_cents': per_use, 'forecast_uses': uses, 'assessment_cents': 10000,
                    'additional_lifecycle_cents': 20000, 'lower_delta_cents': None,
                    'fresh_correctness_passed': True, 'available_cents': 100000}
            retention.append({'assumptions': spec, 'decision': retention_decision(spec)})
    return {'schema': 'evidence-continuity-economic-boundaries/v1', 'evidence_type': 'ASSUMED_SCENARIOS_EXECUTED_EXACTLY',
            'actual_customer_revenue_usd': 0, 'complete_actual_profit': None,
            'source_of_prices': 'Hypothetical quote grid, not measured willingness-to-pay or market prices',
            'human_reference': {'estimated_hours_range': [4, 12], 'assumed_hourly_service_rate_usd': [100, 200],
                                'estimated_scope': 'Reconstruct and independently check a small reproducible numerical evidence packet',
                                'observed_quote': False, 'limitations': 'Editorial adjudication, inaccessible sources and complete systematic-review update excluded'},
            'model_cost_sensitivity': {'gpt-6-astra_standard_usd_per_million_input_output': [10,50],
                                       'gpt-6.1-terra_standard_usd_per_million_input_output': [1,5],
                                       'example_tokens_input_output': [60000,10000],
                                       'example_astra_token_cost_usd': 1.1, 'example_terra_token_cost_usd': .11,
                                       'tokens_are_assumed': True, 'all_tools_corrections_overhead_still_required': True},
            'thresholds': scenarios, 'cash_paths': paths, 'retention_reachability': retention,
            'same_content_library': 'Identical technical outcomes; no graph-specific revenue or benefit added',
            'unrestricted_expert': 'May use identical instrument and arrangement; no exclusive frontier crossing established',
            'decision': 'Do not admit incremental monetary Alpha or finance expansion from unmeasured savings',
            'next_measurement': 'Complete reconstruction/adaptation effort and buyer acceptance, with strong expert tools'}


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=run();a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'threshold_scenarios':len(result['thresholds']), 'cash_paths':len(result['cash_paths']),
                      'retention_cases':len(result['retention_reachability']), 'actual_customer_revenue_usd':0}))
