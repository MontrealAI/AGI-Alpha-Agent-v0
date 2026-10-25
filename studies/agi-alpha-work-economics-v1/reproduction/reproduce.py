#!/usr/bin/env python3
"""Reproduce the frozen workflow in a NEW, isolated destination; never in place."""
import argparse
import datetime
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
sys.dont_write_bytecode = True
from common import DEFAULT_ROOT, EXPECTED_FREEZE, copy_files, new_destination, verify_freeze, write_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_ROOT, help='Original complete companion, read only.')
    parser.add_argument('--destination', type=Path, required=True, help='New sibling or external directory; its parent must exist.')
    parser.add_argument('--prepare-only', action='store_true', help='Copy/verify frozen inputs and write the execution plan; run no jobs.')
    args = parser.parse_args()
    source = args.source.resolve()
    freeze = verify_freeze(source)
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js must already be installed; this script installs nothing.')
    versions = {'python': platform.python_version(), 'node': subprocess.check_output([node, '--version'], text=True).strip()}
    for package in ['pydantic', 'cryptography']:
        versions[package] = importlib.metadata.version(package)
    if not versions['pydantic'].startswith('2.'):
        raise RuntimeError('The released Python adapter requires Pydantic 2 APIs.')
    destination = new_destination(source, args.destination)
    names = [row['path'] for row in freeze['files']] + ['protocol/FREEZE.json', 'protocol/FREEZE.sha256']
    names += [str(path.relative_to(source)) for path in (source / 'reproduction').glob('*.py')]
    names.append('reproduction/REFERENCE_ENVIRONMENT.json')
    copied = copy_files(source, destination, names)
    verify_freeze(destination)
    (destination / 'README.md').write_text('# Isolated AGI ALPHA workflow replication\n\n'
        'This new tree contains the original frozen implementation and inputs. '
        'It does not contain copied observations or publication artifacts. '
        'REPRODUCTION.json records the exact source companion, command plan, new environment, '
        'and stage outcomes. Consult the source companion README for interpretation and build instructions.\n\n'
        'The fixed-seed generator reproduces the original inputs; this is not a new independent held-out sample. '
        'Complete actual cost and human attention remain unmetered.\n')
    raw = destination / 'raw'
    raw.mkdir()
    (destination / 'reproduction-logs').mkdir()
    environment = {'date_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'os': platform.platform(), 'machine': platform.machine(), 'logical_cpu_count': os.cpu_count(),
                   **versions, 'scope': 'New replication environment; host price and actual human attention unmetered.',
                   'task_model': 'none; original deterministic released adapters',
                   'development_assistant': None}
    write_json(raw / 'ENVIRONMENT.json', environment)
    py = sys.executable
    plan = [
        ('public_inputs', [py, 'src/prepare_public_task.py']),
        ('controlled_inputs', [py, 'src/generate_tasks.py', '--phase', 'confirmation', '--out', 'raw/tasks']),
        ('first_useful_job', [py, 'src/run_job.py', '--task', 'raw/public-task', '--out', 'raw/showcase']),
        ('primary_sequence', [py, 'src/run_campaign.py', '--mode', 'primary', '--tasks', 'raw/tasks', '--out', 'raw/primary', '--parent', 'raw/showcase/output/successor-tool.mjs']),
        ('composed_successor', [py, 'src/successor_report.py']),
        ('finite_controls', [node, 'src/controls.mjs', '--out', 'raw/controls']),
        ('finite_scale', [py, 'src/run_campaign.py', '--mode', 'scale', '--tasks', 'raw/tasks', '--out', 'raw/scale', '--parent', 'raw/showcase/output/successor-tool.mjs']),
        ('analysis', [py, 'src/analyse.py']),
    ]
    receipt = {'schema': 'agialpha-isolated-reproduction/v1', 'status': 'PREPARED',
               'created_utc': environment['date_utc'], 'source_freeze_sha256': EXPECTED_FREEZE,
               'source_companion': str(source), 'new_destination': str(destination),
               'input_interpretation': 'Exact fixed-seed regeneration of the original 36 controlled instances and frozen public inventories; not a new independent held-out sample.',
               'identity_policy': 'Original sources and protocol copied byte-for-byte. Original evidence is never overwritten.',
               'copied_files': copied, 'versions': versions,
               'commands': [{'step': name, 'argv': argv} for name, argv in plan], 'steps': []}
    write_json(destination / 'REPRODUCTION.json', receipt)
    if args.prepare_only:
        print('PREPARED_ONLY: no tasks generated, no job/control/scale executions. ' + str(destination))
        return 0
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'TMPDIR', 'SYSTEMROOT', 'WINDIR'}}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    receipt['status'] = 'RUNNING'
    write_json(destination / 'REPRODUCTION.json', receipt)
    for name, argv in plan:
        start = time.perf_counter()
        log = destination / 'reproduction-logs'
        error = None
        with (log / (name + '.stdout.txt')).open('w') as stdout, (log / (name + '.stderr.txt')).open('w') as stderr:
            try:
                result = subprocess.run(argv, cwd=destination, env=env, stdout=stdout, stderr=stderr, timeout=900)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code, error = 124, 'Replication stage exceeded the wrapper 900-second limit.'
            except Exception as exc:
                code, error = 1, type(exc).__name__ + ': ' + str(exc)
        receipt['steps'].append({'step': name, 'exit_code': code, 'elapsed_seconds': time.perf_counter() - start, 'error': error})
        if code:
            receipt['status'] = 'STOPPED_WITH_PRESERVED_FAILURE'
            write_json(destination / 'REPRODUCTION.json', receipt)
            print('FAILED step ' + name + '; all evidence retained in ' + str(destination), file=sys.stderr)
            return code
        write_json(destination / 'REPRODUCTION.json', receipt)
    verify_freeze(source)
    verify_freeze(destination)
    receipt['status'] = 'COMPLETED'
    receipt['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt['new_empirical_human_trial'] = 'NOT_RUN'
    receipt['complete_actual_cost'] = None
    write_json(destination / 'REPRODUCTION.json', receipt)
    print('COMPLETED isolated replication: ' + str(destination))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
