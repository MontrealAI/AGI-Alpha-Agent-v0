from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

SOURCE = Path(__file__).resolve().parents[1] / 'independent' / 'solver.py'


def solve_design(task: dict[str, Any]) -> dict[str, Any]:
    if task.get('family') != 'design':
        raise ValueError('CONTRIBUTED_DESIGN_SCOPE_REQUIRED')
    spec = importlib.util.spec_from_file_location('contributed_design_v2', SOURCE)
    if spec is None or spec.loader is None:
        raise ValueError('CONTRIBUTED_IMPLEMENTATION_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.solve(task)
