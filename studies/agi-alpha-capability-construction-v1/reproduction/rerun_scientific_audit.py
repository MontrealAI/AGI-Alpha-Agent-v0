# SPDX-License-Identifier: Apache-2.0
"""Additive verification route for the exact preserved capability-study archive.

The original audit source and its non-overwrite guard are executed unchanged in a
fresh temporary working copy. The archived receipt is retained separately; no
mission, provider call, scientific refreeze or original-archive write occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ARCHIVE_SHA256 = '0fa00aadc1df63f55e5c5985bc90b4c3851862f8b6567d65b66bbc2368e92015'
PINNED = {
    'protocol/FREEZE.json': '55fe389e077028c1439cf3dbdadc09164455df00865db471ddf03bd1eb99e282',
    'analysis/independent_summary_audit.py': '14b8896d266b4708c2b0dcc43bb2948e0b66d4aa5444ab9172cd5fcdd1e3f0d6',
    'analysis/INDEPENDENT_SCIENTIFIC_AUDIT.json': 'ed77c435a67ade4a1276179b069b5d22db2a7675a9af575814fca4302474d63e',
}
AUDIT_PATH = Path('analysis/INDEPENDENT_SCIENTIFIC_AUDIT.json')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def inventory(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlink outside archived regular-file scope: ' + str(path))
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha(path)
    return result


def normalized(report: dict) -> dict:
    # Only the audit's declared generation timestamp is expected to change.
    return {key: value for key, value in report.items() if key != 'created_utc'}


def run(archive: Path, destination: Path) -> int:
    if archive.is_symlink() or not archive.is_file():
        raise ValueError('Archive must be an existing regular file')
    if sha(archive) != ARCHIVE_SHA256:
        raise ValueError('This helper is bound to the exact preserved v1 archive')
    if destination.exists():
        raise FileExistsError('Destination exists; choose a new verification output directory')
    destination.mkdir()
    report = {
        'schema': 'capability-preserved-audit-rerun/v1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'RUNNING',
        'archive_sha256': ARCHIVE_SHA256,
        'helper_sha256': sha(Path(__file__)),
        'original_audit_pins': PINNED,
        'scientific_confirmation_rerun': False,
        'new_mission_execution': False,
        'remote_execution': False,
        'method': 'Unchanged archived audit executed in a fresh temporary copy; archived receipt retained separately and fixed output destination initially absent.',
    }
    write_json(destination / 'VERIFICATION.json', report)
    try:
        with tempfile.TemporaryDirectory(prefix='agialpha-preserved-audit-') as temporary:
            temp = Path(temporary)
            extracted = temp / 'archive'
            extracted.mkdir()
            with tarfile.open(archive, 'r:gz') as bundle:
                members = bundle.getmembers()
                for member in members:
                    path = PurePosixPath(member.name)
                    if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                        raise ValueError('Unexpected archived path/type: ' + member.name)
                bundle.extractall(extracted, filter='data')
            original = extracted / 'capability_study'
            for relative, wanted in PINNED.items():
                if sha(original / relative) != wanted:
                    raise ValueError('Pinned archived artifact differs: ' + relative)
            freeze = json.loads((original / 'protocol/FREEZE.json').read_text())
            for item in freeze['files']:
                source = original / item['path']
                if source.stat().st_size != item['bytes'] or sha(source) != item['sha256']:
                    raise ValueError('Frozen source differs: ' + item['path'])
            recorded_bytes = (original / AUDIT_PATH).read_bytes()
            (destination / 'RECORDED_AUDIT.json').write_bytes(recorded_bytes)
            source_inventory = inventory(original)
            workspace = temp / 'verification'

            def omit_recorded_destination(directory: str, names: list[str]) -> list[str]:
                if Path(directory) == original / 'analysis':
                    return ['INDEPENDENT_SCIENTIFIC_AUDIT.json']
                return []

            shutil.copytree(original, workspace, ignore=omit_recorded_destination)
            expected_workspace = {key: value for key, value in source_inventory.items() if key != AUDIT_PATH.as_posix()}
            if inventory(workspace) != expected_workspace:
                raise ValueError('Working copy differs before audit invocation')
            env = dict(os.environ)
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            completed = subprocess.run(
                [sys.executable, '-B', str(workspace / 'analysis/independent_summary_audit.py')],
                cwd=workspace, env=env, capture_output=True, text=True, timeout=120,
            )
            (destination / 'stdout.txt').write_text(completed.stdout)
            (destination / 'stderr.txt').write_text(completed.stderr)
            report['audit_returncode'] = completed.returncode
            if completed.returncode != 0:
                raise RuntimeError('Preserved audit returned nonzero; see retained stdout/stderr')
            generated = workspace / AUDIT_PATH
            if not generated.is_file():
                raise ValueError('Audit produced no new receipt')
            (destination / 'RECOMPUTED_AUDIT.json').write_bytes(generated.read_bytes())
            observed_workspace = inventory(workspace)
            generated_sha = observed_workspace.pop(AUDIT_PATH.as_posix())
            if observed_workspace != expected_workspace:
                raise ValueError('Audit changed working inputs outside its new receipt')
            if inventory(original) != source_inventory:
                raise ValueError('Archived extraction changed')
            previous = json.loads(recorded_bytes)
            current = json.loads(generated.read_text())
            equal = normalized(previous) == normalized(current)
            report.update({
                'frozen_inputs_verified': len(freeze['files']),
                'archived_study_files_verified_unchanged': len(source_inventory),
                'working_input_files_verified_unchanged': len(expected_workspace),
                'original_audit_source_unchanged': sha(workspace / 'analysis/independent_summary_audit.py') == PINNED['analysis/independent_summary_audit.py'],
                'recorded_audit_sha256': sha(destination / 'RECORDED_AUDIT.json'),
                'recomputed_audit_sha256': generated_sha,
                'audit_passed': current.get('passed'),
                'checks_total': current.get('checks_total'),
                'failed_checks': current.get('failed_checks'),
                'matches_recorded_audit_except_created_utc': equal,
            })
            if current.get('passed') is not True or not equal:
                raise ValueError('Recomputed scientific audit differs; failure retained without retry')
        report['archive_unchanged'] = sha(archive) == ARCHIVE_SHA256
        if not report['archive_unchanged']:
            raise ValueError('Original archive identity changed')
        report['status'] = 'PASS'
        returncode = 0
    except Exception:
        report['status'] = 'FAIL'
        report['error'] = traceback.format_exc()
        report['archive_unchanged'] = sha(archive) == ARCHIVE_SHA256
        returncode = 1
    report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(destination / 'VERIFICATION.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'original_audit_pins'}))
    return returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.archive.resolve(), args.destination.resolve()))
