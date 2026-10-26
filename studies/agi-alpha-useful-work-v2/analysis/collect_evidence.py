# SPDX-License-Identifier: Apache-2.0
"""Post-freeze accounting mapping only; never executes a consumer or changes a gate.

The six frozen missions and all eighteen declared arm runs are retained, including
failures. Complete ledger emission waits for eighteen terminal run records. This
collector does not select cases, change acceptance, retry workers, or price time.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
FREEZE_SHA256 = 'f417768b69a6729000d5ce9d10393bfac7eec45b7ce448a0d61c711a6662530c'
ARMS = ('manual', 'retained', 'conventional')
STAGES = ['preparation', 'planning', 'execution', 'verification', 'correction', 'packaging', 'reporting', 'recovery']
ACCEPTED = {'SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION'}
PRESERVED = 'PRESERVED_WITHIN_COMPONENT_CONTRACT'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def complete_sum(values):
    return sum(values) if values and all(number(v) is not None for v in values) else None


def ident(path, root):
    path = path.resolve()
    return {'path': str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            'sha256': sha(path), 'bytes': path.stat().st_size}


def local(root, path):
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Evidence path outside study root')
    return result


def source_check(root):
    path = root / 'protocol/source-freeze.json'
    if sha(path) != FREEZE_SHA256:
        raise ValueError('Primary freeze identity changed')
    frozen = read(path)
    errors = []
    for row in frozen['files']:
        target = local(root, row['path'])
        if not target.is_file() or sha(target) != row['sha256'] or target.stat().st_size != row['bytes']:
            errors.append(row['path'])
    if errors:
        raise ValueError('Frozen files changed: ' + ', '.join(errors))
    protocol = read(root / 'protocol/primary-protocol.json')
    if sha(root / 'protocol/primary-protocol.json') != frozen['protocol_sha256']:
        raise ValueError('Primary protocol identity changed')
    if len(protocol['mission_order']) != 6 or any(set(row['arms']) != set(ARMS) for row in protocol['mission_order']):
        raise ValueError('Expected six declared three-arm missions')
    return protocol, {'freeze': ident(path, root), 'files_checked': len(frozen['files']), 'all_match': True,
                      'frozen_at': frozen['frozen_at']}


def choose(root, explicit, candidates, label, optional=False):
    if explicit:
        path = local(root, explicit)
        if not path.is_file():
            if optional:
                return None
            raise FileNotFoundError(str(path))
        return path
    present = list(dict.fromkeys(path.resolve() for path in candidates if path.is_file()))
    if len(present) > 1:
        raise ValueError('Ambiguous ' + label + '; provide explicit analysis layout: ' + ', '.join(map(str, present)))
    if not present:
        if optional:
            return None
        raise FileNotFoundError(label)
    return present[0]


def discover_run(root, mission, arm, overrides):
    base = root / 'results/confirmation' / mission / arm
    cfg = overrides.get(f'{mission}/{arm}', {})
    result = {'mission_id': mission, 'arm': arm, 'base': base, 'layout_override': cfg}
    result['terminal_path'] = choose(root, cfg.get('terminal'), [base / 'terminal.json'], 'campaign terminal', True)
    terminal = read(result['terminal_path']) if result['terminal_path'] else {}
    result['terminal_record'] = terminal
    result['terminal'] = (terminal.get('schema') == 'useful-work-campaign-terminal/v1'
                          and terminal.get('mission_id') == mission and terminal.get('arm') == arm
                          and bool(terminal.get('ended_at')) and number(terminal.get('service_span_seconds')) is not None)
    result['decision_path'] = choose(root, cfg.get('decision'), [base / 'package/decision.json', base / 'delivery/package/decision.json'], 'decision', True)
    result['delivery_path'] = choose(root, cfg.get('delivery'), [base / 'delivery.json', base / 'delivery/delivery.json'], 'delivery', True)
    if arm == 'manual':
        result['span_path'] = result['terminal_path']
        result['mechanical_path'] = choose(root, cfg.get('mechanical', terminal.get('mechanical_pair')), [base / 'pair/pair.json'], 'manual mechanics', True)
        result['finalization_path'] = choose(root, cfg.get('finalization'), [base / name for name in ['finalization-execution.json', 'assembly-execution.json', 'package-execution.json']], 'manual finalization', True)
    else:
        result['outer_path'] = choose(root, cfg.get('outer'), [base / 'execution.json', base / 'workbench-execution.json',
            base / 'delivery-execution.json', base.parent / (arm + '-execution.json')], 'outer execution', True)
    return result


def validate_package(root, run, job, contract):
    """Reconcile frozen producer verdict with its already-executed evidence."""
    path = run['decision_path']
    if path is None:
        return {'accepted': False, 'decision': 'INCOMPLETE_HOLD', 'independently_verified': False,
                'errors': ['No decision packet'], 'evidence_path': None, 'manifest_files': 0}
    packet = read(path)
    errors = []
    terminal = run['terminal_record']
    if terminal.get('accepted') is not True or terminal.get('error'):
        errors.append('Campaign terminal did not accept completed delivery')
    if terminal.get('decision_sha256') != sha(path) or terminal.get('decision') != packet.get('decision'):
        errors.append('Campaign terminal/decision binding mismatch')
    if packet.get('schema') != 'alpha-component-decision/v1' or packet.get('mission_id') != run['mission_id'] or packet.get('phase') != 'confirmation':
        errors.append('Packet identity mismatch')
    if packet.get('job_sha256') != sha(root / job['path']):
        errors.append('Packet job hash mismatch')
    decision = packet.get('decision', 'INCOMPLETE_HOLD')
    if packet.get('custody_failures') or packet.get('custody_errors'):
        errors.append('Producer reported custody gaps')
    package = path.parent
    manifest_path = package / 'artifact-manifest.json'
    manifest = read(manifest_path) if manifest_path.is_file() else {'files': []}
    if not manifest['files']:
        errors.append('Package manifest missing or empty')
    seen = set()
    for item in manifest['files']:
        relative = Path(item['path'])
        target = (package / relative).resolve()
        if item['path'] in seen or relative.is_absolute() or '..' in relative.parts or not target.is_relative_to(package.resolve()):
            errors.append('Unsafe or duplicate package manifest entry')
            continue
        seen.add(item['path'])
        if not target.is_file() or sha(target) != item['sha256'] or target.stat().st_size != item['bytes']:
            errors.append('Package content mismatch:' + item['path'])
    for name in ('decision.json', 'requirement-results.json', 'proposed-component-lock.patch', 'reproduce.txt'):
        if name not in seen:
            errors.append('Missing required package output:' + name)
    if not (package / 'report-en.html').is_file() and not (package / 'README.md').is_file():
        errors.append('English readable result absent')
    if not (package / 'report-fr.html').is_file() and not (package / 'README.fr.md').is_file():
        errors.append('French readable result absent')
    verification = {}
    expected_ids = {case['id'] for case in contract['cases']}
    for side in ('before', 'after'):
        record = package / 'evidence' / f'{side}-verification.json'
        observation = package / 'evidence' / f'{side}-observations.json'
        if not record.is_file() or not observation.is_file():
            errors.append('Independent evidence absent:' + side)
            continue
        proof = read(record)
        verification[side] = proof
        ids = [case.get('id') for case in proof.get('cases', [])]
        if proof.get('schema') != 'independent-component-verification/v1' or proof.get('observations_sha256') != sha(observation):
            errors.append('Independent evidence binding:' + side)
        if len(ids) != len(expected_ids) or set(ids) != expected_ids:
            errors.append('Incomplete independent case inventory:' + side)
        if proof.get('global_incomplete'):
            errors.append('Independent verifier reported incompleteness:' + side)
    before = verification.get('before', {}).get('status')
    after = verification.get('after', {}).get('status')
    if decision == 'SCOPED_COMPONENT_PRESERVED' and (before != PRESERVED or after != PRESERVED):
        errors.append('Preserved verdict does not match independent result')
    if decision == 'COMPONENT_REGRESSION' and (before != PRESERVED or after != 'BEHAVIOR_MISMATCH'):
        errors.append('Regression verdict does not match independent result')
    return {'accepted': decision in ACCEPTED and not errors, 'decision': decision,
            'independently_verified': decision in ACCEPTED and not errors, 'errors': errors,
            'evidence_path': str(path.relative_to(root)), 'evidence_sha256': sha(path),
            'manifest_files': len(manifest['files']),
            'verification_status': {'before': before, 'after': after},
            'verification_counts': {side: proof.get('counts') for side, proof in verification.items()}}


def normalize(raw):
    """Only rename observed resource quantities; never price or fill an unknown."""
    return {'wall_seconds': number(raw.get('wall_seconds')),
            'child_cpu_seconds': number(raw.get('child_cpu_seconds')),
            'meter_cpu_seconds': number(raw.get('meter_cpu_seconds', raw.get('process_cpu_seconds', raw.get('cpu_seconds')))),
            'child_peak_rss_kib': number(raw.get('child_peak_rss_kib', raw.get('self_peak_rss_kib'))),
            'network_requests': number(raw.get('network_requests', raw.get('runtime_network_requests'))),
            'network_response_bytes': number(raw.get('network_response_bytes')),
            'runtime_model_calls': number(raw.get('runtime_model_calls')),
            'inference_tokens': number(raw.get('inference_tokens')),
            'human_minutes': number(raw.get('human_minutes')),
            'customer_minutes': number(raw.get('customer_minutes')),
            'money_usd': None}


def duration(raw, key=None):
    keys = [key] if key else ['service_span_seconds', 'request_to_package_span_seconds', 'mission_span_seconds', 'wall_seconds']
    values = [(name, number(raw.get(name))) for name in keys if name]
    values = [(name, value) for name, value in values if value is not None]
    if values:
        return values[0][1], values[0][0]
    first, last = raw.get('started_at'), raw.get('ended_at', raw.get('completed_at'))
    if first and last:
        value = (datetime.datetime.fromisoformat(last.replace('Z', '+00:00'))
                 - datetime.datetime.fromisoformat(first.replace('Z', '+00:00'))).total_seconds()
        if value >= 0:
            return value, 'UTC timestamp interval; not a human or inference bill'
    return None, 'Unmeasured span'


def materialize_run(root, out, run, quality, resources, envelopes):
    mission, arm = run['mission_id'], run['arm']
    row_id = f'{mission}-{arm}-delivery'
    terminal = run['terminal_record']
    sources = [run['terminal_path']]
    values = normalize({})
    values['wall_seconds'] = number(terminal.get('service_span_seconds'))
    values['child_cpu_seconds'] = number(terminal.get('inclusive_child_cpu_seconds'))
    values['meter_cpu_seconds'] = number(terminal.get('driver_process_cpu_seconds'))
    values['child_peak_rss_kib'] = number(terminal.get('child_peak_rss_kib'))
    chronology = {'started_at': terminal.get('started_at'), 'ended_at': terminal.get('ended_at')}
    span_basis = 'Campaign terminal encloses this complete arm delivery and its local driver overhead; never add nested receipts.'
    pair_wall = None
    if arm == 'manual':
        mechanical = read(run['mechanical_path']) if run['mechanical_path'] else {}
        finalization = read(run['finalization_path']) if run['finalization_path'] else {}
        values['runtime_model_calls'] = None
        values['runtime_network_requests'] = None
        sources += [p for p in [run['mechanical_path'], run['finalization_path']] if p]
        pair_wall = number(mechanical.get('wall_seconds'))
        finalization_wall = number(finalization.get('wall_seconds'))
        mechanical_wall = complete_sum([pair_wall, finalization_wall])
        notes = ['Manual elapsed span is observed researcher-assisted turnaround, not measured no-AI human work.',
                 'Terminal CPU includes the local mechanics/finalization and driver; researcher inference and unmetered remote resources remain unknown.',
                 'Mechanical elapsed and finalization elapsed are retained separately and are not added to the inclusive service span.']
    else:
        outer = read(run['outer_path']) if run['outer_path'] else {}
        delivery = read(run['delivery_path']) if run['delivery_path'] else {}
        # Worker activity is a separate declared observation from the inspected
        # frozen complete path, never inferred from meter_model_calls.
        values['runtime_model_calls'] = number(delivery.get('runtime_model_calls'))
        values['network_requests'] = number(delivery.get('runtime_network_requests'))
        sources += ([run['outer_path']] if run['outer_path'] else []) + ([run['delivery_path']] if run['delivery_path'] else [])
        mechanical_wall = number(outer.get('wall_seconds'))
        finalization_wall = None
        notes = ['Terminal totals enclose external command totals, which themselves enclose delivery, pair, verifier and case receipts; sum this hierarchy only once.',
                 'Known runtime worker activity excludes research/construction inference, which is unknown and charged separately.']
    values.update(schema='postfreeze-derived-delivery-resource/v1', mission_id=mission, arm=arm,
                  source_identities=[ident(p, root) for p in sources], span_basis=span_basis,
                  complete_delivery_scope=quality['accepted'], observed_mechanical_wall_seconds=mechanical_wall,
                  observed_finalization_wall_seconds=finalization_wall, observed_manual_pair_wall_seconds=pair_wall,
                  actual_manual_finalizations=terminal.get('manual_finalizations'), limitations=notes, **chronology)
    derived = out / 'derived' / f'{mission}-{arm}-delivery.json'
    write(derived, values)
    resources.append({'id': row_id, 'ownership': 'delivery', 'arm': arm, 'mission_id': mission,
        'outcome': 'succeeded' if quality['accepted'] else 'failed', 'accounting_role': 'additive',
        'stages': STAGES, 'evidence_path': str(derived.relative_to(root)), 'evidence_sha256': sha(derived),
        'lifecycle_phase': 'primary-delivery', 'note': 'Derived exactly from pinned inclusive/disjoint sources; no monetary conversion.'})
    for index, path in enumerate(sources):
        resources.append({'id': f'{row_id}-source-{index}', 'ownership': 'delivery', 'arm': arm, 'mission_id': mission,
            'outcome': 'succeeded' if quality['accepted'] else 'failed', 'accounting_role': 'nested_evidence',
            'covered_by': row_id, 'stages': [], 'evidence_path': str(path.relative_to(root)), 'evidence_sha256': sha(path),
            'lifecycle_phase': 'primary-source-receipt'})
    envelopes.append({'mission_id': mission, 'arm': arm, 'scope_complete': quality['accepted'], 'resource_ids': [row_id]})
    return {'mission_id': mission, 'arm': arm, **quality, **chronology,
            'request_to_package_wall_seconds': values['wall_seconds'],
            'mechanical_wall_seconds': mechanical_wall, 'finalization_wall_seconds': finalization_wall,
            'manual_pair_wall_seconds': pair_wall, 'actual_manual_finalizations': terminal.get('manual_finalizations'),
            'earlier_arms_visible': terminal.get('earlier_arms_visible'), 'sequence': terminal.get('sequence'),
            'measured_local_child_cpu_seconds': values['child_cpu_seconds'],
            'measured_local_controller_cpu_seconds': values['meter_cpu_seconds'],
            'measured_local_cpu_seconds': complete_sum([values['child_cpu_seconds'], values['meter_cpu_seconds']]),
            'runtime_model_calls': values['runtime_model_calls'], 'complete_cost_usd': None,
            'researcher_or_customer_minutes': None, 'cost_provenance': ident(derived, root)}


def acquisition(root, out, construction, resources):
    source = root / 'data/confirmation-inputs/acquisition-summary.json'
    raw = read(source)
    if raw.get('freeze_sha256') != FREEZE_SHA256 or raw.get('attempt_count') != 8 or len(raw.get('attempts', [])) != 8:
        raise ValueError('Acquisition does not match fixed eight-profile campaign')
    if {a['environment_id'] for a in raw['attempts']} != {a['id'] for a in construction['environments']}:
        raise ValueError('Acquisition replaced or omitted a selected environment')
    for attempt in raw['attempts']:
        path = local(root, attempt['preparation_path'])
        if path.is_file() and sha(path) != attempt['preparation_sha256']:
            raise ValueError('Preparation identity mismatch')
    derived = out / 'derived/shared-acquisition.json'
    values = {'schema': 'postfreeze-shared-acquisition-resource/v1',
        'wall_seconds': number(raw.get('driver_wall_seconds')),
        'child_cpu_seconds': number(raw.get('driver_child_cpu_seconds_inclusive')),
        'meter_cpu_seconds': number(raw.get('driver_process_cpu_seconds')),
        'network_requests': number(raw.get('network_requests')),
        'network_response_bytes': number(raw.get('network_response_bytes')),
        'logical_storage_bytes_before_final_reports': number(raw.get('logical_storage_bytes_before_final_reports_sum')),
        'inference_tokens': None, 'money_usd': None, 'source_identity': ident(source, root),
        'aggregation': 'Outer driver child CPU includes all eight builders/setup children. Inner preparation CPU and wall are nested diagnostics, not added.',
        'attempts': raw['attempt_count'], 'failed_attempts': raw.get('failed_environments'),
        'inner_preparation_diagnostics': {k: raw.get(k) for k in ['preparation_wall_seconds_sum', 'preparation_process_cpu_seconds_sum', 'preparation_child_cpu_seconds_sum']}}
    write(derived, values)
    resources.append({'id': 'shared-primary-acquisition', 'ownership': 'shared_investment', 'arm': 'shared',
        'outcome': 'failed' if raw.get('failed_environments') else 'succeeded', 'accounting_role': 'additive',
        'stages': ['preparation'], 'evidence_path': str(derived.relative_to(root)),
        'evidence_sha256': sha(derived), 'lifecycle_phase': 'primary-acquisition'})
    for index, attempt in enumerate(raw['attempts']):
        path = local(root, attempt['preparation_path'])
        if path.is_file():
            resources.append({'id': f'shared-primary-preparation-{index+1}', 'ownership': 'shared_investment', 'arm': 'shared',
                'outcome': 'succeeded' if attempt.get('complete') is True else 'failed',
                'accounting_role': 'nested_evidence', 'covered_by': 'shared-primary-acquisition', 'stages': [],
                'evidence_path': str(path.relative_to(root)), 'evidence_sha256': sha(path), 'lifecycle_phase': 'primary-acquisition'})
    return values


def lifecycle(root, out, manifest_path, resources):
    mapping = read(manifest_path) if manifest_path else {'schema': 'postfreeze-lifecycle-resource-map/v1', 'entries': [], 'exclusions': []}
    if mapping.get('schema') != 'postfreeze-lifecycle-resource-map/v1':
        raise ValueError('Lifecycle ownership schema')
    seen_hashes, records = set(), []
    exclusions = list(mapping.get('exclusions', []))
    for entry in mapping['entries']:
        path = local(root, entry['evidence_path'])
        if not path.is_file():
            raise FileNotFoundError('Lifecycle source missing: ' + str(path))
        content_hash = sha(path)
        if entry.get('evidence_sha256') and content_hash != entry['evidence_sha256']:
            raise ValueError('Lifecycle evidence changed: ' + str(path))
        if entry['accounting_role'] == 'additive' and content_hash in seen_hashes:
            raise ValueError('Byte-identical copied receipt counted twice: ' + str(path))
        if entry['accounting_role'] == 'additive':
            seen_hashes.add(content_hash)
        if entry.get('format') == 'jsonl' or entry['accounting_role'] != 'additive':
            if entry.get('format') == 'jsonl':
                snapshot = out / 'evidence/lifecycle' / (entry['id'] + '.jsonl')
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                snapshot.write_bytes(path.read_bytes())
                resources.append({**entry, 'evidence_path': str(snapshot.relative_to(root)),
                                  'evidence_sha256': sha(snapshot), 'original_source_path': str(path.relative_to(root))})
            else:
                resources.append({**entry, 'evidence_sha256': content_hash})
            continue
        raw = read(path)
        if entry.get('resource_pointer'):
            raw = raw[entry['resource_pointer']]
        normalized = normalize(raw)
        normalized.update(schema='postfreeze-normalized-lifecycle-resource/v1', source_identity=ident(path, root),
            monetary_cost_usd=None, lifecycle_phase=entry.get('lifecycle_phase'),
            note='Resource field normalization only; original receipt retained. No unknown filled as zero.')
        derived = out / 'derived/lifecycle' / (entry['id'] + '.json')
        write(derived, normalized)
        resources.append({**entry, 'evidence_path': str(derived.relative_to(root)), 'evidence_sha256': sha(derived)})
        records.append({**entry, 'original_evidence': ident(path, root), 'normalized_evidence': ident(derived, root), 'resources': normalized})
    # Logs retain authoring, model/tool work, unknown launch costs and reporting
    # actions without treating their often overlapping timestamps as a CPU bill.
    registered_paths = {row['evidence_path'] for row in resources}
    for index, path in enumerate(sorted((root / 'metering').glob('*.jsonl'))):
        relative = str(path.relative_to(root))
        if path.name == 'prior-delivery-recovery.jsonl':
            exclusions.append({'path': relative, 'sha256_at_collection': sha(path),
                'cost_account': 'Prior V1 delivery recovery, explicitly assigned by the source owner and root',
                'reason': 'Separate historical deliverable recovery; not an attributable V2 component-capability investment.'})
            continue
        if relative not in registered_paths:
            snapshot = out / 'evidence/metering' / path.name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(path.read_bytes())
            resources.append({'id': f'full-study-event-log-{index+1}', 'ownership': 'shared_investment', 'arm': 'shared',
                'outcome': 'unknown', 'accounting_role': 'documentary', 'format': 'jsonl', 'stages': [],
                'evidence_path': str(snapshot.relative_to(root)), 'evidence_sha256': sha(snapshot),
                'original_source_path': relative, 'lifecycle_phase': 'authoring-and-tool-provenance'})
    gaps = out / 'derived/unpriced-unmetered-lifecycle.json'
    write(gaps, {'schema': 'unpriced-lifecycle-cost-gaps/v1', **normalize({}),
        'gaps': ['Complete construction/research inference calls, tokens and charges',
                 'Researcher active attention distinct from elapsed assistant time',
                 'Unmetered launch/diagnostic/review work retained in event logs',
                 'Attributable platform, storage, maintenance and legacy-asset monetary costs',
                 'Publication and final archival work not yet covered by a supplied measured receipt',
                 'Customer effort, validated price, demand, starting capital and approved allocation'],
        'policy': 'Unknowns remain costs to identify, not zero. Supplied known subtotals do not identify complete monetary investment.'})
    resources.append({'id': 'unpriced-unmetered-lifecycle', 'ownership': 'shared_investment', 'arm': 'shared',
        'outcome': 'unknown', 'accounting_role': 'additive', 'stages': STAGES,
        'evidence_path': str(gaps.relative_to(root)), 'evidence_sha256': sha(gaps), 'lifecycle_phase': 'unknown-lifecycle-costs'})
    phases = {}
    for row in records:
        phase = row.get('lifecycle_phase', 'unclassified')
        phases.setdefault(phase, []).append(row)
    totals = {}
    for phase, rows in phases.items():
        quantities = {}
        for key in ('wall_seconds', 'child_cpu_seconds', 'meter_cpu_seconds'):
            values = [row['resources'][key] for row in rows]
            measured = [value for value in values if value is not None]
            quantities[key] = {'complete_total': complete_sum(values), 'known_subtotal': sum(measured) if measured else None,
                               'missing_count': len(values)-len(measured)}
        totals[phase] = {'records': len(rows), 'failed_records': sum(row['outcome']=='failed' for row in rows), 'quantities': quantities, 'money_usd': None}
    return {'mapping': ident(manifest_path, root) if manifest_path else None, 'records': records,
            'by_phase': totals, 'exclusions': exclusions,
            'complete_cost': None, 'scope': 'Known physical subtotals plus explicit gaps; no elapsed-assistant wage or inference charge inferred.'}


def descriptive(values):
    known = [value for value in values if number(value) is not None]
    return {'observations': len(known), 'missing': len(values)-len(known),
            'sum': sum(known) if known else None, 'median': statistics.median(known) if known else None,
            'minimum': min(known) if known else None, 'maximum': max(known) if known else None,
            'scope': 'Descriptive single-run measurements on a shared host, not a reliability estimate or significance test.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--layout', type=Path)
    parser.add_argument('--lifecycle', type=Path)
    parser.add_argument('--readiness-only', action='store_true')
    parser.add_argument('--emit-canonical', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    start, cpu = time.perf_counter(), time.process_time()
    protocol, freeze_check = source_check(root)
    layout = read(args.layout) if args.layout else {'runs': {}}
    construction_path = root / 'data/confirmation-inputs/construction.json'
    construction = read(construction_path)
    if construction.get('freeze_sha256') != FREEZE_SHA256:
        raise ValueError('Input construction belongs to another epoch')
    jobs = {job['id']: job for job in construction['jobs']}
    expected = [row['mission'] for row in protocol['mission_order']]
    if set(jobs) != set(expected):
        raise ValueError('Input jobs differ from the frozen selection')
    runs = [discover_run(root, row['mission'], arm, layout.get('runs', {}))
            for row in protocol['mission_order'] for arm in row['arms']]
    missing = [f"{run['mission_id']}/{run['arm']}" for run in runs if not run['terminal']]
    readiness = {'schema': 'postfreeze-campaign-readiness/v1', 'expected_runs': 18,
                 'terminal_runs': 18-len(missing), 'missing_terminal_runs': missing, 'freeze_check': freeze_check}
    if args.readiness_only or missing:
        print(json.dumps(readiness, indent=2))
        if missing and not args.readiness_only:
            raise SystemExit(2)
        return
    campaign_path = root / 'results/confirmation/campaign.json'
    if not campaign_path.is_file():
        raise ValueError('All terminal records exist but the enclosing campaign is not finalized')
    campaign = read(campaign_path)
    prescribed_order = [(row['mission'], arm) for row in protocol['mission_order'] for arm in row['arms']]
    recorded_order = [(row['mission_id'], row['arm']) for row in campaign.get('results', [])]
    if (campaign.get('schema') != 'useful-work-campaign/v1' or recorded_order != prescribed_order
            or campaign.get('arm_evaluations') != 18 or campaign.get('unique_missions') != 6):
        raise ValueError('Campaign sequence/completeness differs from the frozen eighteen runs')
    if not campaign.get('freeze_before', {}).get('unchanged') or not campaign.get('freeze_after', {}).get('unchanged'):
        raise ValueError('Campaign did not attest frozen identities before/after')
    if not args.out:
        raise ValueError('--out is required for a completed campaign mapping')
    out = args.out.resolve()
    if not out.is_relative_to(root) or out.exists():
        raise ValueError('Use a new output edition inside the study root')
    out.mkdir(parents=True)
    contract = read(root / 'protocol/component-contract.json')
    resources, envelopes, observed = [], [], []
    for run in runs:
        job = jobs[run['mission_id']]
        if sha(root / job['path']) != job['sha256']:
            raise ValueError('Registered job changed after construction')
        try:
            quality = validate_package(root, run, job, contract)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            quality = {'accepted': False, 'decision': 'INCOMPLETE_HOLD', 'independently_verified': False,
                       'errors': [f'Package evidence cannot be verified: {type(exc).__name__}: {exc}'],
                       'evidence_path': None, 'manifest_files': 0}
        observed.append(materialize_run(root, out, run, quality, resources, envelopes))
    setup = acquisition(root, out, construction, resources)
    lifecycle_summary = lifecycle(root, out, args.lifecycle, resources)
    missions = []
    for name in expected:
        job_path = root / jobs[name]['path']
        job = read(job_path)
        outcomes = []
        for arm in ARMS:
            row = next(value for value in observed if value['mission_id']==name and value['arm']==arm)
            evidence_path = row['evidence_path'] or str((out / 'derived' / f'{name}-{arm}-delivery.json').relative_to(root))
            outcomes.append({'arm': arm, 'accepted': row['accepted'], 'independently_verified': row['independently_verified'],
                'decision': row['decision'] if row['decision'] in ACCEPTED else 'INCOMPLETE_HOLD',
                'evidence_path': evidence_path, 'evidence_sha256': sha(root / evidence_path)})
        missions.append({'mission_id': name, 'phase': 'confirmation', 'freshness_status': 'untouched_before_protocol_freeze',
            'trigger': {'kind': 'dependency_bundle',
                'before_identity': hashlib.sha256(json.dumps(job['before']['expected_versions'], sort_keys=True).encode()).hexdigest(),
                'after_identity': hashlib.sha256(json.dumps(job['after']['expected_versions'], sort_keys=True).encode()).hexdigest(),
                'reference': jobs[name]['path'] + '; ' + job['trigger']}, 'outcomes': outcomes})
    economic = {'schema': 'useful-work-economic-evidence/v2', 'capability_id': 'component-compatibility',
        'primary_arm': 'retained', 'actual_collections_minor': 0, 'starting_capital_minor': None,
        'approved_allocation_minor': None, 'customer_price_minor': None,
        'capability_description': 'One retained source-bound component-compatibility decision and evidence delivery capability; shared conventional custody validation is adopted with attribution.',
        'capability_artifacts': ['src/run_pair.py', 'src/package_component.py', 'src/conventional_package.py',
            'src/manual_probe.py', 'src/conventional_probe.py', 'src/verify_component.py', 'src/delivery.py', 'src/workbench.mjs'],
        'missions': missions, 'resource_entries': resources, 'delivery_envelopes': envelopes}
    by_arm = {arm: {'evaluations': 6, 'accepted': sum(row['accepted'] for row in observed if row['arm']==arm),
        'incomplete': sum(not row['accepted'] for row in observed if row['arm']==arm),
        'service_span_seconds': descriptive([row['request_to_package_wall_seconds'] for row in observed if row['arm']==arm]),
        'mechanical_wall_seconds': descriptive([row['mechanical_wall_seconds'] for row in observed if row['arm']==arm]),
        'measured_local_cpu_seconds': descriptive([row['measured_local_cpu_seconds'] for row in observed if row['arm']==arm])}
        for arm in ARMS}
    summary = {'schema': 'postfreeze-complete-campaign-analysis/v1', 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'collector_sha256': sha(Path(__file__)), 'freeze_check': freeze_check, 'primary_protocol': ident(root / 'protocol/primary-protocol.json', root),
        'input_construction': ident(construction_path, root), 'unique_missions': 6, 'arm_evaluations': 18,
        'campaign_receipt': ident(campaign_path, root),
        'campaign_envelope_not_added_again': {key: campaign.get(key) for key in ['wall_seconds', 'process_cpu_seconds', 'child_cpu_seconds', 'aggregation']},
        'paid_customer_missions': 0, 'by_arm': by_arm, 'runs': observed, 'shared_acquisition': setup,
        'lifecycle': lifecycle_summary, 'manual_scope': protocol['arms']['manual'],
        'freshness': protocol['sampling']['freshness'], 'quality_and_timing_limits': protocol['analysis'],
        'monetary_cost_usd': None, 'customer_price_usd': None, 'customer_savings_usd': None,
        'investment_repaid': None, 'available_to_commit_usd': None,
        'source_freeze_rechecked_after_collection': source_check(root)[1],
        'collector_wall_seconds': time.perf_counter()-start, 'collector_process_cpu_seconds': time.process_time()-cpu}
    write(out / 'summary.json', summary)
    write(out / 'economic-evidence.json', economic)
    write(out / 'lifecycle-known-subtotals.json', lifecycle_summary)
    if args.emit_canonical:
        command = ['node', str(root / 'analysis/economics.mjs'), '--input', str(out / 'economic-evidence.json'),
                   '--root', str(root), '--out', str(out / 'canonical-economics')]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        write(out / 'canonical-execution.json', {'command': command, 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr, 'money_usd': None})
        if result.returncode:
            raise RuntimeError('Canonical economics adapter refused mapping: ' + result.stderr)
    print(json.dumps({'out': str(out), 'unique_missions': 6, 'arm_evaluations': 18,
                      'accepted_by_arm': {arm: row['accepted'] for arm, row in by_arm.items()},
                      'actual_collections_minor': 0, 'complete_cost_minor': None}))


if __name__ == '__main__':
    main()
