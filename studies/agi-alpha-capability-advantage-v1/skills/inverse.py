from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import least_squares

from core import Network


def solve_inverse(task: dict[str, Any]) -> dict[str, Any]:
    net = Network(task)
    groups = [np.asarray(g, dtype=int) for g in task['parameters']['groups']]
    bounds = np.asarray(task['parameters']['bounds'], dtype=float)
    initial = np.asarray(task['parameters']['initial'], dtype=float)
    if len(np.unique(np.concatenate(groups))) != sum(len(g) for g in groups):
        raise ValueError('OVERLAPPING_PARAMETER_GROUPS')
    loads = np.asarray(task['loads'], dtype=float)
    sensors = np.asarray(task['observations']['nodes'], dtype=int)
    observations = np.asarray(task['observations']['states'], dtype=float)
    scale = max(float(np.linalg.norm(observations)) / np.sqrt(observations.size), 1e-8)
    cached: dict[str, Any] = {}

    def evaluate(theta: np.ndarray) -> dict[str, Any]:
        if 'theta' in cached and np.array_equal(theta, cached['theta']):
            return cached
        conductance = net.base.copy()
        for j, edges in enumerate(groups):
            conductance[edges] *= theta[j]
        factor = net.factor(conductance)
        states = net.states(factor, loads)
        adjoint = factor.solve(np.eye(net.n)[:, sensors])
        net.solves += 1
        state_diff = states[:, net.a] - states[:, net.b]
        adjoint_diff = adjoint[net.a, :] - adjoint[net.b, :]
        jac = np.empty((loads.shape[0], len(sensors), len(groups)))
        for j, edges in enumerate(groups):
            jac[:, :, j] = -(state_diff[:, edges] * net.base[edges]) @ adjoint_diff[edges, :]
        cached.clear()
        cached.update(theta=theta.copy(), factor=factor, states=states, residual=(states[:, sensors] - observations).ravel() / scale,
                      jac=jac.reshape(-1, len(groups)) / scale)
        return cached

    initial_jac = evaluate(initial)['jac']
    singular_values = np.linalg.svd(initial_jac, compute_uv=False)
    if len(singular_values) < len(groups) or singular_values[-1] <= max(singular_values[0], 1) * 1e-10:
        return {'status': 'refused', 'reason': 'NONIDENTIFIABLE_PARAMETERS'}
    result = least_squares(lambda x: evaluate(x)['residual'], initial, jac=lambda x: evaluate(x)['jac'],
                           bounds=(bounds[:, 0], bounds[:, 1]), ftol=1e-11, xtol=1e-11, gtol=1e-11,
                           x_scale='jac', max_nfev=250)
    final = evaluate(result.x)
    predictions = net.states(final['factor'], np.asarray(task['prediction_loads'], dtype=float))
    return {'status': 'complete', 'parameters': result.x.tolist(), 'states': final['states'].tolist(),
            'prediction_states': predictions.tolist(), 'solver_success': bool(result.success),
            'metrics': {'factorizations': net.factorizations, 'solves': net.solves,
                        'residual_norm': float(np.linalg.norm(final['residual'])), 'evaluations': int(result.nfev)}}

