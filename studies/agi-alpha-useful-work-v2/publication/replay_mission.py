# SPDX-License-Identifier: Apache-2.0
"""Reproduce a frozen mission offline in a relocated companion, without new-job credit."""
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

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mission', required=True)
    parser.add_argument('--arm', choices=['retained', 'conventional'], default='conventional')
    parser.add_argument('--out', type=Path, required=True, help='New directory within the companion root.')
    args = parser.parse_args()
    registry = read(ROOT / 'data/confirmation-inputs/mission-registry.json')
    primary = {row['mission'] for row in read(ROOT / 'protocol/primary-protocol.json')['mission_order']}
    if args.mission not in primary:
        raise ValueError('SELECT_A_FROZEN_PRIMARY_MISSION')
    out = (ROOT / args.out).resolve()
    if not out.is_relative_to(ROOT) or out == ROOT or out.exists():
        raise ValueError('NEW_OUTPUT_WITHIN_COMPANION_REQUIRED')
    out.mkdir(parents=True)
    wall, cpu = time.perf_counter(), time.process_time()
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {'schema': 'relocated-component-mission-replay/v1', 'mission': args.mission, 'arm': args.arm,
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'offline': True,
              'new_missions': 0, 'money_usd': None, 'steps': [], 'complete': False}

    def execute(command, name, timeout=60):
        start = time.perf_counter()
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        (out / (name + '.stdout.txt')).write_text(completed.stdout)
        (out / (name + '.stderr.txt')).write_text(completed.stderr)
        result['steps'].append({'name': name, 'command': command, 'exit_code': completed.returncode,
                                'wall_seconds': time.perf_counter() - start})
        if completed.returncode:
            raise ValueError('REPLAY_STEP_FAILED:' + name)

    try:
        freeze_path = ROOT / 'protocol/source-freeze.json'
        freeze = read(freeze_path)
        if sha(freeze_path) != 'f417768b69a6729000d5ce9d10393bfac7eec45b7ce448a0d61c711a6662530c':
            raise ValueError('FREEZE_IDENTITY')
        for row in freeze['files']:
            if sha(ROOT / row['path']) != row['sha256']:
                raise ValueError('FROZEN_SOURCE_CHANGED:' + row['path'])
        entry = registry['missions'][args.mission]
        original_job_path = ROOT / entry['path']
        if sha(original_job_path) != entry['sha256']:
            raise ValueError('JOB_IDENTITY')
        job = read(original_job_path)
        result['original_job_sha256'] = sha(original_job_path)
        result['plan_relocations'] = []
        for side in ('before', 'after'):
            original_environment = ROOT / job[side]['environment']
            original_plan = ROOT / 'data/confirmation-inputs/plans' / (original_environment.name + '.json')
            plan = read(original_plan)
            plan['native_lock'] = str(ROOT / 'discovery/requirements/requirements-agent.lock')
            plan['incoming_constraint_metadata'] = [str(ROOT / 'discovery/release-metadata' / Path(p).name)
                                                     for p in plan['incoming_constraint_metadata']]
            plan['consumer_contract'] = str(ROOT / 'protocol/component-contract.json')
            relocated = out / (side + '-relocated-plan.json')
            write(relocated, plan)
            result['plan_relocations'].append({'side': side, 'original_sha256': sha(original_plan),
                                               'relocated_sha256': sha(relocated), 'changes': 'Absolute local paths only'})
            env = out / (side + '-environment')
            execute([sys.executable, str(ROOT / 'curation/prepare_environment.py'), '--plan', str(relocated),
                     '--out', str(env), '--metadata-reuse', str(original_environment / 'metadata'),
                     '--wheel-reuse', str(original_environment / 'wheels'), '--confirmation-freeze', str(freeze_path),
                     '--offline'], side + '-environment')
            prepared = read(env / 'preparation.json')
            if prepared.get('complete') is not True or prepared.get('network_requests') != 0:
                raise ValueError('OFFLINE_ENVIRONMENT_INCOMPLETE')
            job[side]['environment'] = str(env.relative_to(ROOT))
        replay_id = 'replay-' + args.mission
        job.update(mission_id=replay_id, phase='development',
                   trigger='Reproduction of an already exposed mission; zero new mission credit',
                   replay_of=args.mission, original_job_sha256=result['original_job_sha256'])
        job_path = out / 'replay-job.json'
        write(job_path, job)
        replay_registry = out / 'replay-registry.json'
        write(replay_registry, {'schema': 'alpha-component-registry/v1', 'missions': {
            replay_id: {'path': str(job_path.relative_to(ROOT)), 'sha256': sha(job_path)}}})
        execute(['node', str(ROOT / 'src/workbench.mjs'), replay_id, args.arm, str(out / 'native'),
                 str(replay_registry.relative_to(ROOT))], 'native-workbench')
        delivery = read(out / 'native/delivery/delivery.json')
        result.update(complete=delivery.get('accepted') is True, decision=delivery.get('decision'),
                      replay_job_sha256=sha(job_path), delivery_sha256=sha(out / 'native/delivery/delivery.json'),
                      native_inspection=read(out / 'native/inspection.json'))
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      wall_seconds=time.perf_counter() - wall, process_cpu_seconds=time.process_time() - cpu,
                      child_cpu_seconds=after.ru_utime + after.ru_stime - children.ru_utime - children.ru_stime,
                      aggregation='Inclusive replay total; nested setup/delivery records must not be added again.')
        write(out / 'replay.json', result)
    print(json.dumps({key: result.get(key) for key in ('complete', 'decision', 'error', 'new_missions', 'wall_seconds')}))
    if not result['complete']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
