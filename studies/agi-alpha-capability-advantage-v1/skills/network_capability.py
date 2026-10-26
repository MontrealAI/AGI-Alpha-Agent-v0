from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from forward import solve_forward
from inverse import solve_inverse
from selected_design import solve_design


def solve(task: dict[str, Any]) -> dict[str, Any]:
    if task.get('schema') != 'agi-alpha-conductance-job/v1':
        raise ValueError('UNSUPPORTED_JOB_SCHEMA')
    functions = {'forward': solve_forward, 'inverse': solve_inverse, 'design': solve_design}
    return functions[task['family']](task)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('job', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = solve(json.loads(args.job.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, allow_nan=False, indent=2) + '\n')
