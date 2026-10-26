from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workloads'))
from workload_generator import canonical, materialize_design, release_design

ARMS = ['A', 'B', 'C', 'D']
METHODS = {'A': 'independent', 'B': 'shared', 'C': 'shared', 'D': 'conventional'}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(task_path: Path, oracle_path: Path, destination: Path, arm: str, parent: tuple[Path, Path] | None, use_catalog: bool) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    command = ['node', str(ROOT / 'production' / ('run_one.mjs' if use_catalog else 'workbench.mjs')),
               str(task_path), str(oracle_path), str(destination), arm if use_catalog else METHODS[arm]]
    if parent:
        command += [str(parent[0]), str(parent[1])]
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONHASHSEED='0')
    begin = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = datetime.now(timezone.utc).isoformat()
    process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=70)
        code = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        code = 124
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    elapsed = time.perf_counter() - begin
    (destination / 'stdout.txt').write_text(stdout)
    (destination / 'stderr.txt').write_text(stderr)
    verification = json.loads((destination / 'verification.json').read_text()) if (destination / 'verification.json').exists() else {}
    inspection = json.loads((destination / 'inspection.json').read_text()) if (destination / 'inspection.json').exists() else {}
    pack = json.loads((destination / 'pack.json').read_text()) if (destination / 'pack.json').exists() else {}
    evaluation = pack.get('evaluation', {})
    native_boundary = evaluation.get('admission') == 'HOLD' and evaluation.get('authority') == [] and evaluation.get('settlement') == 'NOT_CONNECTED'
    accepted = code == 0 and elapsed <= 60 and verification.get('accepted') is True and native_boundary and inspection.get('activeAuthority') == []
    record = {'arm': arm, 'method': METHODS[arm], 'started_at': started, 'elapsed_seconds': elapsed,
              'cpu_seconds': (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime),
              'child_cpu_accounting': 'UNKNOWN_AFTER_FORCED_GROUP_TERMINATION' if code == 124 else 'POSIX RUSAGE_CHILDREN including waited descendant processes',
              'child_cpu_complete': code != 124,
              'exit_code': code, 'accepted': accepted, 'task_path': str(task_path.relative_to(ROOT)),
              'complete_budget_respected': elapsed <= 60, 'native_boundary_preserved': native_boundary,
              'task_sha256': digest(task_path), 'oracle_sha256': digest(oracle_path),
              'output': str(destination.relative_to(ROOT)), 'verification': verification, 'native_inspection': inspection}
    if (destination / 'result.json').exists():
        record['result_sha256'] = digest(destination / 'result.json')
    (destination / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def campaign(cohort: str, arms: list[str], output: Path, use_catalog: bool, limit: int, replay: bool = False) -> None:
    output.mkdir(parents=True, exist_ok=False)
    cohort_root = ROOT / 'workloads' / cohort
    tasks = cohort_root / ('forward-inverse/tasks' if cohort == 'primary' else 'tasks')
    oracles = cohort_root / ('forward-inverse/oracles' if cohort == 'primary' else 'oracles')
    chain_ids = sorted(p.stem.removesuffix('-FORWARD') for p in tasks.glob('*-FORWARD.json'))
    if not chain_ids:
        raise ValueError('NO_REGISTERED_TASKS')
    records: list[dict[str, Any]] = []
    start = time.monotonic()
    for stage, family in enumerate(['forward', 'inverse', 'design']):
        if family == 'design':
            seal = [{'task': r['id'], 'arm': r['arm'], 'accepted': r['accepted'], 'result_sha256': r.get('result_sha256')}
                    for r in records if r['family'] == 'inverse']
            (output / 'inverse-seal.json').write_text(json.dumps(seal, indent=2) + '\n')
            if cohort == 'primary':
                outcomes = []
                for row in [r for r in records if r['family'] == 'inverse']:
                    result_path = ROOT / row['output'] / 'result.json'
                    if not result_path.exists():
                        result_path.write_text(json.dumps({'status': 'not_completed', 'task_id': row['id'], 'arm': row['arm'],
                                                         'reason': row.get('blocked', 'recorded process failure')}) + '\n')
                    outcomes.append({'task_id': row['id'], 'arm': row['arm'], 'result_path': str(result_path), 'sha256': digest(result_path)})
                sealed_file = output / 'inverse-outcomes-seal.json'
                sealed_file.write_text(json.dumps({'inverse_outcomes': outcomes}, indent=2) + '\n')
                if not replay:
                    release_design(cohort_root, sealed_file, digest(sealed_file))
                elif not (cohort_root / 'design-released').exists():
                    raise ValueError('REPLAY_REQUIRES_ORIGINAL_RELEASED_DESIGN')
                tasks = cohort_root / 'design-released/tasks'
                oracles = cohort_root / 'design-released/oracles'
        for index, chain in enumerate(chain_ids):
            base_path = tasks / (chain + '-' + family.upper() + '.json')
            task = json.loads(base_path.read_text())
            oracle = oracles / base_path.name
            order = ARMS[(index + stage) % 4:] + ARMS[:(index + stage) % 4]
            for arm in [x for x in order if x in arms]:
                target = output / chain / family / arm
                parent = None
                actual_path = base_path
                blocked = None
                if time.monotonic() - start > limit:
                    blocked = 'CAMPAIGN_RESOURCE_ENVELOPE_EXHAUSTED'
                if family == 'design':
                    earlier = next(r for r in records if r['chain'] == chain and r['arm'] == arm and r['family'] == 'inverse')
                    if not earlier['accepted']:
                        blocked = 'UPSTREAM_INVERSE_NOT_ACCEPTED'
                    else:
                        inverse_path = (cohort_root / ('forward-inverse/tasks' if cohort == 'primary' else 'tasks')) / (chain + '-INVERSE.json')
                        parent_dir = ROOT / earlier['output']
                        inverse_task = json.loads(inverse_path.read_text())
                        inverse_result = json.loads((parent_dir / 'result.json').read_text())
                        inverse_acceptance = json.loads((parent_dir / 'verification.json').read_text())
                        materialized = materialize_design(task, inverse_task, inverse_result, inverse_acceptance)
                        location = output / 'materialized' / chain
                        location.mkdir(parents=True, exist_ok=True)
                        actual_path = location / (arm + '-DESIGN.json')
                        actual_path.write_bytes(canonical(materialized) + b'\n')
                        parent = (inverse_path, parent_dir / 'result.json')
                if blocked:
                    target.mkdir(parents=True, exist_ok=False)
                    row = {'arm': arm, 'method': METHODS[arm], 'accepted': False, 'blocked': blocked,
                           'cpu_seconds': 0.0, 'elapsed_seconds': 0.0, 'not_executed': True,
                           'output': str(target.relative_to(ROOT)), 'task_path': str(actual_path.relative_to(ROOT)), 'task_sha256': digest(actual_path)}
                else:
                    row = invoke(actual_path, oracle, target, arm, parent, use_catalog)
                row.update(id=task['id'], chain=chain, family=family, cohort=cohort, node_count=task['network']['node_count'])
                records.append(row)
                with (output / 'records.jsonl').open('a') as stream:
                    stream.write(json.dumps(row, allow_nan=False) + '\n')
                print(json.dumps({key: row[key] for key in ['id', 'arm', 'accepted', 'cpu_seconds', 'elapsed_seconds']}), flush=True)
    summary: dict[str, Any] = {'cohort': cohort, 'chains': len(chain_ids), 'planned_stages': len(chain_ids) * 3,
                               'observed_collections': 0, 'identity': 'FIXTURE_ONLY', 'live_authentication': 'NOT RUN', 'arms': {}}
    for arm in arms:
        own = [r for r in records if r['arm'] == arm]
        summary['arms'][arm] = {'accepted_stages': sum(r['accepted'] for r in own), 'stage_count': len(own),
                                'accepted_chains': sum(all(r['accepted'] for r in own if r['chain'] == chain) for chain in chain_ids),
                                'cpu_seconds': sum(r['cpu_seconds'] for r in own), 'elapsed_seconds': sum(r['elapsed_seconds'] for r in own),
                                'not_executed': sum(r.get('not_executed', False) for r in own)}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=['discovery', 'primary'], required=True)
    parser.add_argument('--arms', default='ABCD')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--catalog', action='store_true')
    parser.add_argument('--limit', type=int, default=2700)
    parser.add_argument('--replay', action='store_true')
    arguments = parser.parse_args()
    campaign(arguments.cohort, list(arguments.arms), arguments.output.resolve(), arguments.catalog, arguments.limit, arguments.replay)
