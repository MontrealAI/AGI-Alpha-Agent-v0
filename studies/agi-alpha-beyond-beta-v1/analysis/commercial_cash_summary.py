# SPDX-License-Identifier: Apache-2.0
"""Deterministic reporting from frozen histories; no policy or simulation changes."""
from pathlib import Path
import collections
import datetime
import gzip
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'results/paid_work_final'
CONFIG = json.loads((RESULTS / 'frozen_config.json').read_text())
MONTHS = {'operating_horizon': CONFIG['months'], 'terminal_runoff': CONFIG['months'] + CONFIG['runoff_months']}
FIELDS = ['closing_cash', 'reserve', 'unpaid_obligations', 'known_future_refunds',
          'pending_recovery_obligation', 'outstanding_receivables',
          'available_uncommitted_cash', 'retained_operating_cash_above_seed']
VALUES = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
PRICES = collections.defaultdict(list)
WORLD_PRICES = collections.defaultdict(list)
COUNTS = collections.Counter()
FAILURES = []
SOURCE_FILES = []
MAX_CASH_RESIDUAL = 0.0
MAX_REFERENCE_RESIDUAL = 0.0


def stats(values):
    x = np.asarray(values, dtype=float)
    if not len(x):
        return {'n': 0, 'mean': None, 'median': None, 'p05': None, 'p95': None, 'min': None, 'max': None}
    return {'n': len(x), 'mean': float(x.mean()), 'median': float(np.median(x)),
            'p05': float(np.quantile(x, .05)), 'p95': float(np.quantile(x, .95)),
            'min': float(x.min()), 'max': float(x.max())}


for file in sorted(RESULTS.glob('*_complete_records.jsonl.gz')):
    SOURCE_FILES.append({'file': file.name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
    with gzip.open(file, 'rt') as stream:
        for line in stream:
            result = json.loads(line)
            key = (result['scenario'], result['policy'])
            COUNTS[key] += 1
            rows = {row['month']: row for row in result['ledger']}
            for endpoint, month in MONTHS.items():
                row = rows[month]
                for field in FIELDS:
                    VALUES[key][endpoint][field].append(row[field])
                known = row['unpaid_obligations'] + row['known_future_refunds'] + row['pending_recovery_obligation']
                reserve_only = max(0., row['reserve'] - row['known_future_refunds'] - row['pending_recovery_obligation'])
                expected_available = max(0., row['closing_cash'] - known - reserve_only)
                expected_earned = max(0., row['closing_cash'] - CONFIG['seed_cash'] - known - reserve_only)
                residual = max(abs(expected_available - row['available_uncommitted_cash']),
                               abs(expected_earned - row['retained_operating_cash_above_seed']))
                MAX_CASH_RESIDUAL = max(MAX_CASH_RESIDUAL, residual)
                if residual > 1e-6:
                    FAILURES.append({'kind': 'cash_endpoint_identity', 'scenario': key[0], 'policy': key[1], 'world': result['world'], 'month': month, 'residual': residual})
                VALUES[key][endpoint]['all_known_obligations_excluding_warranty_provision'].append(known)
                VALUES[key][endpoint]['reserve_excluding_known_obligations'].append(reserve_only)
            world_prices = []
            for job in result['job_records'].values():
                if not (job.get('true_useful_for_analysis_only') and job.get('actually_collected_by_horizon') and job.get('status') == 'validated_pass'):
                    continue
                # The frozen kernel forms project ID world:original_offer_month:index,
                # fixes price at that offer and preserves it through any delivery queue.
                # Price / that month's fraction therefore recovers its exact modeled
                # human reference; verify against the two permitted scope references.
                pieces = job['job_id'].split(':')
                if len(pieces) != 3 or int(pieces[0]) != result['world']:
                    raise ValueError('Unexpected frozen project identifier')
                original_offer_month = int(pieces[1])
                fraction = rows[original_offer_month]['price_fraction']
                gross_price = job['offered_price']
                inferred_reference = gross_price / fraction
                base = CONFIG['scenarios'][key[0]]['human_reference']
                alternatives = [base, base * CONFIG['scope']['rich_human_reference_multiplier']]
                reference = min(alternatives, key=lambda value: abs(value - inferred_reference))
                reference_residual = abs(reference - inferred_reference)
                MAX_REFERENCE_RESIDUAL = max(MAX_REFERENCE_RESIDUAL, reference_residual)
                if reference_residual > 1e-6:
                    FAILURES.append({'kind': 'matched_scope_reference', 'scenario': key[0], 'policy': key[1], 'world': result['world'], 'job_id': job['job_id'], 'residual': reference_residual})
                item = {'modeled_human_service_reference': reference, 'gross_offered_price': gross_price,
                        'reference_price_difference': reference - gross_price,
                        'reference_price_difference_fraction': 1 - gross_price / reference}
                PRICES[key].append(item)
                world_prices.append(item)
            WORLD_PRICES[key].append({'true_useful_collected_projects': len(world_prices),
                                     'total_reference_price_difference': sum(x['reference_price_difference'] for x in world_prices),
                                     'total_modeled_human_service_reference': sum(x['modeled_human_service_reference'] for x in world_prices),
                                     'total_gross_offered_price': sum(x['gross_offered_price'] for x in world_prices)})

OUTPUT = {
    'schema': 'paid-work-commercial-cash-summary/v1',
    'basis': 'POSTHOC_DETERMINISTIC_REPORTING_FROM_FROZEN_SIMULATED_HISTORIES',
    'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_files': SOURCE_FILES,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'frozen_config_sha256': hashlib.sha256((RESULTS / 'frozen_config.json').read_bytes()).hexdigest(),
    'seed_cash_usd': CONFIG['seed_cash'],
    'definitions': {
        'endpoints': 'Month 24 is the end of operations; month 27 is the end of collection/refund runoff. Stocks are not summed across months.',
        'closing_cash': 'Actual simulated cleared cash stock, including remaining seed. Outstanding receivables are not cash.',
        'reserve': 'Protected cash balance under the frozen policy, including known future refunds, pending recovery, fixed operating reserve and warranty provision. It is not an additional expense.',
        'unpaid_obligations': 'The monthly ledger field contains unpaid fixed/refund obligations; pending recovery and scheduled known future refunds are shown separately.',
        'available_uncommitted_cash': 'max(0, closing_cash - reserve - unpaid_obligations). May include remaining seed. Known refund/recovery amounts already included in reserve are not deducted twice.',
        'retained_operating_cash_above_seed': 'max(0, closing_cash - original seed_cash - reserve - unpaid_obligations). A conservative cash stock after preserving the entire original seed, not net profit.',
        'net_profit': 'Reported separately by the frozen simulation: terminal cash - original seed - all unpaid terminal obligations. Neither cash availability field is substituted for profit.',
        'quantiles': 'World-level mean, median and linear 5th/95th quantiles; each primary condition has 500 independent world IDs. Common random numbers reuse those IDs across scenario conditions and policy arms: 1,500 condition-world evaluations are not 1,500 independent underlying draws.',
        'true_useful_collected_price_reference': 'Jobs labeled truly useful by the simulation and actually collected by the horizon, with validated-pass status. False passes and unpaid jobs are excluded.',
        'reference_price_difference': 'Matched frozen human-service scope reference minus gross offered price. This is an arithmetic reference-price difference, not observed buyer savings, willingness to pay, consumer surplus or a counterfactual purchase claim.',
        'reference_reconstruction': 'Job records do not repeat the rich flag. Recover the exact reference as offered_price divided by the original offer month price_fraction from project ID; verify against the frozen base or richer-scope reference. No new outcomes or scope assumptions are introduced.',
    },
    'audit': {'status': 'PASS' if not FAILURES else 'FAIL', 'histories': sum(COUNTS.values()),
              'endpoint_rows': sum(COUNTS.values()) * len(MONTHS), 'max_cash_identity_residual_usd': MAX_CASH_RESIDUAL,
              'max_reference_reconstruction_residual_usd': MAX_REFERENCE_RESIDUAL, 'failures': FAILURES},
    'scenarios': {},
}
for key, count in sorted(COUNTS.items()):
    scenario, policy = key
    item = {'worlds': count, 'endpoints': {}}
    for endpoint, month in MONTHS.items():
        item['endpoints'][endpoint] = {'month': month, 'metrics': {field: stats(values) for field, values in VALUES[key][endpoint].items()}}
    projects = PRICES[key]
    item['true_useful_collected_price_reference'] = {
        'projects': len(projects),
        'per_project': {field: stats([project[field] for project in projects]) for field in ['modeled_human_service_reference', 'gross_offered_price', 'reference_price_difference', 'reference_price_difference_fraction']},
        'pooled_totals': {field: sum(project[field] for project in projects) for field in ['modeled_human_service_reference', 'gross_offered_price', 'reference_price_difference']},
        'per_world': {field: stats([world[field] for world in WORLD_PRICES[key]]) for field in ['true_useful_collected_projects', 'total_reference_price_difference', 'total_modeled_human_service_reference', 'total_gross_offered_price']},
    }
    OUTPUT['scenarios'].setdefault(scenario, {'policies': {}})['policies'][policy] = item
out = RESULTS / 'commercial_cash_summary.json'
out.write_text(json.dumps(OUTPUT, indent=2) + '\n')
print(json.dumps({'output': str(out), **OUTPUT['audit']}))
if FAILURES:
    raise SystemExit(1)
