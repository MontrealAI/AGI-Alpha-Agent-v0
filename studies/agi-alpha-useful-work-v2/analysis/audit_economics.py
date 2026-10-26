# SPDX-License-Identifier: Apache-2.0
"""Independent arithmetic and scope audit of the completed economic mapping."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time


ARMS = ('manual', 'retained', 'conventional')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    return {'n': len(values), 'sum': sum(values), 'mean': statistics.mean(values),
            'median': statistics.median(values), 'min': min(values), 'max': max(values)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--analysis', type=Path, required=True)
    args = parser.parse_args()
    root, analysis = args.root.resolve(), args.analysis.resolve()
    started, cpu = time.perf_counter(), time.process_time()
    summary = read(analysis / 'summary.json')
    economics = read(analysis / 'canonical-economics/economics.json')
    campaign = read(root / 'results/confirmation/campaign.json')
    errors, rows = [], []
    for result in campaign['results']:
        terminal_path = root / result['terminal']
        terminal = read(terminal_path)
        mapped = next(row for row in summary['runs'] if row['mission_id'] == result['mission_id'] and row['arm'] == result['arm'])
        for key, expected in [('request_to_package_wall_seconds', terminal['service_span_seconds']),
                              ('measured_local_child_cpu_seconds', terminal['inclusive_child_cpu_seconds']),
                              ('measured_local_controller_cpu_seconds', terminal['driver_process_cpu_seconds'])]:
            if mapped[key] != expected:
                errors.append(f'{result["mission_id"]}/{result["arm"]}:{key}')
        if mapped['accepted'] != terminal['accepted']:
            errors.append(f'{result["mission_id"]}/{result["arm"]}:acceptance')
        if result['arm'] == 'manual':
            pair = read(root / terminal['mechanical_pair'])
            finalization = read(root / terminal['finalization_receipt'])
            mechanical = pair['wall_seconds'] + finalization['wall_seconds']
            sub_cpu = pair['process_cpu_seconds'] + pair['child_cpu_seconds'] + finalization['meter_cpu_seconds'] + finalization['child_cpu_seconds']
        else:
            external = read(root / terminal['external_receipt'])
            mechanical = external['wall_seconds']
            sub_cpu = external['meter_cpu_seconds'] + external['child_cpu_seconds']
        if abs(mapped['mechanical_wall_seconds'] - mechanical) > 1e-9:
            errors.append(f'{result["mission_id"]}/{result["arm"]}:mechanical_wall')
        enclosing_cpu = terminal['driver_process_cpu_seconds'] + terminal['inclusive_child_cpu_seconds']
        # Linux nested child accounting should fit its enclosing process usage;
        # preserve a tiny accounting-resolution tolerance, not a savings margin.
        if enclosing_cpu + 0.01 < sub_cpu:
            errors.append(f'{result["mission_id"]}/{result["arm"]}:nested_cpu_exceeds_envelope')
        directory = terminal_path.parent
        files = list(directory.rglob('*'))
        if result['arm'] != 'manual':
            external_path = root / terminal['external_receipt']
            files += [external_path, external_path.with_suffix('.stdout.txt'), external_path.with_suffix('.stderr.txt')]
        unique = {path.resolve() for path in files if path.is_file()}
        logical_bytes = sum(path.stat().st_size for path in unique)
        rows.append({'mission_id': result['mission_id'], 'arm': result['arm'], 'accepted': mapped['accepted'],
            'decision': mapped['decision'], 'service_span_seconds': terminal['service_span_seconds'],
            'mechanical_wall_seconds': mechanical, 'enclosing_local_cpu_seconds': enclosing_cpu,
            'nested_mechanical_cpu_seconds_diagnostic': sub_cpu,
            'explicit_manual_finalizations': terminal.get('manual_finalizations'),
            'logical_output_bytes': logical_bytes, 'output_files': len(unique), 'terminal_sha256': sha(terminal_path)})
    by_arm = {}
    for arm in ARMS:
        selected = [row for row in rows if row['arm'] == arm]
        by_arm[arm] = {'accepted': sum(row['accepted'] for row in selected), 'evaluations': len(selected),
            **{key: stats([row[key] for row in selected]) for key in ['service_span_seconds', 'mechanical_wall_seconds', 'enclosing_local_cpu_seconds']},
            'logical_output_bytes': sum(row['logical_output_bytes'] for row in selected),
            'output_files': sum(row['output_files'] for row in selected),
            'explicit_manual_finalizations': sum(row['explicit_manual_finalizations'] for row in selected)}
    paired = []
    for mission in [row['mission'] for row in read(root / 'protocol/primary-protocol.json')['mission_order']]:
        left = next(row for row in rows if row['mission_id'] == mission and row['arm'] == 'retained')
        right = next(row for row in rows if row['mission_id'] == mission and row['arm'] == 'conventional')
        paired.append({'mission_id': mission, 'both_accepted': left['accepted'] and right['accepted'],
            **{key: left[key] - right[key] for key in ['service_span_seconds', 'mechanical_wall_seconds', 'enclosing_local_cpu_seconds']},
            'logical_output_bytes': left['logical_output_bytes'] - right['logical_output_bytes']})
    paired_summary = {key: stats([row[key] for row in paired]) for key in
                      ['service_span_seconds', 'mechanical_wall_seconds', 'enclosing_local_cpu_seconds', 'logical_output_bytes']}
    additive = [row for row in economics['resource_records'] if row['accounting_role'] == 'additive']
    if len({row['evidence']['path'] for row in additive}) != len(additive):
        errors.append('Duplicate additive resource source')
    delivery = [row for row in additive if row['ownership'] == 'delivery']
    if len(delivery) != 18:
        errors.append('Expected exactly one inclusive additive resource envelope per arm run')
    if sum(row['resources']['wall_seconds'] for row in delivery) != sum(row['service_span_seconds'] for row in rows):
        errors.append('Additive delivery wall differs from terminal sums')
    for key in ['starting_capital_minor', 'approved_allocation_minor', 'customer_price_minor',
                'complete_delivery_cost_minor', 'complete_investment_minor', 'available_surplus_minor', 'available_to_commit_minor']:
        if economics['finance'][key] is not None:
            errors.append('Unsupported numeric financial value:' + key)
    if economics['finance']['actual_collections_minor'] != 0 or economics['actual_paid_customer_missions'] != 0:
        errors.append('Unsupported paid receipts or customers')
    for scenario in economics['canonical_cost_projection']['scenarios']:
        for key in ['marginalMicrosPerAccepted', 'recurringMicrosPerAccepted', 'fullyLoadedMicrosPerAccepted']:
            if scenario['costs'][key] is not None:
                errors.append('Unidentified complete cost converted to numeric:' + key)
    if economics['canonical_ledger_summary']['observed']['revenue'] != 0:
        errors.append('Canonical observed collection mismatch')
    for key in ['fullCost', 'operatingMargin', 'availableSurplus', 'eligibleInvestment']:
        if economics['canonical_ledger_summary']['observed'][key] is not None:
            errors.append('Unknown canonical monetary quantity became numeric:' + key)
    capability_costs = [event for event in economics['canonical_ledger']['events']
                        if event['missionId'] == 'study-investment' and event['type'] == 'cost' and event['category'] == 'capability']
    if len(capability_costs) != 10 or any(event['amountMinor'] is not None for event in capability_costs):
        errors.append('Same-asset builder/failed-construction accounting changed')
    result = {'schema': 'independent-economic-aggregation-audit/v1', 'status': 'PASS' if not errors else 'FAIL',
        'errors': errors, 'summary_sha256': sha(analysis / 'summary.json'),
        'economics_sha256': sha(analysis / 'canonical-economics/economics.json'),
        'unique_missions': 6, 'arm_evaluations': len(rows), 'rows': rows, 'by_arm': by_arm,
        'paired_retained_minus_conventional': {'rows': paired, 'summary': paired_summary,
            'sign': 'Negative means the retained arm used less measured resource; no inferential significance or monetary saving is implied.'},
        'delivery_additive_records': len(delivery), 'all_additive_records': len(additive),
        'logical_storage_scope': 'Logical file bytes in each completed run directory plus its external receipt/stdout/stderr; excludes shared environments, publication and archive copies. Not allocated disk blocks, compressed size or a storage bill.',
        'construction_scope': 'Known lifecycle subtotals retain both builders, shared work and failures; complete construction inference and monetary costs remain unknown.',
        'audit_wall_seconds': time.perf_counter() - started, 'audit_process_cpu_seconds': time.process_time() - cpu,
        'money_usd': None}
    path = analysis / 'independent-aggregation-audit.json'
    if path.exists():
        raise ValueError('Preserve previous audit edition')
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'errors': errors, 'by_arm': by_arm,
                      'paired_retained_minus_conventional': paired_summary}, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == '__main__':
    main()
