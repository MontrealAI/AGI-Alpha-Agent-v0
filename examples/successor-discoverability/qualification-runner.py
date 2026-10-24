#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Retain local-EVM qualification evidence and propagate subprocess failure.

This reusable runner supersedes evidence/local-evm/qualification-02/run.py for
future runs. The executed historical wrapper and its receipts remain immutable.
It requires already installed dependencies; it does not install or fund anything.
The separate fixture remains a different disposable instance from the test run.

Example (use a NEW output directory):
  python qualification-runner.py --source /tmp/discoverability-evm \
      --output /tmp/discoverability-qualification-new
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/research/discoverability/evidence/local-evm'
TEST_COMMAND = [
    'npm', 'test', '--',
    'test/ascension/lifecycle.test.js',
    'test/ascension/marketplace.test.js',
    'test/ascension/settlement.test.js',
    'test/ascension/successor-adapter.test.js',
]


def now() -> str:
    """Return an ISO UTC observation timestamp."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def identity(path: Path) -> dict[str, int | str]:
    """Hash exact file bytes without interpreting their contents."""
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def write(output: Path, name: str, value: Any) -> None:
    """Write a retained JSON record within the newly claimed output."""
    (output / name).write_text(json.dumps(value, indent=2) + '\n')


def claim_output(output: Path, kind: str = 'local-evm-qualification') -> None:
    """Claim an empty directory, refusing to overwrite existing evidence."""
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError('Refusing nonempty qualification output: ' + str(output))
    with (output / 'qualification-start.json').open('x') as handle:
        json.dump({'startedAtUtc': now(), 'kind': kind}, handle, indent=2)
        handle.write('\n')


def source_inventory(source: Path, inventory: Path) -> list[dict[str, Any]]:
    """Verify executable inputs against the preserved historical inventory."""
    observations = []
    for item in json.loads(inventory.read_text())['files']:
        if item['path'] == 'LICENSE':
            continue  # Archive license is not an executable input; historical rule.
        path = source / item['path']
        actual = identity(path)
        if actual['sha256'] != item['sha256']:
            raise RuntimeError('Retained source changed: ' + item['path'])
        observations.append({'path': item['path'], **actual})
    return observations


def execute(
    output: Path, label: str, argv: list[str], cwd: Path, env: dict[str, str], timeout_seconds: float,
) -> dict[str, Any]:
    """Retain subprocess streams and status, terminating its process group on timeout."""
    start = time.monotonic()
    record = {
        'command': argv, 'cwd': str(cwd), 'startedAtUtc': now(),
        'environmentOverrides': {
            key: env[key] for key in ['ALPHA_PYTHON', 'SUCCESSOR_EVM_EVIDENCE_DIR']
            if key in env
        },
        'timeoutSeconds': timeout_seconds, 'exitCode': None, 'timedOut': False,
    }
    write(output, label + '-execution.json', record)
    with (
        (output / (label + '-stdout.log')).open('wb') as stdout,
        (output / (label + '-stderr.log')).open('wb') as stderr,
    ):
        try:
            process = subprocess.Popen(
                argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                start_new_session=os.name == 'posix',
            )
            try:
                record['exitCode'] = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                record['terminationExitCode'] = process.wait()
        except OSError as error:
            record['exitCode'] = 127
            record['launchError'] = str(error)
    record['endedAtUtc'] = now()
    record['elapsedSeconds'] = time.monotonic() - start
    for stream in ['stdout', 'stderr']:
        path = output / (label + '-' + stream + '.log')
        record[stream] = {'path': path.name, **identity(path)}
    write(output, label + '-execution.json', record)
    return record


def exit_status(record: dict[str, Any]) -> int:
    """Map retained outcomes to shell status, using 124 for a timeout."""
    if record['timedOut']:
        return 124
    code = record['exitCode']
    if code is None:
        return 1
    return min(code, 255) if code >= 0 else min(128 - code, 255)


def run_commands(
    output: Path, cwd: Path, env: dict[str, str], tests: list[str], fixture: list[str],
    timeout_seconds: float, after_tests: Callable[[], None] | None = None,
) -> int:
    """Run the two stages; explicit command arguments also permit isolated tests.

    The public CLI always supplies TEST_COMMAND and the retained local fixture.
    Regression fixtures calling this function are not local-EVM qualification.
    """
    test = execute(output, 'tests', tests, cwd, env, timeout_seconds)
    status = exit_status(test)
    integrity_error = None
    if after_tests is not None:
        try:
            after_tests()
        except (OSError, ValueError, RuntimeError) as error:
            integrity_error = str(error)
            if status == 0:
                status = 2
    fixture_record = None
    if status == 0:
        fixture_record = execute(output, 'separate-fixture', fixture, cwd, env, timeout_seconds)
        status = exit_status(fixture_record)
    summary = {
        'endedAtUtc': now(), 'wrapperExitCode': status,
        'testExitCode': test['exitCode'], 'testTimedOut': test['timedOut'],
        'fixtureExecuted': fixture_record is not None,
        'fixtureExitCode': fixture_record['exitCode'] if fixture_record else None,
        'fixtureTimedOut': fixture_record['timedOut'] if fixture_record else None,
        'sourceIntegrityError': integrity_error,
        'scope': 'Subprocess custody only; consult commands and qualification-start.json for execution kind.',
    }
    write(output, 'qualification-summary.json', summary)
    return status


def main(argv: list[str] | None = None) -> int:
    """Qualify installed, unchanged local source into a fresh evidence directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--source', type=Path, required=True, help='Exact retained source closure with installed dependencies',
    )
    parser.add_argument(
        '--output', type=Path, required=True, help='New or empty output directory; nonempty output is refused',
    )
    parser.add_argument('--python', type=Path, help='Reviewed Python executable; default: SOURCE/.venv/bin/python')
    parser.add_argument('--timeout-seconds', type=float, default=180, help='Per-stage timeout; expiry exits 124')
    args = parser.parse_args(argv)
    if not 0 < args.timeout_seconds <= 180:
        parser.error('--timeout-seconds must be greater than 0 and no more than 180')
    source, output = args.source.resolve(), args.output.resolve()
    try:
        claim_output(output)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        inventory = EVIDENCE / 'source-inventory.json'
        before = source_inventory(source, inventory)
        write(output, 'source-before.json', {'observedAtUtc': now(), 'files': before})
        snapshot_source = EVIDENCE / 'qualification-02/snapshot.cjs'
        snapshot = output / 'snapshot.cjs'
        shutil.copyfile(snapshot_source, snapshot)
        python = (args.python or source / '.venv/bin/python').resolve()
        cwd = source / 'tests/contracts'
        env = dict(os.environ)
        receipts = output / 'receipts'
        receipts.mkdir()
        env.update(ALPHA_PYTHON=str(python), SUCCESSOR_EVM_EVIDENCE_DIR=str(receipts))
        write(output, 'runner-provenance.json', {
            'observedAtUtc': now(), 'runner': identity(Path(__file__)),
            'sourceDirectory': str(source), 'inventory': identity(inventory),
            'snapshot': identity(snapshot), 'copiedSnapshotUnchanged': identity(snapshot) == identity(snapshot_source),
            'supersedesForFutureUse': 'docs/research/discoverability/evidence/local-evm/qualification-02/run.py',
            'historicalWrapper': identity(EVIDENCE / 'qualification-02/run.py'),
            'dependencyInstallationPerformed': False, 'externalFundsUsed': False,
            'qualification': 'Local EVM with simulated balances; separate fixture is not the test instance.',
        })

        probe_commands = {
            'python': [str(python), '-c', (
                'import sys,json,importlib.metadata as m;'
                'print(json.dumps({"python":sys.version,"distributions":sorted('
                '[{"name":d.metadata["Name"],"version":d.version} for d in m.distributions()],'
                'key=lambda x:x["name"].lower())}))'
            )],
            'node': ['node', '--version'],
            'npm': ['npm', '--version'],
        }
        versions = {}
        for name, command in probe_commands.items():
            label = 'environment-' + name
            probe = execute(output, label, command, cwd, env, args.timeout_seconds)
            status = exit_status(probe)
            if status:
                write(output, 'qualification-summary.json', {
                    'endedAtUtc': now(), 'wrapperExitCode': status,
                    'failedStage': label, 'testsExecuted': False, 'fixtureExecuted': False,
                })
                return status
            versions[name] = (output / (label + '-stdout.log')).read_text().strip()
        packages = {}
        for name in ['hardhat', 'ethers', 'solc', '@openzeppelin/contracts']:
            packages[name] = json.loads((cwd / 'node_modules' / name / 'package.json').read_text())['version']
        write(output, 'installed-environment.json', {
            'observedAtUtc': now(), 'pythonEnvironment': json.loads(versions['python']),
            'node': versions['node'], 'npm': versions['npm'], 'selectedNodePackages': packages,
            'dependencyInstallationPerformed': False,
        })

        def after_tests() -> None:
            """Retain the source check even after an unsuccessful test subprocess."""
            after = source_inventory(source, inventory)
            write(output, 'source-after.json', {'observedAtUtc': now(), 'files': after, 'unchanged': before == after})
            if before != after:
                raise RuntimeError('Source inventory changed during qualification')

        return run_commands(output, cwd, env, TEST_COMMAND, ['node', str(snapshot)], args.timeout_seconds, after_tests)
    except (OSError, ValueError, RuntimeError) as error:
        write(output, 'setup-error.json', {'observedAtUtc': now(), 'error': str(error), 'wrapperExitCode': 2})
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
