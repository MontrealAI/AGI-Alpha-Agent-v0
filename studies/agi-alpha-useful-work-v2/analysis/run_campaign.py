# SPDX-License-Identifier: Apache-2.0
"""Invocation-only expansion of the frozen protocol; A requires root input.

Created after source freeze, before any primary behavior outcome. It supplies no
new oracle or automatic A decision. All construction and scheduling are charged.
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/confirmation'
FREEZE_SHA = 'f417768b69a6729000d5ce9d10393bfac7eec45b7ce448a0d61c711a6662530c'
REGISTRY = ROOT / 'data/confirmation-inputs/mission-registry.json'
SPEC = importlib.util.spec_from_file_location('frozen_common_launch_helpers', ROOT / 'src/run_pair.py')
COMMON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMMON)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def freeze_check():
    path = ROOT / 'protocol/source-freeze.json'
    if sha(path) != FREEZE_SHA:
        raise ValueError('FREEZE_IDENTITY')
    rows = read(path)['files']
    failures = [r['path'] for r in rows if sha(ROOT / r['path']) != r['sha256']
                or (ROOT / r['path']).stat().st_size != r['bytes']]
    if failures:
        raise ValueError('FROZEN_FILES_CHANGED:' + ','.join(failures))
    return {'checked_at': now(), 'files': len(rows), 'unchanged': True, 'freeze_sha256': FREEZE_SHA}


def meter(phase, receipt, binds, outputs, command, timeout=45):
    argv = [sys.executable, str(ROOT / 'src/measured_run.py'), '--phase', phase,
            '--record', str(receipt), '--timeout', str(timeout)]
    for path in binds:
        argv.extend(['--bind', str(path)])
    for path in outputs:
        argv.extend(['--output', str(path)])
    return argv + ['--'] + command


def manual_pair(job_path, out):
    """Expand the preserved manual command template, without a decision producer."""
    out.mkdir(parents=True, exist_ok=False)
    start, cpu, child = time.perf_counter(), time.process_time(), resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'job.json').write_bytes(job_path.read_bytes())
    job = read(job_path)
    worker = ROOT / 'src/manual_probe.py'
    result = {'schema': 'alpha-component-pair/v1', 'arm': 'manual', 'started_at': now(),
              'job_sha256': sha(job_path), 'worker_path': 'src/manual_probe.py',
              'worker_sha256': sha(worker), 'records': COMMON.RECORDS, 'custody_complete': False,
              'runtime_model_calls': 0, 'money_usd': None, 'process_results': []}
    try:
        contract, consumer = COMMON.validate_job(job)
        processes = []
        for side in ('before', 'after'):
            env = COMMON.local_path(job[side]['environment'])
            paths = {key: out / value for key, value in COMMON.RECORDS[side].items()}
            interpreter = env / 'venv/bin/python'
            binds = [job_path, worker, ROOT / 'src/measured_run.py', contract,
                     ROOT / 'protocol/component-projections.json', consumer / 'api.py', consumer / 'models.py',
                     env / 'requirements.lock', env / 'preparation.json', interpreter]
            command = [str(interpreter), '-I', '-B', str(worker), '--consumer', str(consumer),
                       '--contract', str(contract), '--out', str(paths['observations'])]
            argv = meter(side + '-consumer-execution', paths['execution'], binds, [paths['observations']], command)
            processes.append((side, subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
        for side, process in processes:
            stdout, stderr = process.communicate()
            result['process_results'].append({'side': side, 'phase': 'observations', 'exit_code': process.returncode,
                                              'stdout': stdout, 'stderr': stderr})
        for side in ('before', 'after'):
            env = COMMON.local_path(job[side]['environment'])
            paths = {key: out / value for key, value in COMMON.RECORDS[side].items()}
            if not paths['observations'].is_file():
                continue
            verifier = ROOT / 'src/verify_component.py'
            binds = [job_path, verifier, contract, ROOT / 'protocol/component-projections.json', paths['observations'],
                     consumer / 'api.py', consumer / 'models.py', ROOT / 'discovery/test_api_boundary.py', env / 'preparation.json']
            command = [sys.executable, str(verifier), '--contract', str(contract), '--consumer', str(consumer),
                       '--environment', str(env / 'preparation.json'), '--projection', 'native-fastapi-bridge-v2',
                       '--observations', str(paths['observations']), '--out', str(paths['verification'])]
            completed = subprocess.run(meter(side + '-independent-verification', paths['verification_execution'],
                                             binds, [paths['verification']], command), capture_output=True, text=True, check=False)
            result['process_results'].append({'side': side, 'phase': 'verification', 'exit_code': completed.returncode,
                                              'stdout': completed.stdout, 'stderr': completed.stderr})
        receipts = [(field, read(out / COMMON.RECORDS[side][field]) if (out / COMMON.RECORDS[side][field]).is_file() else {})
                    for side in ('before', 'after') for field in ('execution', 'verification_execution')]
        result['custody_complete'] = all(r.get('inputs_unchanged') is True and not r.get('missing_outputs', ['missing'])
                                         and r.get('command_started') is True and r.get('timed_out') is False
                                         and type(r.get('exit_code')) is int
                                         and r.get('exit_code') in ({0, 1} if field == 'execution' else {0, 2})
                                         and not r.get('launcher_error') for field, r in receipts)
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(ended_at=now(), wall_seconds=time.perf_counter() - start,
                      process_cpu_seconds=time.process_time() - cpu,
                      child_cpu_seconds=after.ru_utime + after.ru_stime - child.ru_utime - child.ru_stime,
                      child_peak_rss_kib=after.ru_maxrss)
        result['artifacts'] = [{'path': str(p.relative_to(out)), 'sha256': sha(p), 'bytes': p.stat().st_size}
                               for p in sorted(out.rglob('*')) if p.is_file()]
        write(out / 'pair.json', result)
    return result


def run_one(mission, arm, index, exposed):
    entry = read(REGISTRY)['missions'][mission]
    job = ROOT / entry['path']
    if sha(job) != entry['sha256']:
        raise ValueError('REGISTERED_JOB_CHANGED')
    out = OUT / mission / arm
    start, cpu, child = time.perf_counter(), time.process_time(), resource.getrusage(resource.RUSAGE_CHILDREN)
    terminal = {'schema': 'useful-work-campaign-terminal/v1', 'mission_id': mission, 'arm': arm,
                'sequence': index, 'started_at': now(), 'job_sha256': sha(job), 'accepted': False,
                'decision': 'INCOMPLETE_HOLD', 'earlier_arms_visible': exposed, 'model_cost_usd': None,
                'operator_minutes': None, 'customer_minutes': None, 'money_usd': None}
    print(json.dumps({'event': 'starting', 'sequence': index, 'mission': mission, 'arm': arm}), flush=True)
    try:
        if out.exists():
            raise ValueError('OUTPUT_ALREADY_EXISTS_NO_RESAMPLING')
        if arm == 'manual':
            out.mkdir(parents=True)
            pair = manual_pair(job, out / 'pair')
            review = {'event': 'manual_review_required', 'mission': mission, 'pair_custody_complete': pair['custody_complete'],
                      'verifications': {}, 'instruction': 'Root must inspect these actual outcomes and supply a JSON decision.'}
            for side in ('before', 'after'):
                p = out / 'pair' / f'{side}-verification.json'
                v = read(p) if p.is_file() else {}
                review['verifications'][side] = {'path': str(p.relative_to(ROOT)), 'sha256': sha(p) if p.is_file() else None,
                    'status': v.get('status'), 'counts': v.get('counts'), 'global_incomplete': v.get('global_incomplete'),
                    'nonpass_cases': [c for c in v.get('cases', []) if c.get('status') != 'PASS']}
            write(out / 'manual-review-request.json', review)
            print(json.dumps(review), flush=True)
            answer = json.loads(sys.stdin.readline())
            decision = answer['decision']
            write(out / 'manual-finalization.json', {'schema': 'researcher-finalization/v1', 'recorded_at': now(),
                'role': 'root assistant/researcher, not recruited no-AI human', 'decision': decision,
                'basis': answer.get('basis'), 'request_sha256': sha(out / 'manual-review-request.json'),
                'earlier_arms_visible': exposed, 'attention_minutes': None, 'inference_cost_usd': None})
            receipt = out / 'finalization-execution.json'
            argv = meter('manual-packet-finalization', receipt,
                [job, ROOT / 'curation/assemble_manual_mission.py', ROOT / 'src/conventional_package.py', out / 'pair/pair.json',
                 out / 'manual-finalization.json'], [out / 'package/decision.json', out / 'package/artifact-manifest.json'],
                [sys.executable, str(ROOT / 'curation/assemble_manual_mission.py'), '--job', str(job), '--pair-root', str(out / 'pair'),
                 '--out', str(out / 'package'), '--decision', decision])
            completed = subprocess.run(argv, capture_output=True, text=True, check=False)
            terminal['finalization_exit_code'] = completed.returncode
            terminal['finalization_stdout'] = completed.stdout
            terminal['finalization_stderr'] = completed.stderr
            terminal['manual_finalizations'] = 1
            terminal['mechanical_pair'] = str((out / 'pair/pair.json').relative_to(ROOT))
            terminal['finalization_receipt'] = str(receipt.relative_to(ROOT))
            decision_path = out / 'package/decision.json'
        else:
            receipt = out.parent / (arm + '-execution.json')
            argv = meter('native-workbench-' + arm, receipt,
                [job, REGISTRY, ROOT / 'protocol/source-freeze.json', ROOT / 'src/workbench.mjs', ROOT / 'src/delivery.py'],
                [out / 'pack.json', out / 'inspection.json', out / 'delivery/delivery.json'],
                ['node', str(ROOT / 'src/workbench.mjs'), mission, arm, str(out), str(REGISTRY.relative_to(ROOT))], 60)
            completed = subprocess.run(argv, capture_output=True, text=True, check=False)
            terminal['outer_exit_code'] = completed.returncode
            terminal['outer_stdout'] = completed.stdout
            terminal['outer_stderr'] = completed.stderr
            terminal['external_receipt'] = str(receipt.relative_to(ROOT))
            terminal['manual_finalizations'] = 0
            decision_path = out / 'delivery/package/decision.json'
        if decision_path.is_file():
            d = read(decision_path)
            terminal['decision'] = d.get('decision', 'INCOMPLETE_HOLD')
            terminal['decision_path'] = str(decision_path.relative_to(ROOT))
            terminal['decision_sha256'] = sha(decision_path)
            manifest = read(decision_path.parent / 'artifact-manifest.json')
            terminal['manifest_valid'] = all(sha(decision_path.parent / r['path']) == r['sha256']
                                              and (decision_path.parent / r['path']).stat().st_size == r['bytes']
                                              for r in manifest['files'])
            command_complete = (terminal.get('finalization_exit_code') == 0 if arm == 'manual'
                                else terminal.get('outer_exit_code') == 0)
            terminal['accepted'] = (command_complete and terminal['manifest_valid']
                                    and terminal['decision'] in ('SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION'))
        terminal['freeze_after'] = freeze_check()
    except Exception as exc:
        terminal['error'] = f'{type(exc).__name__}: {exc}'
        terminal['accepted'] = False
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        terminal.update(ended_at=now(), service_span_seconds=time.perf_counter() - start,
                        driver_process_cpu_seconds=time.process_time() - cpu,
                        inclusive_child_cpu_seconds=after.ru_utime + after.ru_stime - child.ru_utime - child.ru_stime,
                        child_peak_rss_kib=after.ru_maxrss,
                        aggregation='Service span includes scheduling/root response for A; not human attention. Inclusive child CPU is nested, not additive to receipts.')
        write(out / 'terminal.json', terminal)
    print(json.dumps({'event': 'completed', 'mission': mission, 'arm': arm, 'accepted': terminal['accepted'],
                      'decision': terminal['decision'], 'error': terminal.get('error')}), flush=True)
    return terminal


def main():
    if OUT.exists():
        raise ValueError('CAMPAIGN_ALREADY_STARTED_NO_RESAMPLING')
    OUT.mkdir(parents=True)
    start, cpu, child = time.perf_counter(), time.process_time(), resource.getrusage(resource.RUSAGE_CHILDREN)
    campaign = {'schema': 'useful-work-campaign/v1', 'started_at': now(), 'driver_sha256': sha(Path(__file__)),
                'freeze_before': freeze_check(), 'registry_sha256': sha(REGISTRY), 'results': [], 'money_usd': None}
    write(OUT / 'campaign-start.json', campaign)
    for row in read(ROOT / 'protocol/primary-protocol.json')['mission_order']:
        exposed = []
        for arm in row['arms']:
            terminal = run_one(row['mission'], arm, len(campaign['results']) + 1, list(exposed))
            campaign['results'].append({'mission_id': row['mission'], 'arm': arm, 'accepted': terminal['accepted'],
                                        'terminal': str((OUT / row['mission'] / arm / 'terminal.json').relative_to(ROOT))})
            exposed.append(arm)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    campaign.update(ended_at=now(), wall_seconds=time.perf_counter() - start, process_cpu_seconds=time.process_time() - cpu,
                    child_cpu_seconds=after.ru_utime + after.ru_stime - child.ru_utime - child.ru_stime,
                    freeze_after=freeze_check(), accepted_evaluations=sum(r['accepted'] for r in campaign['results']),
                    unique_missions=6, arm_evaluations=18,
                    aggregation='Campaign envelope includes all run resources and root scheduling; do not sum with nested receipts.')
    write(OUT / 'campaign.json', campaign)
    print(json.dumps({'event': 'campaign_complete', 'accepted_evaluations': campaign['accepted_evaluations'], 'unique_missions': 6}), flush=True)


if __name__ == '__main__':
    main()
