from __future__ import annotations

from typing import Any

import numpy as np

from core import Network


def solve_forward(task: dict[str, Any]) -> dict[str, Any]:
    net = Network(task)
    states = net.states(net.factor(net.base), np.asarray(task['loads']))
    return {'status': 'complete', 'states': states.tolist(), 'metrics': {'factorizations': net.factorizations, 'solves': net.solves}}

