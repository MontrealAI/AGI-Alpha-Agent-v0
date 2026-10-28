# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'results/strategic_game.json'
published = json.loads(source.read_text())
randomness = random.Random(published['seed'])
types = []
for _ in range(4000):
    value = 6500 * randomness.lognormvariate(0, .4)
    urgency = randomness.uniform(3, 18)
    work = randomness.uniform(6, 16) + randomness.uniform(4, 8)
    internal = .94 * value - work * 135 - 405 - 14 * urgency
    free = .91 * value - (work + 4) * 135 - 405 - 21 * urgency
    types.append((.94 * value - 405 - 250 - 10 * urgency,
                  .96 * value - 405 - 50 - 7 * urgency, max(0, internal, free)))
records, errors = [], []


def response(values: list[float], temperature: float) -> list[float]:
    largest = max(values)
    exp = [math.exp((value - largest) / temperature) for value in values]
    denominator = math.fsum(exp)
    return [value / denominator for value in exp]


for name, game in published['games'].items():
    actions = game['price_actions']
    count = len(actions)
    cost = game['unit_cost_assumption_both']
    ours = [[0.0] * count for _ in actions]
    rival = [[0.0] * count for _ in actions]
    comparisons = 0
    for i, left in enumerate(actions):
        for j, right in enumerate(actions):
            sold_left = sold_right = 0
            for u, v, outside in types:
                u = u - left if isinstance(left, int) else -math.inf
                v = v - right if isinstance(right, int) else -math.inf
                sold_left += int(u > v and u >= outside)
                sold_right += int(v >= u and v >= outside)
            ours[i][j] = (20 * sold_left / len(types) * (left - cost) - game['startup_ours']
                          if isinstance(left, int) else 0)
            rival[i][j] = (20 * sold_right / len(types) * (right - cost)
                           if isinstance(right, int) else 0)
            for label, calculated, field in [('ours', ours[i][j], 'payoffs_ours'),
                                              ('rival', rival[i][j], 'payoffs_rival')]:
                comparisons += 1
                if abs(calculated - game[field][i][j]) > 1e-7:
                    errors.append(f'{name}:{label}:{i},{j}: payoff mismatch')
    entry, active = [], []
    for i, left in enumerate(actions):
        for j, right in enumerate(actions):
            if (ours[i][j] >= max(row[j] for row in ours) - 1e-8
                    and rival[i][j] >= max(rival[i]) - 1e-8):
                entry.append(('do_not_enter' if left == 'exit' else left, right))
            if i < count - 1 and j < count - 1:
                if (ours[i][j] >= max(row[j] for row in ours[:-1]) - 1e-8
                        and rival[i][j] >= max(rival[i][:-1]) - 1e-8):
                    active.append((left, right))
    stated_entry = [(item['ours_action'], item['rival_action']) for item in game['entry_pure_nash']]
    stated_active = [(item['ours_price'], item['rival_price']) for item in game['conditional_active_pure_nash']]
    if entry != stated_entry or active != stated_active:
        errors.append(f'{name}: equilibrium set mismatch')
    left = [0.0] * count
    left[-1] = 1.0
    right = [1 / count] * count
    for _ in range(1000):
        utility_left = [math.fsum(ours[i][j] * right[j] for j in range(count)) for i in range(count)]
        utility_right = [math.fsum(left[i] * rival[i][j] for i in range(count)) for j in range(count)]
        target_left = response(utility_left, game['bounded_rational_logit_temperature_usd'])
        target_right = response(utility_right, game['bounded_rational_logit_temperature_usd'])
        left = [.75 * a + .25 * b for a, b in zip(left, target_left)]
        right = [.75 * a + .25 * b for a, b in zip(right, target_right)]
    residual = max(abs(a - b) for a, b in zip(left + right, target_left + target_right))
    if residual > 1e-10:
        errors.append(f'{name}: logit fixed-point residual {residual}')
    if abs(left[-1] - game['logit_ours_exit_probability']) > 1e-10:
        errors.append(f'{name}: logit exit probability mismatch')
    records.append(dict(arrangement=name, payoff_cells_checked=comparisons,
                        active_equilibria=active, entry_equilibria=entry,
                        logit_ours_exit_probability=left[-1], logit_residual=residual))
report = dict(schema='possibility-engine.independent-strategic-audit.v1',
              input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              method='Separate standard-library reconstruction of synthetic types, payoff matrices and best responses; '
                     'logit recomputation from a different initial condition and relaxation rate.',
              records=records, errors=errors, passed=not errors,
              limits='Only the declared finite game is checked. Buyer demand, price grids, costs, beliefs and '
                     'incumbent sunk-cost advantage are assumptions. No market or unique general equilibrium is claimed.')
(ROOT / 'audit/strategic_confirmation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(passed=not errors, payoff_cells=sum(item['payoff_cells_checked'] for item in records),
                      errors=errors)))
raise SystemExit(0 if not errors else 1)
