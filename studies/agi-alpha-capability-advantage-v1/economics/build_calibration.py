from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

FAMILIES = [('G1', 'forward'), ('G2', 'inverse'), ('G3', 'design')]
ARMS = ['A', 'B', 'C', 'D']


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def within(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    return path


def fact(seconds: float, basis: str, reference: str) -> dict[str, Any]:
    return {'seconds': seconds, 'basis': basis, 'reference': reference}


def index_records(records: list[dict[str, Any]]) -> tuple[list[str], dict[tuple[str, str, str], dict[str, Any]]]:
    if len(records) != 144:
        raise ValueError('CALIBRATION_REQUIRES_ALL_144_REGISTERED_ARM_STAGE_RECORDS')
    chains = sorted({r['chain'] for r in records})
    if len(chains) != 12:
        raise ValueError('CALIBRATION_REQUIRES_12_CONNECTED_CHAINS')
    indexed = {}
    for row in records:
        key = row['chain'], row['family'], row['arm']
        if key in indexed:
            raise ValueError('DUPLICATE_ARM_STAGE_RECORD')
        if row.get('cohort') != 'primary' or row['arm'] not in ARMS or row['family'] not in dict(FAMILIES).values():
            raise ValueError('UNEXPECTED_COHORT_OR_METHOD')
        if not isinstance(row['accepted'], bool):
            raise ValueError('ACTUAL_ACCEPTANCE_REQUIRED')
        if not row.get('not_executed') and row.get('child_cpu_complete') is not True:
            raise ValueError('COMPLETE_CPU_UNKNOWN_NO_FREE_FAILURE_OR_FINANCIAL_PROMOTION')
        if row.get('not_executed') and (row['accepted'] or row['cpu_seconds'] != 0):
            raise ValueError('BLOCKED_STAGE_MUST_REMAIN_UNEXECUTED')
        indexed[key] = row
    expected = {(c, f, a) for c in chains for _, f in FAMILIES for a in ARMS}
    if set(indexed) != expected:
        raise ValueError('MISSING_OR_EXTRA_REGISTERED_ARM_STAGE')
    for chain in chains:
        sizes = {indexed[chain, family, arm]['node_count'] for _, family in FAMILIES for arm in ARMS}
        if len(sizes) != 1 or next(iter(sizes)) not in [100, 625, 1600, 2500]:
            raise ValueError('CONNECTED_CHAIN_SIZE_STRATUM_DRIFT')
    return chains, indexed


def build(root: Path, primary: Path) -> dict[str, Any]:
    root, primary = root.resolve(), primary.resolve()
    primary.relative_to(root)
    summary_path = primary / 'summary.json'
    if not summary_path.exists():
        raise ValueError('WAIT_FOR_COMPLETE_REGISTERED_PRIMARY_SUMMARY')
    summary = read(summary_path)
    if summary['cohort'] != 'primary' or summary['chains'] != 12 or summary['planned_stages'] != 36:
        raise ValueError('PRIMARY_SUMMARY_SCOPE_MISMATCH')
    records_path = primary / 'records.jsonl'
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line]
    chains, indexed = index_records(records)
    freeze_path = root / 'protocol/production-freeze.json'
    freeze = read(freeze_path)
    if freeze['status'] != 'FROZEN_BEFORE_PRIMARY_GENERATION_AND_OUTCOMES':
        raise ValueError('PROSPECTIVE_PRODUCTION_FREEZE_REQUIRED')
    frozen = {row['path']: row for row in freeze['files']}
    for row in freeze['files']:
        path = within(root, row['path'])
        if sha(path) != row['sha256'] or path.stat().st_size != row['bytes']:
            raise ValueError(f"PRODUCTION_FROZEN_SOURCE_DRIFT:{row['path']}")
    assumptions_path = root / 'protocol/resource-assumptions.json'
    assumptions = read(assumptions_path)
    if assumptions['status'] != 'DECLARED_BEFORE_PRIMARY_AND_MARKET_OUTCOMES':
        raise ValueError('PROSPECTIVE_RESOURCE_ASSUMPTIONS_REQUIRED')
    if 'protocol/resource-assumptions.json' not in frozen:
        raise ValueError('RESOURCE_ASSUMPTIONS_NOT_BOUND_TO_PRODUCTION_FREEZE')
    catalog_path = root / 'identity/catalog.json'
    catalog = read(catalog_path)
    admission_path = within(root, catalog['executionReceipt']['path'])
    if sha(admission_path) != catalog['executionReceipt']['sha256']:
        raise ValueError('ADMISSION_RECEIPT_IDENTITY_MISMATCH')
    admission = read(admission_path)
    if admission['accepted'] is not True:
        raise ValueError('ACTUAL_PROTOTYPE_ADMISSION_NOT_ESTABLISHED')
    initial_path = root / 'evidence/discovery-initial/records.jsonl'
    initial = [json.loads(line) for line in initial_path.read_text().splitlines() if line]
    failed_shared_elapsed = sum(r['elapsed_seconds'] for r in initial if r['arm'] == 'B' and not r.get('not_executed'))
    source_shared = {'G1': ('forward', '1'), 'G2': ('inverse', '1'), 'G3': ('design', '2')}
    result: dict[str, Any] = {
        'schema': 'capability-advantage-calibration/v2',
        'basis': 'EXECUTED_RESEARCH_COHORT_ONLY',
        'actual_customer_collections_cents': 0,
        'actual_total_cost_cents': None,
        'timing_scope': 'complete_stage_no_additional_retrieval',
        'resources_are_exclusive_or_explicitly_included': True,
        'sampling_scope': 'Each conditional market purchase selects one stage of a sampled connected-chain profile; exact chain correspondence and paired methods are retained. This does not create three customers from one actual research chain.',
        'difficulty_rule': '100/625 nodes standard; 1600/2500 nodes hard. Fixed before market outcomes; not selected from success.',
        'raw_prior_capability': 'NOT_RUN. Independent reconstruction and conventional production remain available; missing skill files establish no incapability.',
        'root_authoring_cost': 'UNKNOWN. Explicitly priced resource proxies and complete-category schedules are assumptions, not invoices or empirical bounds.',
        'graph_control_authoring_cost': 'UNKNOWN separately. Equal B/C construction and generic authoring allocations are a scenario assumption, never measured zero incremental graph-control authoring.',
        'families': [],
        'retrieval': {
            'registry_build': fact(0.456, 'measured_elapsed_allocation',
                'Root-reported original catalogue construction tool wall duration, 0.456s; attributed once. Not independently remetered.'),
            'graph_build': fact(0.456, 'measured_elapsed_allocation',
                'Same original catalogue construction, charged once; distinct control-authoring actual cost remains UNKNOWN and scenario authoring allocation explicit.')},
        'resource_allocation': [],
        'provenance': {
            'production_freeze': {'path': str(freeze_path.relative_to(root)), 'sha256': sha(freeze_path)},
            'primary_records': {'path': str(records_path.relative_to(root)), 'sha256': sha(records_path), 'records': len(records)},
            'primary_summary': {'path': str(summary_path.relative_to(root)), 'sha256': sha(summary_path)},
            'resource_assumptions': {'path': str(assumptions_path.relative_to(root)), 'sha256': sha(assumptions_path)},
            'catalog': {'path': str(catalog_path.relative_to(root)), 'sha256': sha(catalog_path)},
            'admission_receipt': {'path': str(admission_path.relative_to(root)), 'sha256': sha(admission_path)},
            'failed_shared_campaign': {'path': str(initial_path.relative_to(root)), 'sha256': sha(initial_path),
                'elapsed_seconds_once': failed_shared_elapsed,
                'scope': 'All actual invocations in the unsuccessful original shared campaign; blocked stages were not executed.'},
            'admission_resources_not_charged_twice': {'elapsed_seconds': admission['elapsed_seconds'],
                'parent_cpu_seconds': admission['cpu_seconds'], 'dispatch_child_cpu_seconds': admission['dispatch_child_cpu_seconds'],
                'pricing_rule': 'Price elapsed validation once as research resource; retain CPU as observation without adding another bill.'}}
    }
    for generation, family_name in FAMILIES:
        skill_name, version = source_shared[generation]
        skill = next(s for s in catalog['skills'] if s['id'] == skill_name and s['version'] == version)
        for row in skill['implementation']['files']:
            if sha(within(root, row['path'])) != row['sha256']:
                raise ValueError('ADMITTED_IMPLEMENTATION_SOURCE_DRIFT')
        shared_identity = hashlib.sha256(canonical(skill['implementation'])).hexdigest()
        arm_assets = {
            'A': {'sha256': sha(root / 'independent/solver.py'), 'source': 'independent/solver.py'},
            'B': {'sha256': shared_identity, 'source': 'Canonical SHA256 of exact admitted implementation descriptor', 'skill': f'{skill_name}@{version}'},
            'C': {'sha256': shared_identity, 'source': 'Same admitted skill as B; graph and registry selection evidence remain separately measured', 'skill': f'{skill_name}@{version}'},
            'D': {'sha256': sha(root / 'conventional/solver.py'), 'source': 'conventional/solver.py'}}
        for arm in ARMS:
            arm_assets[arm]['acceptance_sha256'] = sha(records_path)
            arm_assets[arm]['acceptance_scope'] = f'Full 144-record preserved cohort; filter family={family_name}, arm={arm} without removing failures'
        by_arm = {}
        for arm in ARMS:
            included = lambda: fact(0, 'included_in_construction', 'Already inside this arm\'s measured full construction interval; zero additional charge, not zero effort')
            if arm in ['A', 'D']:
                total = assumptions['independent_A_total_elapsed_seconds' if arm == 'A' else 'conventional_D_total_elapsed_seconds']
                by_arm[arm] = {'construction': fact(total / 3, 'measured_elapsed_allocation', assumptions['allocation_rule']),
                    'failedCandidates': included(), 'validation': included(), 'integration': included()}
            else:
                by_arm[arm] = {
                    'construction': fact(assumptions['shared_B_C_construction_proxy_seconds_by_family'][generation],
                        'scenario_resource_proxy', assumptions['shared_construction_basis']),
                    'failedCandidates': fact(failed_shared_elapsed / 3, 'measured_elapsed_allocation',
                        'Unsuccessful development campaign elapsed allocated once across three families, separate from unmetered authoring proxy'),
                    'validation': fact(admission['elapsed_seconds'] / 3, 'measured_elapsed_allocation',
                        'Actual source-bound admission/revalidation elapsed allocated once; CPU is not added again'),
                    'integration': fact(assumptions['shared_integration_proxy_seconds_by_family'][generation],
                        'scenario_resource_proxy', assumptions['shared_integration_basis'])}
        trials = []
        for chain in chains:
            size = indexed[chain, family_name, 'A']['node_count']
            methods = {}
            for arm in ARMS:
                record = indexed[chain, family_name, arm]
                output = within(root, record['output'])
                source_record = output / 'execution.json'
                methods[arm] = {'accepted': record['accepted'], 'cpu_seconds': record['cpu_seconds'],
                    'elapsed_seconds': record['elapsed_seconds'], 'timing_scope': 'complete_stage',
                    'cpu_basis': 'EXPLICITLY_NOT_EXECUTED' if record.get('not_executed') else 'MEASURED_COMPLETE_CHILD_CPU',
                    'not_executed': record.get('not_executed', False), 'blocked': record.get('blocked'),
                    'exit_code': record.get('exit_code'), 'task_sha256': record['task_sha256'],
                    'result_sha256': record.get('result_sha256'),
                    'record_source': {'path': str(source_record.relative_to(root)), 'sha256': sha(source_record)}
                        if source_record.exists() else {'path': str(records_path.relative_to(root)), 'sha256': sha(records_path)}}
            trials.append({'task_id': indexed[chain, family_name, 'A']['id'], 'chain_id': chain,
                'difficulty': 'standard' if size in [100, 625] else 'hard', 'node_count': size,
                'before': {'accepted': None, 'cpu_seconds': None, 'basis': 'NOT_RUN'}, 'methods': methods})
        result['families'].append({'id': generation, 'title': family_name, 'prerequisites': [] if generation == 'G1' else [f'G{int(generation[1]) - 1}'],
            'arm_assets': arm_assets, 'tested': True, 'tested_interpretation': 'Actual source-bound admitted prototype; per-case failures retained below',
            'resources': {'by_arm': by_arm}, 'trials': trials})
    for arm, total in [('A', assumptions['independent_A_total_elapsed_seconds']), ('D', assumptions['conventional_D_total_elapsed_seconds'])]:
        result['resource_allocation'].append({'arm': arm, 'category': 'construction', 'total_seconds': total,
            'basis': 'measured_elapsed_allocation', 'allocation_basis': assumptions['allocation_rule']})
    for arm in ['B', 'C']:
        for category, total in [('failedCandidates', failed_shared_elapsed), ('validation', admission['elapsed_seconds'])]:
            result['resource_allocation'].append({'arm': arm, 'category': category, 'total_seconds': total,
                'basis': 'measured_elapsed_allocation', 'allocation_basis': 'One original interval allocated equally across three families; arms are mutually exclusive counterfactual enterprises, not added together as actual study cost'})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--primary', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('calibration.json'))
    args = parser.parse_args()
    value = build(args.root, args.primary)
    with args.output.open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'written': str(args.output), 'sha256': sha(args.output), 'families': len(value['families']),
        'primary_records': value['provenance']['primary_records']['records'], 'market_outcomes_run': 0}))
