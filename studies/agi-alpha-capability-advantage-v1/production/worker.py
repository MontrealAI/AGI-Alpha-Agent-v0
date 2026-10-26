from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
MODULES = {'shared': 'skills/network_capability.py', 'conventional': 'conventional/solver.py', 'independent': 'independent/solver.py'}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('method', choices=MODULES)
    parser.add_argument('job', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (55, 55))
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    source = ROOT / MODULES[args.method]
    sys.path.insert(0, str(source.parent))
    begin = time.perf_counter()
    cpu = time.process_time()
    try:
        spec = importlib.util.spec_from_file_location('declared_research_solver', source)
        if spec is None or spec.loader is None:
            raise ValueError('DECLARED_MODULE_UNAVAILABLE')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        task = json.loads(args.job.read_text())
        result = module.solve(task)
        if not isinstance(result, dict):
            raise ValueError('INVALID_RESULT')
        json.dumps(result, allow_nan=False)
    except Exception as exc:
        result = {'status': 'error', 'error_type': type(exc).__name__, 'reason': str(exc), 'traceback': traceback.format_exc()}
    result['resource_measurement'] = {'wall_seconds': time.perf_counter() - begin, 'cpu_seconds': time.process_time() - cpu,
                                     'max_rss_kb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                     'pid': os.getpid(), 'scope': 'solver module import and invocation; parent process records full child CPU'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, allow_nan=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
