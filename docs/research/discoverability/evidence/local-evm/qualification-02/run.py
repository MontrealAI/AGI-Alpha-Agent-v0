#!/usr/bin/env python3
"""One fresh qualification of the unchanged, retained Alpha test selection.

This wrapper retains custody; it does not alter source, assertions, compiler
settings, dependencies or authority. The later snapshot is a separate fixture.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
SOURCE = Path('/tmp/discoverability-evm')
CWD = SOURCE / 'tests/contracts'
PYTHON = SOURCE / '.venv/bin/python'
RECEIPTS = HERE / 'receipts'


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


def source_inventory():
    expected = json.loads((HERE.parent / 'source-inventory.json').read_text())
    observations = []
    for item in expected['files']:
        if item['path'] == 'LICENSE':
            continue  # Archive license supplied by repository; not executable.
        p = SOURCE / item['path']
        data = p.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != item['sha256']:
            raise RuntimeError('Retained source changed: ' + item['path'])
        observations.append({'path': item['path'], 'bytes': len(data), 'sha256': actual})
    return observations


def execute(label, argv, env):
    started_at = now()
    start = time.monotonic()
    record = {
        'command': argv, 'cwd': str(CWD), 'startedAtUtc': started_at,
        'environmentOverrides': {k: env[k] for k in ['ALPHA_PYTHON', 'SUCCESSOR_EVM_EVIDENCE_DIR']},
        'timeoutSeconds': 180,
    }
    write(label + '-execution.json', record)
    with (HERE / (label + '-stdout.log')).open('wb') as stdout, (HERE / (label + '-stderr.log')).open('wb') as stderr:
        try:
            completed = subprocess.run(argv, cwd=CWD, env=env, stdout=stdout, stderr=stderr, timeout=180)
            record['exitCode'] = completed.returncode
            record['timedOut'] = False
        except subprocess.TimeoutExpired:
            record['exitCode'] = None
            record['timedOut'] = True
    record['endedAtUtc'] = now()
    record['elapsedSeconds'] = time.monotonic() - start
    for stream in ['stdout', 'stderr']:
        p = HERE / (label + '-' + stream + '.log')
        data = p.read_bytes()
        record[stream] = {'path': p.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    write(label + '-execution.json', record)
    print(json.dumps({'label': label, 'exitCode': record['exitCode'], 'elapsedSeconds': record['elapsedSeconds']}), flush=True)
    return record


def main():
    if (HERE / 'tests-execution.json').exists():
        raise RuntimeError('Qualification output already exists; refusing to overwrite evidence or rerun.')
    RECEIPTS.mkdir(exist_ok=True)
    before = source_inventory()
    write('source-before.json', {'observedAtUtc': now(), 'files': before})
    py = subprocess.run([str(PYTHON), '-c', 'import sys,json,importlib.metadata as m;print(json.dumps({"python":sys.version,"distributions":sorted([{"name":d.metadata["Name"],"version":d.version} for d in m.distributions()],key=lambda x:x["name"].lower())}))'], capture_output=True, text=True, check=True)
    node = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True)
    npm = subprocess.run(['npm', '--version'], capture_output=True, text=True, check=True)
    packages = {}
    for name in ['hardhat', 'ethers', 'solc', '@openzeppelin/contracts']:
        packages[name] = json.loads((CWD / 'node_modules' / name / 'package.json').read_text())['version']
    write('installed-environment.json', {'observedAtUtc': now(), 'pythonEnvironment': json.loads(py.stdout), 'node': node.stdout.strip(), 'npm': npm.stdout.strip(), 'selectedNodePackages': packages, 'dependencyInstallationPerformed': False})
    env = dict(os.environ)
    env.update(ALPHA_PYTHON=str(PYTHON), SUCCESSOR_EVM_EVIDENCE_DIR=str(RECEIPTS))
    command = ['npm', 'test', '--', 'test/ascension/lifecycle.test.js', 'test/ascension/marketplace.test.js', 'test/ascension/settlement.test.js', 'test/ascension/successor-adapter.test.js']
    test = execute('tests', command, env)
    after = source_inventory()
    write('source-after.json', {'observedAtUtc': now(), 'files': after, 'unchanged': before == after})
    if test['exitCode'] == 0:
        execute('separate-fixture', ['node', str(HERE / 'snapshot.cjs')], env)


if __name__ == '__main__':
    main()
