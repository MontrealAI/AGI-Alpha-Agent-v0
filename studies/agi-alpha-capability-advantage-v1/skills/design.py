from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

from core import Network


def solve_design(task: dict[str, Any]) -> dict[str, Any]:
    net = Network(task)
    design = task['design']
    edges = np.asarray(design['edge_indices'], dtype=int)
    upper = np.asarray(design['upper_bounds'], dtype=float)
    costs = np.asarray(design['costs'], dtype=float)
    budget = float(design['resource_budget'])
    loads = np.asarray(task['loads'], dtype=float)
    if len(np.unique(edges)) != len(edges) or np.any(costs <= 0) or np.any(upper < 0) or budget < 0:
        raise ValueError('INVALID_DESIGN')
    cached: dict[str, Any] = {}

    def evaluate(x: np.ndarray) -> dict[str, Any]:
        if 'x' in cached and np.array_equal(cached['x'], x):
            return cached
        conductance = net.base.copy()
        conductance[edges] += x
        states = net.states(net.factor(conductance), loads)
        compliance = np.sum(loads * states, axis=1)
        differences = states[:, net.a[edges]] - states[:, net.b[edges]]
        cached.clear()
        cached.update(x=x.copy(), states=states, compliance=compliance, gradients=-(differences ** 2))
        return cached

    initial = np.minimum(upper / 2, budget / max(1, len(edges)) / costs)
    scale = max(float(evaluate(np.zeros(len(edges)))['compliance'].max()), 1e-10)
    x0 = np.r_[initial, evaluate(initial)['compliance'].max() / scale]

    def scenario_constraint(z: np.ndarray) -> np.ndarray:
        return z[-1] - evaluate(z[:-1])['compliance'] / scale

    def scenario_jacobian(z: np.ndarray) -> np.ndarray:
        return np.c_[-evaluate(z[:-1])['gradients'] / scale, np.ones(loads.shape[0])]

    result = minimize(lambda z: z[-1], x0, jac=lambda z: np.r_[np.zeros(len(edges)), 1.0], method='SLSQP',
                      bounds=list(zip(np.zeros(len(edges)), upper)) + [(0.0, None)],
                      constraints=[{'type': 'ineq', 'fun': scenario_constraint, 'jac': scenario_jacobian},
                                   {'type': 'ineq', 'fun': lambda z: (budget - costs @ z[:-1]) / max(budget, 1),
                                    'jac': lambda z: np.r_[-costs / max(budget, 1), 0.0]}],
                      options={'ftol': 1e-11, 'maxiter': 500})
    final = evaluate(result.x[:-1])
    return {'status': 'complete', 'allocation': result.x[:-1].tolist(), 'states': final['states'].tolist(),
            'solver_success': bool(result.success), 'metrics': {'factorizations': net.factorizations, 'solves': net.solves,
                                                               'iterations': int(result.nit), 'worst_compliance': float(final['compliance'].max())}}

