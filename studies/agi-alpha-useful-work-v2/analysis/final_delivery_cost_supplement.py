# SPDX-License-Identifier: Apache-2.0
"""Append final delivery resources to the existing finite capability account.

This postfreeze analysis never executes a consumer, modifies a primary result,
prices an unknown, or makes a financial transaction. A pending required receipt
prevents finalization. Output editions are immutable and may travel outside the
already sealed companion to avoid self-referential archive rebuilding.
"""

import argparse
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import resource
import subprocess
import time


FIELDS = (
    'wall_seconds', 'child_cpu_seconds', 'meter_cpu_seconds',
    'child_peak_rss_kib', 'network_requests', 'network_response_bytes',
    'runtime_model_calls', 'inference_tokens', 'human_minutes',
    'customer_minutes',
)
MISSIONS = {'starlette-1', 'starlette-2', 'starlette-3', 'pydantic-1', 'pydantic-2', 'pydantic-3'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def read_pinned(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Source hash mismatch: ' + str(path))
    return json.loads(data), data


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def within(root, name):
    path = (root / name).resolve()
    delivery_root = root.parent.parent / 'deliverables'
    if not path.is_relative_to(root) and not path.is_relative_to(delivery_root):
        raise ValueError('Evidence must remain inside the project or its workspace deliverables directory')
    return path


def resource_reference(root, path):
    return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)


def pointer(value, keys):
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def quantity(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Resource quantity must be a number or null')
    if not math.isfinite(value) or value < 0:
        raise ValueError('Resource quantity must be finite and nonnegative')
    return value


def identity_hashes(value):
    """Find preserved source bindings, including normalized/outer source links."""
    found = set()
    if isinstance(value, dict):
        if isinstance(value.get('sha256'), str):
            found.add(value['sha256'])
        if isinstance(value.get('evidence_sha256'), str):
            found.add(value['evidence_sha256'])
        for child in value.values():
            found.update(identity_hashes(child))
    elif isinstance(value, list):
        for child in value:
            found.update(identity_hashes(child))
    return found


def stats(rows):
    out = {}
    for key in FIELDS:
        values = [row['resources'].get(key) for row in rows]
        measured = [value for value in values if value is not None]
        out[key] = {
            'known_subtotal': sum(measured) if measured else None,
            'measured_records': len(measured),
            'unknown_records': len(values) - len(measured),
            'complete_total': sum(measured) if len(measured) == len(values) and values else None,
        }
    # Peak RSS is a maximum, never an additive memory bill.
    peaks = [row['resources'].get('child_peak_rss_kib') for row in rows]
    peaks = [value for value in peaks if value is not None]
    out['child_peak_rss_kib'] = {
        'observed_maximum': max(peaks) if peaks else None,
        'scope': 'Maximum observed child peak; not simultaneous memory or a bill.',
    }
    return out


def collect(root, plan):
    if plan.get('schema') != 'same-capability-delivery-cost-plan/v1':
        raise ValueError('Unsupported plan schema')
    if plan.get('capability_id') != 'component-compatibility' or plan.get('investment_account') != 'study-investment':
        raise ValueError('Supplement must extend the same tested capability account')
    base_path = within(root, plan['base_evidence']['path'])
    base, _ = read_pinned(base_path, plan['base_evidence']['sha256'])
    if base['capability_id'] != plan['capability_id'] or len(base['missions']) != 6 or {row.get('mission_id') for row in base['missions']} != MISSIONS:
        raise ValueError('Base capability or primary mission inventory changed')
    if base['actual_collections_minor'] != 0 or base['customer_price_minor'] is not None:
        raise ValueError('Unsupported financial state in base evidence')
    known_hashes = identity_hashes(base)
    known_paths = {row['evidence_path'] for row in base['resource_entries']}
    for path in known_paths:
        source = within(root, path)
        known_hashes.add(sha(source))
        if source.suffix == '.json':
            known_hashes.update(identity_hashes(read(source)))
    existing_snapshot = within(root, plan['base_cost_snapshot']['path'])
    snapshot, _ = read_pinned(existing_snapshot, plan['base_cost_snapshot']['sha256'])
    known_hashes.update(identity_hashes(snapshot))
    ids, used_hashes, rows, pending = set(), set(), [], []
    entries = plan['entries']
    active_paths = {entry.get('source_path') for entry in entries if entry.get('source_path') and entry.get('accounting_role', 'additive') == 'additive'}
    for entry in entries:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', entry['id']):
            raise ValueError('Supplement entry ID must be a safe local identifier')
        if type(entry.get('required', True)) is not bool:
            raise ValueError('Required receipt flag must be a typed boolean')
        if entry.get('outcome') not in {'succeeded', 'failed', 'unknown'}:
            raise ValueError('Unsupported activity outcome')
        if entry['id'] in ids:
            raise ValueError('Duplicate supplement entry ID')
        ids.add(entry['id'])
        if entry.get('accounting_role', 'additive') not in {'additive', 'documentary'}:
            raise ValueError('Unknown accounting role')
        if active_paths.intersection(entry.get('covers_sources', [])):
            raise ValueError('Nested cost source is also an additive envelope')
        if entry.get('activity_state') != 'completed' or not entry.get('source_path'):
            pending.append({'id': entry['id'], 'required': entry.get('required', True), 'reason': 'Activity or pinned receipt is still pending', 'description': entry['description']})
            continue
        path = within(root, entry['source_path'])
        if not path.is_file():
            raise ValueError('Supplement source missing or hash mismatch: ' + entry['id'])
        raw, source_bytes = read_pinned(path, entry.get('source_sha256'))
        if raw.get('schema') != entry.get('source_schema'):
            raise ValueError('Supplement receipt schema mismatch: ' + entry['id'])
        check = entry.get('completion_check')
        if not check or pointer(raw, check['path']) != check['equals'] or type(pointer(raw, check['path'])) is not type(check['equals']):
            raise ValueError('Required typed activity-completion evidence missing: ' + entry['id'])
        digest = hashlib.sha256(source_bytes).hexdigest()
        if entry.get('accounting_role', 'additive') == 'additive':
            if digest in known_hashes or digest in used_hashes:
                raise ValueError('Receipt already charged or copied twice: ' + entry['id'])
            used_hashes.add(digest)
        resources = {key: quantity(pointer(raw, entry['resource_fields'][key])) if key in entry.get('resource_fields', {}) else None for key in FIELDS}
        resources['money_usd'] = None
        rows.append({'entry': entry, 'source': {'path': entry['source_path'], 'sha256': digest, 'bytes': len(source_bytes)}, 'source_bytes': source_bytes, 'raw': raw, 'resources': resources})
    return base, rows, pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--finalize', action='store_true', help='Require every mandatory activity receipt and regenerate the same canonical account')
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    delivery_root = root.parent.parent / 'deliverables'
    if (not out.is_relative_to(root) and not out.is_relative_to(delivery_root)) or out.exists():
        raise ValueError('Use a new output edition inside the project or workspace deliverables directory')
    started = time.perf_counter()
    cpu = time.process_time()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    plan_bytes = args.plan.read_bytes()
    plan = json.loads(plan_bytes)
    base, rows, pending = collect(root, plan)
    required_pending = [row for row in pending if row['required']]
    if args.finalize and required_pending:
        raise ValueError('Cannot finalize while required activities are pending: ' + ', '.join(row['id'] for row in required_pending))
    out.mkdir(parents=True)
    (out / 'plan.json').write_bytes(plan_bytes)
    evidence = copy.deepcopy(base)
    records = []
    for row in rows:
        entry = row['entry']
        raw_path = out / 'sources' / (entry['id'] + '.json')
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(row['source_bytes'])
        normalized_path = out / 'resources' / (entry['id'] + '.json')
        write(normalized_path, {'schema': 'same-capability-delivery-resource/v1', **row['resources'], 'original_source': row['source'], 'scope': entry['description'], 'aggregation': entry['aggregation']})
        mapped = {'id': 'final-delivery-' + entry['id'], 'ownership': 'shared_investment', 'arm': 'shared', 'outcome': entry['outcome'], 'accounting_role': entry.get('accounting_role', 'additive'), 'stages': entry.get('stages', ['verification', 'packaging', 'reporting']), 'evidence_path': resource_reference(root, normalized_path), 'evidence_sha256': sha(normalized_path), 'lifecycle_phase': entry['phase']}
        evidence['resource_entries'].append(mapped)
        records.append({**mapped, 'original_source': row['source'], 'resources': row['resources']})
    pending_path = out / 'pending-activities.json'
    write(pending_path, {'schema': 'same-capability-pending-delivery-activities/v1', 'pending': pending, 'cost_policy': 'Pending work is not claimed executed; no absent monetary quantity is zero.'})
    evidence['resource_entries'].append({'id': 'final-delivery-pending-inventory', 'ownership': 'shared_investment', 'arm': 'shared', 'outcome': 'unknown', 'accounting_role': 'documentary', 'stages': [], 'evidence_path': resource_reference(root, pending_path), 'evidence_sha256': sha(pending_path)})
    if evidence['missions'] != base['missions']:
        raise AssertionError('Primary mission changes are forbidden')
    evidence_path = out / 'economic-evidence.json'
    write(evidence_path, evidence)
    additive = [row for row in records if row['accounting_role'] == 'additive']
    result = {'schema': 'same-capability-final-delivery-cost-supplement/v1', 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'RECEIPT_INVENTORY_FINALIZED' if args.finalize else 'DRAFT_NOT_FINALIZED', 'capability_id': plan['capability_id'], 'investment_account': plan['investment_account'], 'base_evidence': plan['base_evidence'], 'plan_sha256': hashlib.sha256(plan_bytes).hexdigest(), 'primary_missions': 6, 'new_missions': 0, 'additional_capabilities': 0, 'records': records, 'pending': pending, 'additional_known_resources': stats(additive), 'complete_monetary_cost': None, 'actual_collections_minor': 0, 'customer_price_minor': None, 'approved_monetary_allocation_minor': None, 'available_cash_minor': None, 'earned_surplus_minor': None, 'financeable_expansion_proven': False, 'allocation_finding': 'Completed records show continued work within existing session-authorized research and engineering resources on this same asset. They establish resource use, not a priced budget, earned surplus, cash availability, another financed capability or sustained acceleration.', 'self_cost_boundary': 'This supplement preparation/canonical execution is separately metered after its input cutoff; preserve its outer receipt without recursively rebuilding the already sealed companion.', 'scope': 'Complete receipt inventory does not mean complete monetary cost. Same canonical account with extended resources; no transaction or new paid commitment.'}
    if args.finalize:
        command = ['node', str(root / 'analysis/economics.mjs'), '--input', str(evidence_path), '--root', str(root), '--out', str(out / 'canonical-economics')]
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        write(out / 'canonical-execution.json', {'command': command, 'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr, 'money_usd': None})
        if process.returncode:
            result['status'] = 'CANONICAL_MAPPING_FAILED'
            write(out / 'cost-supplement.json', result)
            raise RuntimeError('Canonical accounting rejected the supplement')
        final = read(out / 'canonical-economics/economics.json')
        if final['distinct_substantive_missions'] != 6 or final['finance']['actual_collections_minor'] != 0 or final['finance']['available_surplus_minor'] is not None:
            raise AssertionError('Unsupported mission or financial change')
        result['canonical_economics_sha256'] = sha(out / 'canonical-economics/economics.json')
    write(out / 'cost-supplement.json', result)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    write(out / 'supplement-construction-receipt.json', {'schema': 'supplement-construction-receipt/v1', 'wall_seconds': time.perf_counter() - started, 'process_cpu_seconds': time.process_time() - cpu, 'child_cpu_seconds': after.ru_utime + after.ru_stime - usage.ru_utime - usage.ru_stime, 'money_usd': None, 'inference_tokens': None, 'new_missions': 0, 'aggregation': 'Encloses supplement generation and canonical subprocess if finalized. Do not add inner canonical process a second time or recursively repack.'})
    print(json.dumps({'status': result['status'], 'completed_records': len(rows), 'required_pending': len(required_pending), 'new_missions': 0, 'complete_monetary_cost': None, 'out': str(out)}))


if __name__ == '__main__':
    main()
