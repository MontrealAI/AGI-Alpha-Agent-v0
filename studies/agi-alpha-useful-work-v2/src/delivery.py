# SPDX-License-Identifier: Apache-2.0
"""Run one registered component assessment through a complete local delivery."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import resource
import time

from run_pair import run_pair

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--arm', choices=['retained', 'conventional'], required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    wall, cpu = time.perf_counter(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {'schema': 'alpha-component-delivery/v1', 'arm': args.arm,
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'job_sha256': hashlib.sha256(args.job.read_bytes()).hexdigest(),
              'money_usd': None, 'operator_minutes': None, 'customer_minutes': None,
              'runtime_model_calls': 0, 'runtime_network_requests': 0,
              'accepted': False, 'decision': 'INCOMPLETE_HOLD'}
    try:
        pair = run_pair(args.job.resolve(), args.out / 'pair', args.arm)
        if args.arm == 'retained':
            from package_component import assemble
            packet = assemble(args.job.resolve(), args.out / 'pair', args.out / 'package')
        else:
            from conventional_package import assemble
            job = json.loads(args.job.read_text())
            packet = assemble(job, args.out / 'pair', args.out / 'package')
        if packet is None:
            packet = json.loads((args.out / 'package/decision.json').read_text())
        result['decision'] = packet['decision']
        result['accepted'] = packet.get('useful_outcome_accepted', packet['decision'] in (
            'SCOPED_COMPONENT_PRESERVED', 'COMPONENT_REGRESSION'))
        result['pair_custody_complete'] = pair['custody_complete']
        result['decision_sha256'] = hashlib.sha256((args.out / 'package/decision.json').read_bytes()).hexdigest()
        result['package_path'] = str((args.out / 'package').resolve())
        result['evidence'] = {'pair': 'pair/pair.json', 'package': 'package/decision.json',
                             'manifest': 'package/artifact-manifest.json'}
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result['wall_seconds'] = time.perf_counter() - wall
        result['process_cpu_seconds'] = time.process_time() - cpu
        result['child_cpu_seconds'] = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        result['child_peak_rss_kib'] = after.ru_maxrss
        result['ended_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result['aggregation'] = 'Delivery total includes paired execution, verification, packaging and integrity. Do not add nested pair/command/case receipts again. Environment setup and capability lifecycle costs are additional.'
        (args.out / 'delivery.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if result.get('error'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
