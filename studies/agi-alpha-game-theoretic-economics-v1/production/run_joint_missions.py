# SPDX-License-Identifier: Apache-2.0
"""Run frozen grouped-change assessments through the unchanged local research adapters."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'production'
SOURCE = ROOT / 'vendor/useful-work-v2'
OUTPUT = SOURCE / 'joint-study/run-001'
FREEZE = HERE / 'joint-freeze.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def verify_freeze():
    freeze = read(FREEZE)
    for entry in freeze['files']:
        if sha(ROOT / entry['path']) != entry['sha256']:
            raise ValueError('FROZEN_SOURCE_OR_INPUT_CHANGED:' + entry['path'])
    return {'sha256': sha(FREEZE), 'files': len(freeze['files']), 'unchanged': True, 'at': now()}


def execute(argv, record, timeout=70):
    record.parent.mkdir(parents=True, exist_ok=True)
    if record.exists():
        raise ValueError('RECEIPT_ALREADY_EXISTS')
    started, wall, cpu = now(), time.perf_counter(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHON_EXECUTABLE=sys.executable,
               PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    error, code = None, None
    try:
        run = subprocess.run(argv, cwd=SOURCE, env=env, capture_output=True, timeout=timeout)
        stdout, stderr, code = run.stdout, run.stderr, run.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b'', exc.stderr or b''
        error = 'OUTER_TIMEOUT'
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record.with_suffix('.stdout.txt').write_bytes(stdout)
    record.with_suffix('.stderr.txt').write_bytes(stderr)
    result = {'schema': 'game-market-local-command/v1', 'started_at': started, 'ended_at': now(),
              'command': argv, 'exit_code': code, 'error': error,
              'wall_seconds': time.perf_counter() - wall,
              'meter_cpu_seconds': time.process_time() - cpu,
              'child_cpu_seconds': after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
              'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
              'stderr_sha256': hashlib.sha256(stderr).hexdigest(),
              'complete_money_usd': None, 'active_human_minutes': None,
              'aggregation': 'Inclusive command resources; nested receipts are not additional charges.'}
    write(record, result)
    return result


def prepare():
    identity = verify_freeze()
    if OUTPUT.exists():
        raise ValueError('PRIMARY_OUTPUT_ALREADY_EXISTS')
    OUTPUT.mkdir(parents=True)
    selection = read(HERE / 'joint-selection.json')
    baseline = selection['baseline']
    wheels = {(x['name'], x['version']): x for x in read(SOURCE / 'joint-study/inputs/wheels.json')}
    profiles = [{'mission_id': 'baseline', 'versions': baseline}] + selection['targets']
    setup = {'schema': 'game-market-joint-setup/v1', 'started_at': now(), 'freeze': identity,
             'environments': [], 'complete': True, 'network_requests': 0}
    for profile in profiles:
        ident, pins = profile['mission_id'], profile['versions']
        selected = wheels['starlette', pins['starlette']]
        plan = {'schema': 'component-environment-plan/v1', 'environment_id': ident,
                'phase': 'confirmation', 'pins': pins,
                'unchanged_native_packages': [k for k, v in pins.items() if baseline[k] == v],
                'native_lock': str(SOURCE / 'discovery/requirements/requirements-agent.lock'),
                'native_lock_sha256': sha(SOURCE / 'discovery/requirements/requirements-agent.lock'),
                'incoming_constraint_metadata': [str(SOURCE / 'discovery/release-metadata' / p) for p in
                                                 ['fastapi-0.141.1.json', 'pydantic-settings-2.15.0.json']],
                'consumer_contract': str(SOURCE / 'protocol/component-contract.json'),
                'scope': 'Unseen joint tuple of previously exposed package bodies; no order or app activation.',
                'declared_component_constraints': {'pydantic': '>=2.11,<3', 'fastapi': '>=0.116,<1'},
                'confirmation_freeze_sha256': sha(FREEZE), 'selection_sha256': sha(HERE / 'joint-selection.json'),
                'selected_primary_package': 'starlette',
                'selected_primary_wheel': {'filename': selected['filename'], 'sha256': selected['sha256']}}
        plan_path = OUTPUT / 'plans' / (ident + '.json')
        write(plan_path, plan)
        environment = OUTPUT / 'environments' / ident
        receipt = execute([sys.executable, '-B', str(SOURCE / 'curation/prepare_environment.py'),
                           '--plan', str(plan_path), '--out', str(environment),
                           '--metadata-reuse', str(SOURCE / 'joint-study/inputs/metadata'),
                           '--wheel-reuse', str(SOURCE / 'joint-study/inputs/wheels'),
                           '--confirmation-freeze', str(FREEZE), '--offline'],
                          OUTPUT / 'setup-receipts' / (ident + '.json'), timeout=180)
        state = read(environment / 'preparation.json') if (environment / 'preparation.json').exists() else {}
        complete = state.get('complete') is True and state.get('network_requests') == 0
        setup['environments'].append({'id': ident, 'complete': complete, 'receipt': receipt,
                                     'preparation_sha256': sha(environment / 'preparation.json') if state else None})
        if not complete:
            setup['complete'] = False
        write(OUTPUT / 'setup.json', setup)
    setup['ended_at'] = now()
    setup['freeze_after'] = verify_freeze()
    write(OUTPUT / 'setup.json', setup)
    registry = {'schema': 'alpha-component-registry/v1', 'missions': {}}
    for profile in selection['targets']:
        ident = profile['mission_id']
        job = {'schema': 'alpha-component-job/v1', 'mission_id': ident, 'phase': 'confirmation',
               'trigger': 'Research-proposed grouped dependency refresh of the exact native consumer; not a commissioned order.',
               'sampling_role': selection['freshness'], 'contract': selection['contract'],
               'consumer': selection['source_consumer'],
               'before': {'environment': str((OUTPUT / 'environments/baseline').relative_to(SOURCE)),
                          'expected_versions': baseline},
               'after': {'environment': str((OUTPUT / 'environments' / ident).relative_to(SOURCE)),
                         'expected_versions': profile['versions']},
               'joint_freeze_sha256': sha(FREEZE)}
        path = OUTPUT / 'jobs' / (ident + '.json')
        write(path, job)
        registry['missions'][ident] = {'path': str(path.relative_to(SOURCE)), 'sha256': sha(path)}
    write(OUTPUT / 'registry.json', registry)
    write(OUTPUT / 'campaign.json', {'schema': 'game-market-joint-campaign/v1', 'started_at': now(),
                                    'freeze': identity, 'results': [], 'pending': None,
                                    'complete_cost_usd': None, 'actual_collections_usd': 0})
    print(json.dumps({'setup_complete': setup['complete'], 'environments': len(profiles)}))


def check_package(package):
    manifest = read(package / 'artifact-manifest.json')
    for entry in manifest['files']:
        path = package / entry['path']
        if sha(path) != entry['sha256'] or path.stat().st_size != entry['bytes']:
            raise ValueError('PACKAGE_INTEGRITY')
    decision = read(package / 'decision.json')
    return decision['decision'], sha(package / 'decision.json')


def advance():
    verify_freeze()
    state = read(OUTPUT / 'campaign.json')
    if state['pending']:
        raise ValueError('EXPLICIT_RESEARCHER_DISPOSITION_REQUIRED')
    sequence = read(HERE / 'joint-protocol.json')['sequence']
    while len(state['results']) < len(sequence):
        item = sequence[len(state['results'])]
        ident, arm = item['mission'], item['arm']
        job = OUTPUT / 'jobs' / (ident + '.json')
        out = OUTPUT / 'results' / ident / arm
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            raise ValueError('PRIMARY_ARM_ALREADY_EXISTS')
        started = now()
        if arm == 'manual':
            out.mkdir()
            argv = [sys.executable, '-B', str(SOURCE / 'src/run_pair.py'), '--job', str(job),
                    '--out', str(out / 'pair'), '--arm', 'retained']
        else:
            argv = ['node', str(SOURCE / 'src/workbench.mjs'), ident, arm, str(out),
                    str((OUTPUT / 'registry.json').relative_to(SOURCE))]
        receipt = execute(argv, OUTPUT / 'command-receipts' / (ident + '-' + arm + '.json'))
        if arm == 'manual' and receipt['exit_code'] == 0:
            state['pending'] = {'mission': ident, 'arm': arm, 'started_at': started,
                                'pair_receipt': receipt, 'out': str(out.relative_to(SOURCE))}
            write(OUTPUT / 'campaign.json', state)
            print(json.dumps({'pending': ident, 'review': str(out / 'pair'), 'new_customer_jobs': 0}))
            return
        packet = out / 'delivery/package'
        decision, digest = check_package(packet) if packet.exists() else ('INCOMPLETE_HOLD', None)
        row = {'mission': ident, 'arm': arm, 'started_at': started, 'ended_at': now(),
               'decision': decision, 'accepted': decision in ('SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION'),
               'receipt': receipt, 'decision_sha256': digest, 'explicit_finalizations': 0}
        if (out / 'pack.json').exists():
            pack = read(out / 'pack.json')
            row['native_admission'] = pack['evaluation']['admission']
            row['native_authority'] = pack['evaluation']['authority']
        state['results'].append(row)
        state['freeze_after'] = verify_freeze()
        write(OUTPUT / 'campaign.json', state)
    state['ended_at'] = now()
    state['unique_missions'] = len({x['mission'] for x in sequence})
    state['arm_evaluations'] = len(sequence)
    state['complete'] = True
    write(OUTPUT / 'campaign.json', state)
    print(json.dumps({'complete': True, 'accepted': sum(x['accepted'] for x in state['results']),
                      'missions': state['unique_missions'], 'arm_evaluations': len(sequence)}))


def finalize(disposition):
    verify_freeze()
    state = read(OUTPUT / 'campaign.json')
    pending = state['pending']
    if not pending:
        raise ValueError('NO_PENDING_RESEARCHER_DECISION')
    ident = pending['mission']
    out = SOURCE / pending['out']
    receipt = execute([sys.executable, '-B', str(SOURCE / 'curation/assemble_manual_mission.py'),
                       '--job', str(OUTPUT / 'jobs' / (ident + '.json')), '--pair-root', str(out / 'pair'),
                       '--out', str(out / 'package'), '--decision', disposition],
                      OUTPUT / 'command-receipts' / (ident + '-manual-finalization.json'))
    decision, digest = check_package(out / 'package') if (out / 'package').exists() else ('INCOMPLETE_HOLD', None)
    state['results'].append({'mission': ident, 'arm': 'manual', 'started_at': pending['started_at'],
                             'ended_at': now(), 'decision': decision,
                             'accepted': decision in ('SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION'),
                             'pair_receipt': pending['pair_receipt'], 'finalization_receipt': receipt,
                             'decision_sha256': digest, 'explicit_finalizations': 1,
                             'finalizer': 'Same-session AI research agent after reading actual verifier evidence; not measured human labor.'})
    state['pending'] = None
    state['freeze_after'] = verify_freeze()
    write(OUTPUT / 'campaign.json', state)
    print(json.dumps({'mission': ident, 'decision': decision, 'accepted': state['results'][-1]['accepted']}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'advance', 'finalize', 'verify'])
    parser.add_argument('--decision', choices=['SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION', 'INCOMPLETE_HOLD'])
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'advance':
        advance()
    elif args.action == 'finalize':
        finalize(args.decision)
    else:
        print(json.dumps(verify_freeze()))


if __name__ == '__main__':
    main()
