# SPDX-License-Identifier: Apache-2.0
"""Verify one relocated B replay without changing any frozen scientific source."""
from __future__ import annotations
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

WORKSPACE = Path('/workspace/scratch/da407bff0020')
ORIGINAL = WORKSPACE / 'study/vendor/useful-work-v2'
COPY_ROOT = WORKSPACE / 'tmp/portable-production-verification'
COPY = COPY_ROOT / 'vendor/useful-work-v2'
HERE = WORKSPACE / 'study/review/production-relocation'
OUT = COPY / 'joint-study/relocated-one-b'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def verify():
    freeze_path = COPY_ROOT / 'production/joint-freeze.json'
    assert sha(freeze_path) == '2da7e8191eb2fb80adcd7d808d0494ab3247313e997607e7166e71c352ea7cee'
    freeze = read(freeze_path)
    for entry in freeze['files']:
        assert sha(COPY_ROOT / entry['path']) == entry['sha256'], entry['path']
    return {'files': len(freeze['files']), 'sha256': sha(freeze_path), 'unchanged': True}


def execute(command, name, result, timeout=180):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall, cpu = time.perf_counter(), time.process_time()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHON_EXECUTABLE=sys.executable,
                       PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    run = subprocess.run(command, cwd=COPY, env=environment, capture_output=True, timeout=timeout)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    (HERE / (name + '.stdout.txt')).write_bytes(run.stdout)
    (HERE / (name + '.stderr.txt')).write_bytes(run.stderr)
    record = {'name': name, 'command': command, 'exit_code': run.returncode, 'started_at': started,
              'ended_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'wall_seconds': time.perf_counter() - wall, 'meter_cpu_seconds': time.process_time() - cpu,
              'child_cpu_seconds': after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
              'stdout_sha256': hashlib.sha256(run.stdout).hexdigest(),
              'stderr_sha256': hashlib.sha256(run.stderr).hexdigest()}
    result['steps'].append(record)
    write(HERE / 'receipt.json', result)
    if run.returncode:
        raise ValueError('REPLAY_COMMAND_FAILED:' + name)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'game-market-relocated-production-replay/v1',
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'mission': 'joint-1', 'arm': 'retained', 'steps': [], 'complete': False,
              'new_primary_missions': 0, 'new_customer_jobs': 0,
              'complete_money_usd': None, 'active_human_minutes': None,
              'scope': 'One exact-asset reproduction at a fresh relocated root using original public wheels; no new primary outcome or operator authority.'}
    result['freeze_before'] = verify()
    result['plan_relocations'] = []
    try:
        for ident in ['baseline', 'joint-1']:
            original = ORIGINAL / 'joint-study/run-001/plans' / (ident + '.json')
            plan = read(original)
            plan['native_lock'] = str(COPY / 'discovery/requirements/requirements-agent.lock')
            plan['incoming_constraint_metadata'] = [str(COPY / 'discovery/release-metadata' / Path(p).name)
                                                   for p in plan['incoming_constraint_metadata']]
            plan['consumer_contract'] = str(COPY / 'protocol/component-contract.json')
            path = OUT / 'plans' / (ident + '.json')
            write(path, plan)
            compare = dict(plan)
            initial = read(original)
            for key in ['native_lock', 'incoming_constraint_metadata', 'consumer_contract']:
                compare[key] = initial[key]
            assert compare == initial
            result['plan_relocations'].append({'profile': ident, 'original_sha256': sha(original),
                                               'relocated_sha256': sha(path),
                                               'changes': 'Only three absolute local path fields; pins and scientific conditions unchanged.'})
            execute([sys.executable, '-B', str(COPY / 'curation/prepare_environment.py'),
                     '--plan', str(path), '--out', str(OUT / 'environments' / ident),
                     '--metadata-reuse', str(COPY / 'joint-study/inputs/metadata'),
                     '--wheel-reuse', str(COPY / 'joint-study/inputs/wheels'),
                     '--confirmation-freeze', str(COPY_ROOT / 'production/joint-freeze.json'), '--offline'],
                    'prepare-' + ident, result)
            prep = read(OUT / 'environments' / ident / 'preparation.json')
            assert prep['complete'] is True and prep['network_requests'] == 0
            assert len(prep['wheels']) == 10
        original_job = ORIGINAL / 'joint-study/run-001/jobs/joint-1.json'
        job = read(original_job)
        for side, ident in [('before', 'baseline'), ('after', 'joint-1')]:
            job[side]['environment'] = str((OUT / 'environments' / ident).relative_to(COPY))
        job_path = OUT / 'job.json'
        write(job_path, job)
        registry = OUT / 'registry.json'
        write(registry, {'schema': 'alpha-component-registry/v1', 'missions': {
            'joint-1': {'path': str(job_path.relative_to(COPY)), 'sha256': sha(job_path)}}})
        result['job_relocation'] = {'original_sha256': sha(original_job), 'relocated_sha256': sha(job_path),
                                    'changes': 'Only before/after environment paths; same mission identity, versions and consumer contract.'}
        execute(['node', str(COPY / 'src/workbench.mjs'), 'joint-1', 'retained', str(OUT / 'native'),
                 str(registry.relative_to(COPY))], 'workbench-retained-joint-1', result, timeout=70)
        delivery = read(OUT / 'native/delivery/delivery.json')
        assert delivery['accepted'] is True and delivery['decision'] == 'SCOPED_COMPONENT_PRESERVED'
        semantic = []
        for side in ['before', 'after']:
            path = OUT / 'native/delivery/pair' / (side + '-verification.json')
            checked = read(path)
            old = read(ORIGINAL / 'joint-study/run-001/results/joint-1/retained/delivery/pair' / path.name)
            assert checked['counts'] == old['counts'] == {'PASS': 61, 'BEHAVIOR_MISMATCH': 0, 'INCOMPLETE': 0}
            assert checked['status'] == old['status'] == 'PRESERVED_WITHIN_COMPONENT_CONTRACT'
            for key in ['contract_sha256', 'projection_id', 'native_import_route', 'environment_versions']:
                assert checked[key] == old[key]
            assert checked['cases'] == old['cases']
            semantic.append({'side': side, 'counts': checked['counts'], 'exact_requirement_results_equal': True,
                             'verification_sha256': sha(path), 'original_verification_sha256': sha(
                                 ORIGINAL / 'joint-study/run-001/results/joint-1/retained/delivery/pair' / path.name)})
        pack = read(OUT / 'native/pack.json')
        assert pack['evaluation']['admission'] == 'HOLD' and pack['evaluation']['authority'] == []
        assert pack['evaluation']['settlement'] == 'NOT_CONNECTED'
        result.update(complete=True, decision=delivery['decision'], semantic_results=semantic,
                      runtime_network_requests=delivery['runtime_network_requests'],
                      native_evaluation=pack['evaluation'], decision_sha256=delivery['decision_sha256'])
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    result['freeze_after'] = verify()
    result['ended_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(HERE / 'receipt.json', result)
    print(json.dumps({k: result.get(k) for k in ['complete', 'decision', 'error', 'new_primary_missions', 'runtime_network_requests']}))
    if not result['complete']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
