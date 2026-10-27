# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import json
from fractions import Fraction
from pathlib import Path

def assess_bound(maximum_delta_cents: str, uses: str, lifecycle_cents: int,
                 assessment_cents: int, risk_cents: str = '0', minimum_net_cents: int = 1) -> dict:
    cap, horizon, risk = (Fraction(x) for x in (maximum_delta_cents, uses, risk_cents))
    if min(horizon, risk, lifecycle_cents, assessment_cents, minimum_net_cents) < 0:
        raise ValueError('Negative costs, horizon, risk or threshold')
    upper_per_use = cap - risk
    upper_net = upper_per_use * horizon - lifecycle_cents - assessment_cents
    threshold = max(1, minimum_net_cents)
    return {
        'schema': 'prospective-admission-reachability/v1',
        'upper_per_use_cents': str(upper_per_use), 'upper_lifetime_net_cents': str(upper_net),
        'minimum_net_cents': threshold,
        'structurally_reachable': upper_per_use > 0 and upper_net >= threshold,
        'admission_granted': False,
        'scope': 'Necessary condition only, conditional on a valid per-use upper bound and forecast.',
        'proof': 'The one-sided t lower bound cannot exceed the sample mean; bounded deltas bound that mean.',
        'historical_costs_refunded': False,
        'policy_change': 'A prospective prescreen changes later paths and requires fresh confirmation.'
    }

def controls() -> dict:
    cases = [
        ('positive-control', '100', '10', 100, 100, '0', 1, True),
        ('zero-horizon', '100', '0', 0, 0, '0', 1, False),
        ('nonpositive-advantage', '0', '10', 0, 0, '0', 1, False),
        ('complete-cost-barrier', '100', '10', 1000, 1, '0', 1, False),
        ('exact-threshold', '100', '10', 500, 499, '0', 1, True),
        ('one-cent-below-threshold', '100', '10', 500, 500, '0', 1, False),
        ('risk-removes-advantage', '100', '10', 0, 0, '100', 1, False),
        ('fractional-horizon', '100', '1/2', 0, 49, '0', 1, True),
        ('fractional-floor-boundary', '100', '1/2', 0, 50, '0', 1, False),
        ('custom-hurdle', '100', '10', 0, 0, '0', 1001, False),
        ('negative-benefit', '-1', '10', 0, 0, '0', 1, False),
        ('costs-not-double-counted', '100', '10', 200, 200, '0', 600, True)
    ]
    rows=[]
    for name, cap, horizon, life, assessment, risk, minimum, expected in cases:
        result=assess_bound(cap, horizon, life, assessment, risk, minimum)
        rows.append({'name': name, 'passed': result['structurally_reachable'] == expected, 'result': result})
    return {'schema': 'admission-reachability-controls/v1', 'passed': sum(x['passed'] for x in rows),
            'total': len(rows), 'controls': rows, 'new_confirmatory_policy_result': False}

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    result=controls()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as f: f.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'total': result['total']}))
    raise SystemExit(0 if result['passed'] == result['total'] else 1)
