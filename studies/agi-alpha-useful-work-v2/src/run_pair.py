# SPDX-License-Identifier: Apache-2.0
"""Common bounded execution infrastructure for two equally permitted builders."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
RECORDS = {side: {name: f'{side}-{suffix}.json' for name, suffix in [
    ('observations', 'observations'), ('execution', 'execution'),
    ('verification', 'verification'), ('verification_execution', 'verification-execution')]}
    for side in ('before', 'after')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('RELATIVE_REGISTERED_PATH_REQUIRED')
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('INPUT_PATH_OUTSIDE_STUDY')
    return resolved


def validate_job(job):
    if job.get('schema') != 'alpha-component-job/v1' or job.get('phase') not in ('development', 'confirmation'):
        raise ValueError('JOB_SCHEMA')
    mission = job.get('mission_id', '')
    if not mission or len(mission) > 80 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in mission):
        raise ValueError('MISSION_ID')
    contract = local_path(job['contract']['path'])
    if digest(contract) != job['contract']['sha256']:
        raise ValueError('CONTRACT_IDENTITY')
    consumer = local_path(job['consumer']['directory'])
    for name in ('api', 'models'):
        if digest(consumer / (name + '.py')) != job['consumer'][name + '_sha256']:
            raise ValueError('CONSUMER_SOURCE_IDENTITY')
    for side in ('before', 'after'):
        environment = local_path(job[side]['environment'])
        preparation = json.loads((environment / 'preparation.json').read_text())
        if preparation.get('schema') != 'component-environment-preparation/v1' or preparation.get('complete') is not True:
            raise ValueError('ENVIRONMENT_PREPARATION_INCOMPLETE')
        versions = {entry['name']: entry['version'] for entry in preparation['wheels']}
        if versions != job[side]['expected_versions']:
            raise ValueError('ENVIRONMENT_VERSIONS')
        expected_lock = ''.join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in preparation['wheels'])
        if (environment / 'requirements.lock').read_text() != expected_lock:
            raise ValueError('ENVIRONMENT_LOCK_IDENTITY')
        for wheel in preparation['wheels']:
            path = environment / 'wheels' / wheel['filename']
            if Path(wheel['filename']).name != wheel['filename'] or digest(path) != wheel['sha256']:
                raise ValueError('ENVIRONMENT_WHEEL_IDENTITY')
    return contract, consumer


def measured_command(phase, record, binds, outputs, command):
    argv = [sys.executable, str(ROOT / 'src/measured_run.py'), '--phase', phase,
            '--record', str(record), '--timeout', '45']
    for path in binds:
        argv.extend(['--bind', str(path)])
    for path in outputs:
        argv.extend(['--output', str(path)])
    return argv + ['--'] + command


def run_pair(job_path, out, arm):
    if arm not in ('retained', 'conventional'):
        raise ValueError('SUPPORTED_BUILDER_REQUIRED')
    out.mkdir(parents=True, exist_ok=False)
    wall, cpu = time.perf_counter(), time.process_time()
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    job_raw = job_path.read_bytes()
    (out / 'job.json').write_bytes(job_raw)
    job = json.loads(job_raw)
    worker = ROOT / 'src' / ('manual_probe.py' if arm == 'retained' else 'conventional_probe.py')
    result = {'schema': 'alpha-component-pair/v1', 'job_sha256': hashlib.sha256(job_raw).hexdigest(),
              'worker_path': str(worker.relative_to(ROOT)), 'worker_sha256': digest(worker),
              'arm': arm, 'records': RECORDS, 'started_at': started, 'custody_complete': False,
              'process_results': [], 'money_usd': None, 'runtime_model_calls': 0}
    try:
        contract, consumer = validate_job(job)
        processes = []
        for side in ('before', 'after'):
            environment = local_path(job[side]['environment'])
            output = out / RECORDS[side]['observations']
            executable = environment / 'venv/bin/python'
            binds = [job_path, worker, ROOT / 'src/measured_run.py', contract,
                     ROOT / 'protocol/component-projections.json', consumer / 'api.py', consumer / 'models.py',
                     environment / 'requirements.lock', environment / 'preparation.json', executable]
            command = [str(executable), '-I', '-B', str(worker), '--consumer', str(consumer),
                       '--contract', str(contract), '--out', str(output)]
            if arm == 'conventional':
                command += ['--lock', str(environment / 'requirements.lock')]
            argv = measured_command(side + '-consumer-execution', out / RECORDS[side]['execution'],
                                    binds, [output], command)
            processes.append((side, subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
        for side, process in processes:
            stdout, stderr = process.communicate()
            result['process_results'].append({'side': side, 'phase': 'observations', 'exit_code': process.returncode,
                                              'stdout': stdout, 'stderr': stderr})
        for side in ('before', 'after'):
            observation = out / RECORDS[side]['observations']
            if not observation.is_file():
                continue
            environment = local_path(job[side]['environment'])
            verifier = ROOT / 'src/verify_component.py'
            output = out / RECORDS[side]['verification']
            binds = [job_path, verifier, contract, ROOT / 'protocol/component-projections.json', observation,
                     consumer / 'api.py', consumer / 'models.py', ROOT / 'discovery/test_api_boundary.py',
                     environment / 'preparation.json']
            command = [sys.executable, str(verifier), '--contract', str(contract), '--consumer', str(consumer),
                       '--environment', str(environment / 'preparation.json'), '--projection',
                       'native-fastapi-bridge-v2', '--observations', str(observation), '--out', str(output)]
            argv = measured_command(side + '-independent-verification', out / RECORDS[side]['verification_execution'],
                                    binds, [output], command)
            completed = subprocess.run(argv, capture_output=True, text=True, check=False)
            result['process_results'].append({'side': side, 'phase': 'verification', 'exit_code': completed.returncode,
                                              'stdout': completed.stdout, 'stderr': completed.stderr})
        records = []
        for side in ('before', 'after'):
            for field in ('execution', 'verification_execution'):
                path = out / RECORDS[side][field]
                records.append((field, json.loads(path.read_text()) if path.is_file() else {}))
        result['custody_complete'] = all(row.get('inputs_unchanged') is True and not row.get('missing_outputs', ['missing'])
                                         and row.get('command_started') is True and row.get('timed_out') is False
                                         and type(row.get('exit_code')) is int
                                         and row.get('exit_code') in ({0, 1} if field == 'execution' else {0, 2})
                                         and not row.get('launcher_error') for field, row in records)
        result['artifacts'] = [{'path': str(p.relative_to(out)), 'sha256': digest(p), 'bytes': p.stat().st_size}
                               for p in sorted(out.rglob('*')) if p.is_file()]
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result['wall_seconds'] = time.perf_counter() - wall
        result['process_cpu_seconds'] = time.process_time() - cpu
        result['child_cpu_seconds'] = after.ru_utime + after.ru_stime - children.ru_utime - children.ru_stime
        result['child_peak_rss_kib'] = after.ru_maxrss
        result['ended_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / 'pair.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--arm', choices=['retained', 'conventional'], required=True)
    args = parser.parse_args()
    result = run_pair(args.job.resolve(), args.out.resolve(), args.arm)
    print(json.dumps({'custody_complete': result['custody_complete'], 'error': result.get('error'),
                      'wall_seconds': result['wall_seconds']}))
    if not result['custody_complete']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
