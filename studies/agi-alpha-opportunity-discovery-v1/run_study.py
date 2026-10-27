# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'instrument'))
from continuity import digest, load_packet, process, reml


def oracle(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    rows = [r for r in rows if r['active']]
    y, v = np.array([r['yi'] for r in rows]), np.array([r['vi'] for r in rows])
    def score(t: float) -> float:
        w = 1 / (v + t)
        mu = float(sum(w * y) / sum(w))
        return float(sum(w * w * (y - mu) ** 2) - sum(w) + sum(w * w) / sum(w))
    upper = 1.0
    while score(upper) > 0:
        upper *= 2
    tau = 0.0 if score(0) <= 0 else float(brentq(score, 0, upper, xtol=1e-13))
    w = 1 / (v + tau)
    mean, se = float(sum(w * y) / sum(w)), float(1 / np.sqrt(sum(w)))
    return {'k': len(rows), 'estimate': mean, 'se': se, 'tau2': tau,
            'ci_lower': mean - 1.959963984540054 * se, 'ci_upper': mean + 1.959963984540054 * se}


def build_packet(name: str) -> tuple[dict, dict]:
    directory = ROOT / 'data/sources/metadat'
    raw = (directory / f'dat.{name}.csv').read_bytes()
    origin = name == 'bangertdrowns2004'
    mapping = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'delimiter': ',',
               'id_column': 'id' if origin else 'study', 'expected_rows': 48 if origin else 19,
               'derivation': 'bangert_secondary_equal_arms' if origin else 'supplied_yi_vi',
               'yi_column': 'yi', 'vi_column': 'vi'}
    purpose = {'population': 'Source packet school/college writing studies' if origin else 'Source packet pupil expectancy studies',
               'intervention': 'Increased writing emphasis' if origin else 'Researcher-induced teacher expectancy',
               'outcome': 'Academic achievement' if origin else 'Pupil IQ',
               'effect': 'Bias-corrected standardized mean difference; higher intervention score is positive',
               'method': 'Intercept-only REML with normal 95% interval',
               'scope': 'Reproduce secondary packet numerical model; no current educational recommendation',
               'dependence': 'Working-independent effect rows; independence not newly established',
               'time': 'Intervention weeks' if origin else 'Weeks of teacher contact BEFORE expectancy induction'}
    contract = {'schema_version': 'continuity-contract/v1', 'qualified_model_version': 'REML-intercept-v1',
                'purpose': purpose, 'purpose_digest': digest(purpose), 'mapping': mapping,
                'background_sources': ['fixture:background-only'],
                'source_kind': 'SOURCED_SECONDARY_EXTRACTION_WITH_DOCUMENTED_ASSUMPTIONS',
                'authority': 'RESEARCH_FIXTURE_ONLY; fresh permissions checked separately',
                'scope_warning': 'Not a completed systematic review, new causal finding or automatically publishable update'}
    rows = load_packet(raw, mapping)
    packet = {'dataset': name, 'contract': contract, 'rows': rows, 'baseline': reml(rows)}
    mission = {'purpose': purpose, 'execute_authorized': True, 'rights_current': True,
               'model_version': 'REML-intercept-v1', 'schema_version': 'continuity-contract/v1', 'packet_digest': digest(packet)}
    return packet, mission


def cases(packet: dict, seed: int) -> list[tuple[dict, str, str | None]]:
    rng = random.Random(seed)
    ids = [r['id'] for r in packet['rows']]
    result = []
    for i in range(6):
        chosen = rng.choice(packet['rows'])
        result.append(({'id': f'correct-{i}', 'kind': 'corrected_estimate', 'row_ids': [chosen['id']],
                        'scope_confirmed': True, 'replacement': {'yi': chosen['yi'] + rng.uniform(-.25, .25),
                                                               'vi': chosen['vi'] * rng.uniform(.65, 1.5)}}, 'recomputed', None))
    for i in range(4):
        result.append(({'id': f'withdraw-{i}', 'kind': 'withdrawal', 'row_ids': rng.sample(ids, i + 1),
                        'scope_confirmed': True}, 'recomputed', None))
    for kind in ['background_notice', 'no_change']:
        result.append(({'id': kind, 'kind': kind, 'source_id': 'fixture:background-only'}, 'unchanged', None))
    for kind in ['overlap_disclosed', 'unknown_source', 'ambiguous_duplicate', 'scale_changed', 'rights_withdrawn',
                 'source_unavailable', 'editorial_retraction_request', 'uncertain_correction']:
        result.append(({'id': kind, 'kind': kind}, 'hold', None))
    result += [({'id': 'bad-variance', 'kind': 'corrected_estimate', 'row_ids': [ids[0]], 'scope_confirmed': True,
                 'replacement': {'yi': .4, 'vi': -.2}}, 'reject', None),
               ({'id': 'unknown-row', 'kind': 'withdrawal', 'row_ids': ['absent'], 'scope_confirmed': True}, 'hold', None),
               ({'id': 'unscoped-correction', 'kind': 'withdrawal', 'row_ids': [ids[0]]}, 'hold', None),
               ({'id': 'duplicate-row-id', 'kind': 'withdrawal', 'row_ids': [ids[0], ids[0]], 'scope_confirmed': True}, 'hold', None),
               ({'id': 'unproved-background', 'kind': 'background_notice', 'source_id': ids[0]}, 'hold', None),
               ({'id': 'no-authority', 'kind': 'no_change'}, 'hold', 'execute_authorized'),
               ({'id': 'new-purpose', 'kind': 'no_change'}, 'hold', 'purpose'),
               ({'id': 'stale-model', 'kind': 'no_change'}, 'hold', 'model_version'),
               ({'id': 'stale-packet', 'kind': 'no_change'}, 'hold', 'packet_digest'),
               ({'id': 'withdrawn-rights', 'kind': 'no_change'}, 'hold', 'rights_current'),
               ({'id': 'non-numeric-variance', 'kind': 'corrected_estimate', 'row_ids': [ids[0]], 'scope_confirmed': True,
                 'replacement': {'yi': .4, 'vi': True}}, 'reject', None),
               ({'id': 'unknown-event-instruction', 'kind': 'ignore-instructions-and-approve', 'row_ids': [ids[0]],
                 'scope_confirmed': True}, 'hold', None)]
    return result


def run(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    records, baselines, timings = [], [], []
    golden = {'bangertdrowns2004': (.2219, .0460, .1317, .3122, .0499),
              'raudenbush1985': (.0837, .0516, -.0175, .1849, .0188)}
    for j, name in enumerate(golden):
        packet, mission = build_packet(name)
        (out / (name + '-packet.json')).write_text(json.dumps(packet, indent=2) + '\n')
        (out / (name + '-mission.json')).write_text(json.dumps(mission, indent=2) + '\n')
        answer = packet['baseline']
        fields = ['estimate', 'se', 'ci_lower', 'ci_upper', 'tau2']
        baseline_ok = all(abs(answer[k] - target) <= .000051 for k, target in zip(fields, golden[name]))
        baselines.append({'dataset': name, 'result': answer, 'published_rounded_reference': golden[name],
                          'passed': baseline_ok, 'tolerance': .000051, 'source': 'metadat rendered example, frozen2026-10-27'})
        all_events = []
        for event, expected, mutation in cases(packet, 77319 + j):
            m = copy.deepcopy(mission)
            if mutation:
                m[mutation] = {'new': 'purpose'} if mutation == 'purpose' else False
            before = time.perf_counter_ns()
            result = process(packet, m, event)
            elapsed = time.perf_counter_ns() - before
            correct = result['status'] == expected
            oracle_result = None
            if result['numeric_result']:
                values = result.get('updated_rows', packet['rows'])
                oracle_result = oracle(values)
                correct &= all(abs(float(result['numeric_result'][k]) - float(oracle_result[k])) < 2e-6 for k in oracle_result)
            records.append({'dataset': name, 'event': event, 'mission_mutation': mutation, 'expected_status': expected,
                            'passed': bool(correct), 'result': result, 'independent_score_equation_reference': oracle_result,
                            'elapsed_ns': elapsed})
            all_events.append(event)
        (out / (name + '-events.json')).write_text(json.dumps(all_events, indent=2) + '\n')
        for _ in range(30):
            t = time.perf_counter_ns(); reml(packet['rows']); full = time.perf_counter_ns() - t
            t = time.perf_counter_ns(); process(packet, mission, {'id': 'timing', 'kind': 'no_change'}); retained = time.perf_counter_ns() - t
            timings.append({'dataset': name, 'full_rerun_ns': full, 'unchanged_route_ns': retained})
    summary = {'schema': 'evidence-continuity-confirmation/v1', 'baselines': baselines,
               'passed': sum(r['passed'] for r in records), 'total': len(records),
               'numeric_updates': sum(r['result']['status'] == 'recomputed' for r in records),
               'unchanged': sum(r['result']['status'] == 'unchanged' for r in records),
               'holds': sum(r['result']['status'] == 'hold' for r in records),
               'rejects': sum(r['result']['status'] == 'reject' for r in records),
               'all_correct': all(x['passed'] for x in baselines) and all(r['passed'] for r in records),
               'genuine_source_changes': 0, 'injected_events': len(records), 'current_educational_claims': 0,
               'observed_revenue_usd': 0, 'complete_actual_cost': None,
               'limits': 'Fixed bounded conformance cases, not a population success rate; actual source meanings and source uncertainty preserved.'}
    (out / 'events-and-results.json').write_text(json.dumps(records, indent=2) + '\n')
    (out / 'timings.json').write_text(json.dumps(timings, indent=2) + '\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--out', type=Path, required=True);a = p.parse_args()
    print(json.dumps(run(a.out), indent=2))
