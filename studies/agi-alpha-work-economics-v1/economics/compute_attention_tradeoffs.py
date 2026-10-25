"""Modeled attention limits, with assumptions kept distinct from observed costs."""
import json
from decimal import Decimal
from pathlib import Path

p = Path(__file__).resolve().parent
x = json.loads((p / 'human_market_benchmarks.json').read_text())
d = lambda v: Decimal(str(v))
rounded = lambda v: float(v.quantize(Decimal('0.0001')))
rows = []
for b in x['rates']:
    w = d(b['rate_per_hour'])
    for minutes in x['human_minutes_sensitivity']:
        for non_attention_cost in [1, 5, 10, 25]:
            limit = d(minutes) - d(60) * d(non_attention_cost) / w
            rows.append({
                'benchmark_id': b['id'],
                'currency': b['currency'],
                'human_workflow_minutes_assumption': minutes,
                'human_and_reviewer_hourly_rate': float(w),
                'extra_employer_load_assumption': 1.0,
                'non_attention_system_cost_assumption': non_attention_cost,
                'maximum_review_minutes_at_equal_cost': rounded(limit),
                'economic_advantage_possible_with_nonnegative_attention': limit > 0,
                'status': 'MODELED_LIMIT_NOT_OBSERVED_ATTENTION'
            })
output = {
    'status': 'SCENARIO_ATTENTION_LIMITS',
    'formula': 'maximum review minutes = assumed human minutes - 60 * assumed non-attention system cost / hourly rate',
    'interpretation': 'Non-attention cost includes allocated construction, models, compute, verification, retry and maintenance; remaining employer attention is excluded only to model it explicitly. Same worker/reviewer rate assumed. Wage-only rows have no added employer burden here. Negative limits mean non-attention cost already exceeds the assumed traditional job cost.',
    'currency_policy': x['currency_policy'],
    'actual_review_minutes': None,
    'actual_fully_allocated_system_cost': None,
    'rows': rows
}
(p / 'attention_tradeoffs.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps({'rows': len(rows), 'status': output['status']}))
