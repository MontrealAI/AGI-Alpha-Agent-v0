from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workloads'))
from verifier import verify


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('job', type=Path)
    parser.add_argument('result', type=Path)
    parser.add_argument('oracle', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--parent-task', type=Path)
    parser.add_argument('--parent-result', type=Path)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (55, 55))
    begin = time.perf_counter()
    cpu = time.process_time()
    parent_task = json.loads(args.parent_task.read_text()) if args.parent_task else None
    parent_result = json.loads(args.parent_result.read_text()) if args.parent_result else None
    report = verify(json.loads(args.job.read_text()), json.loads(args.result.read_text()), json.loads(args.oracle.read_text()),
                    parent_task=parent_task, parent_result=parent_result)
    report['resource_measurement'] = {'wall_seconds': time.perf_counter() - begin, 'cpu_seconds': time.process_time() - cpu,
                                     'max_rss_kb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    args.output.write_text(json.dumps(report, allow_nan=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
