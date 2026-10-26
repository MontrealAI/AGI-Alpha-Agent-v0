# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills'))
sys.path.insert(0, str(ROOT / 'workloads'))
from verifier import verify
from workload_generator import materialize_design
import numpy as np
import scipy

ENTRYPOINTS = {
    'forward@1': ('skills/forward.py', 'solve_forward'),
    'inverse@1': ('skills/inverse.py', 'solve_inverse'),
    'design@1': ('skills/design.py', 'solve_design'),
    'design@2': ('skills/selected_design.py', 'solve_design'),
}


def identity(path: Path) -> dict[str, Any]:
    relative = path.relative_to(ROOT).as_posix()
    if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
        raise ValueError('UNSAFE_SOURCE_PATH')
    data = path.read_bytes()
    return {'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def source_closure() -> list[dict[str, Any]]:
    paths = set((ROOT / 'skills').glob('*.py'))
    paths.update(ROOT / name for name in [
        'independent/solver.py', 'production/worker.py', 'workloads/verifier.py',
        'workloads/workload_generator.py', 'identity/validate_evidence.py',
    ])
    return [identity(path) for path in sorted(paths)]


def check_closure(records: list[dict[str, Any]]) -> None:
    for record in records:
        if identity(ROOT / record['path']) != record:
            raise ValueError('CURRENT_IMPLEMENTATION_DRIFT:' + record['path'])


def save(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return path.relative_to(ROOT).as_posix()


def execute_current(output: Path) -> dict[str, Any]:
    if output.exists() or not output.resolve().is_relative_to(ROOT):
        raise ValueError('NEW_STUDY_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    started, cpu = time.perf_counter(), time.process_time()
    closure = source_closure()
    save(output / 'source-closure.json', closure)
    modules = {}
    for skill, (source, callable_name) in ENTRYPOINTS.items():
        spec = importlib.util.spec_from_file_location('admission_' + skill.replace('@', '_'), ROOT / source)
        if spec is None or spec.loader is None:
            raise ValueError('ENTRYPOINT_UNAVAILABLE')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules[skill] = getattr(module, callable_name)
    entries = []
    for chain in ['DISC-01', 'DISC-02']:
        inverse_task = None
        inverse_result = None
        inverse_acceptance = None
        inverse_paths = None
        for skill in ENTRYPOINTS:
            family, version = skill.split('@')
            directory = output / chain / (family + '-v' + version)
            task_file = ROOT / 'workloads/discovery/tasks' / (chain + '-' + family.upper() + '.json')
            task = json.loads(task_file.read_text())
            oracle_file = ROOT / 'workloads/discovery/oracles' / (chain + '-' + family.upper() + '.json')
            oracle = json.loads(oracle_file.read_text())
            if family == 'design':
                task = materialize_design(task, inverse_task, inverse_result, inverse_acceptance)
            task_path = save(directory / 'task.json', task)
            check_closure(closure)
            begin, begin_cpu = time.perf_counter(), time.process_time()
            try:
                result = modules[skill](deepcopy(task))
                json.dumps(result, allow_nan=False)
            except Exception as error:
                result = {'status': 'error', 'error_type': type(error).__name__, 'reason': str(error),
                          'traceback': traceback.format_exc()}
            elapsed, used_cpu = time.perf_counter() - begin, time.process_time() - begin_cpu
            check_closure(closure)
            report = verify(task, result, oracle, parent_task=inverse_task if family == 'design' else None,
                            parent_result=inverse_result if family == 'design' else None)
            result_path = save(directory / 'result.json', result)
            verification_path = save(directory / 'verification.json', report)
            case = {'task': task_path, 'result': result_path, 'oracle': oracle_file.relative_to(ROOT).as_posix(),
                    'verification': verification_path}
            if family == 'design':
                case.update(parent_task=inverse_paths['task'], parent_result=inverse_paths['result'],
                            parent_acceptance=inverse_paths['verification'])
            entries.append({'skill': skill, 'chain': chain, 'case': case, 'accepted': report['accepted'],
                            'entrypoint': ENTRYPOINTS[skill][0], 'callable': ENTRYPOINTS[skill][1],
                            'solver_wall_seconds': elapsed, 'solver_cpu_seconds': used_cpu,
                            'source_closure_sha256': hashlib.sha256(json.dumps(closure, sort_keys=True).encode()).hexdigest()})
            if family == 'inverse':
                inverse_task, inverse_result, inverse_acceptance, inverse_paths = task, result, report, case
    dispatch_entries = []
    for chain in ['DISC-01', 'DISC-02']:
        parent_task = parent_result = parent_acceptance = parent_paths = None
        for family in ['forward', 'inverse', 'design']:
            skill = family + ('@2' if family == 'design' else '@1')
            directory = output / 'production-dispatch' / chain / family
            task = json.loads((ROOT / 'workloads/discovery/tasks' / (chain + '-' + family.upper() + '.json')).read_text())
            oracle_file = ROOT / 'workloads/discovery/oracles' / (chain + '-' + family.upper() + '.json')
            if family == 'design':
                task = materialize_design(task, parent_task, parent_result, parent_acceptance)
            task_path = save(directory / 'task.json', task)
            check_closure(closure)
            begin = time.perf_counter()
            process = subprocess.run([sys.executable, str(ROOT / 'production/worker.py'), 'shared',
                                      str(ROOT / task_path), str(directory / 'result.json')],
                                     cwd=ROOT, capture_output=True, text=True, timeout=50)
            if process.returncode != 0 or not (directory / 'result.json').is_file():
                result = {'status': 'error', 'reason': 'PRODUCTION_DISPATCH_FAILED',
                          'returncode': process.returncode, 'stderr': process.stderr[-4000:]}
                save(directory / 'result.json', result)
            else:
                result = json.loads((directory / 'result.json').read_text())
            check_closure(closure)
            report = verify(task, result, json.loads(oracle_file.read_text()),
                            parent_task=parent_task if family == 'design' else None,
                            parent_result=parent_result if family == 'design' else None)
            verification_path = save(directory / 'verification.json', report)
            case = {'task': task_path, 'result': (directory / 'result.json').relative_to(ROOT).as_posix(),
                    'oracle': oracle_file.relative_to(ROOT).as_posix(), 'verification': verification_path}
            if family == 'design':
                case.update(parent_task=parent_paths['task'], parent_result=parent_paths['result'],
                            parent_acceptance=parent_paths['verification'])
            dispatch_entries.append({'skill': skill, 'chain': chain, 'case': case, 'accepted': report['accepted'],
                                     'entrypoint': 'production/worker.py shared -> skills/network_capability.py:solve',
                                     'elapsed_seconds': time.perf_counter() - begin})
            if family == 'inverse':
                parent_task, parent_result, parent_acceptance, parent_paths = task, result, report, case
    check_closure(closure)
    summary = {'schema': 'capability-current-implementation-validation/v1',
               'executed_at_utc': datetime.now(timezone.utc).isoformat(),
               'accepted': all(item['accepted'] for item in entries + dispatch_entries),
               'entries': entries, 'dispatch_entries': dispatch_entries, 'source_files': closure,
               'checks': len(entries) + len(dispatch_entries),
               'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
               'elapsed_seconds': time.perf_counter() - started, 'cpu_seconds': time.process_time() - cpu,
               'max_rss_kb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               'dispatch_child_cpu_seconds': resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,
               'empirical_nodes': [225, 400], 'prospective_scope': 'Fresh bounded research trials only; primary not run',
               'live_identity_enforcement': 'NOT_RUN', 'native_authority': []}
    save(output / 'execution-summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = execute_current(args.output.resolve())
    print(json.dumps({'accepted': result['accepted'], 'checks': result['checks'],
                      'elapsed_seconds': result['elapsed_seconds']}, allow_nan=False))
    if not result['accepted']:
        raise SystemExit(2)
