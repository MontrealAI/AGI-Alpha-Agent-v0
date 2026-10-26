# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import time
from typing import Any

import numpy as np
from scipy import sparse
from scipy.optimize import least_squares, linprog, minimize
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu


class Network:
    def __init__(self, task: dict[str, Any]) -> None:
        network = task["network"]
        self.n = network["node_count"]
        if isinstance(self.n, bool) or not isinstance(self.n, int) or not 2 <= self.n <= 2500:
            raise ValueError("unsupported network size")
        edges = np.asarray(network["edges"], dtype=float)
        if edges.ndim != 2 or edges.shape[1] != 3 or not np.isfinite(edges).all():
            raise ValueError("invalid edge array")
        self.left, self.right = edges[:, 0].astype(int), edges[:, 1].astype(int)
        if not np.array_equal(edges[:, :2], np.column_stack((self.left, self.right))):
            raise ValueError("noninteger endpoints")
        if np.any(self.left == self.right) or np.any(edges[:, :2] < 0) or np.any(edges[:, :2] >= self.n):
            raise ValueError("invalid edge endpoints")
        pairs = np.sort(np.column_stack((self.left, self.right)), axis=1)
        if len(np.unique(pairs, axis=0)) != len(pairs):
            raise ValueError("duplicate edge")
        self.base = edges[:, 2]
        self.ground = np.asarray(network["ground"], dtype=float)
        if self.ground.shape != (self.n,) or not np.isfinite(self.ground).all() or np.any(self.ground < 0):
            raise ValueError("invalid grounded boundary")
        if np.any(self.base <= 0):
            raise ValueError("nonpositive base conductance")
        self.rows = np.r_[self.left, self.left, self.right, self.right, np.arange(self.n)]
        self.cols = np.r_[self.left, self.right, self.left, self.right, np.arange(self.n)]
        adjacency = sparse.coo_matrix((np.ones(len(self.left)), (self.left, self.right)), shape=(self.n, self.n))
        _, labels = connected_components(adjacency, directed=False)
        for label in np.unique(labels):
            if not np.any(self.ground[labels == label] > 0):
                raise ValueError("ungrounded component")
        self.factorizations = 0
        self.solves = 0

    def matrix(self, weights: np.ndarray) -> sparse.csc_matrix:
        if weights.shape != self.base.shape or not np.isfinite(weights).all() or np.any(weights <= 0):
            raise ValueError("invalid effective conductance")
        values = np.r_[weights, -weights, -weights, weights, self.ground]
        return sparse.coo_matrix((values, (self.rows, self.cols)), shape=(self.n, self.n)).tocsc()

    def factor(self, weights: np.ndarray) -> Any:
        self.factorizations += 1
        return splu(self.matrix(weights))

    def states(self, factor: Any, loads: np.ndarray) -> np.ndarray:
        self.solves += loads.shape[0]
        return factor.solve(np.asfortranarray(loads.T)).T

    def derivative_matrix(self, indices: np.ndarray) -> sparse.csc_matrix:
        left, right, weights = self.left[indices], self.right[indices], self.base[indices]
        return sparse.coo_matrix((np.r_[weights, -weights, -weights, weights],
                                  (np.r_[left, left, right, right], np.r_[left, right, left, right])),
                                 shape=(self.n, self.n)).tocsc()


def solve(task: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()

    def bounded() -> None:
        if time.monotonic() - started > 170:
            raise TimeoutError("fixed 170-second solver budget")

    try:
        if task.get("schema") != "agi-alpha-conductance-job/v1":
            raise ValueError("unsupported schema")
        network = Network(task)
        loads = np.asarray(task["loads"], dtype=float)
        if loads.ndim != 2 or loads.shape[1] != network.n or not 1 <= len(loads) <= 16 or not np.isfinite(loads).all():
            raise ValueError("invalid load array")
        family = task["family"]
        if family == "forward":
            states = network.states(network.factor(network.base), loads)
            result = {"status": "complete", "states": states.tolist()}
        elif family == "inverse":
            result = inverse(task, network, loads, bounded)
        elif family == "design":
            result = design(task, network, loads, bounded)
        else:
            raise ValueError("unsupported family")
        result["resource_counts"] = {"factorizations": network.factorizations, "linear_rhs_solves": network.solves}
        if result.get("status") == "complete":
            for field in ["states", "parameters", "prediction_states", "allocation"]:
                if field in result and not np.isfinite(np.asarray(result[field])).all():
                    raise ValueError("nonfinite numerical result")
        return result
    except (ValueError, KeyError, TypeError, RuntimeError, np.linalg.LinAlgError, TimeoutError) as error:
        return {"status": "refused", "reason": str(error)}


def inverse(task: dict[str, Any], network: Network, loads: np.ndarray, bounded: Any) -> dict[str, Any]:
    specification = task["parameters"]
    groups = [np.asarray(group, dtype=int) for group in specification["groups"]]
    p = len(groups)
    if not 1 <= p <= 32:
        raise ValueError("unsupported parameter count")
    used: set[int] = set()
    for group in groups:
        if not len(group) or len(np.unique(group)) != len(group) or np.any(group < 0) or np.any(group >= len(network.base)):
            raise ValueError("invalid parameter group")
        if used.intersection(group):
            raise ValueError("overlapping parameter group")
        used.update(group.tolist())
    bounds = np.asarray(specification["bounds"], dtype=float)
    initial = np.asarray(specification["initial"], dtype=float)
    if bounds.shape != (p, 2) or initial.shape != (p,) or not np.isfinite(bounds).all():
        raise ValueError("invalid parameter bounds")
    if np.any(bounds[:, 0] <= 0) or np.any(bounds[:, 0] >= bounds[:, 1]):
        raise ValueError("unsupported parameter domain")
    nodes = np.asarray(task["observations"]["nodes"], dtype=int)
    observed = np.asarray(task["observations"]["states"], dtype=float)
    if observed.shape != (len(loads), len(nodes)) or not np.isfinite(observed).all():
        raise ValueError("invalid observations")
    if len(np.unique(nodes)) != len(nodes) or np.any(nodes < 0) or np.any(nodes >= network.n):
        raise ValueError("invalid observation nodes")
    derivatives = [network.derivative_matrix(group) for group in groups]
    cache: dict[str, Any] = {}

    def evaluate(parameters: np.ndarray, jacobian: bool = False) -> dict[str, Any]:
        bounded()
        if "parameters" not in cache or not np.array_equal(parameters, cache["parameters"]):
            weights = network.base.copy()
            for group, multiplier in zip(groups, parameters):
                weights[group] *= multiplier
            factor = network.factor(weights)
            states = network.states(factor, loads)
            cache.clear()
            cache.update(parameters=parameters.copy(), factor=factor, states=states,
                         residual=(states[:, nodes] - observed).ravel())
        if jacobian and "jacobian" not in cache:
            columns = []
            for derivative in derivatives:
                bounded()
                sensitivity = network.states(cache["factor"], np.asarray(-(derivative @ cache["states"].T)).T)
                columns.append(sensitivity[:, nodes].ravel())
            cache["jacobian"] = np.column_stack(columns)
        return cache

    initial = np.clip(initial, bounds[:, 0], bounds[:, 1])
    initial_jacobian = evaluate(initial, True)["jacobian"]
    singular = np.linalg.svd(initial_jacobian, compute_uv=False)
    if len(singular) < p or singular[-1] <= 1e-8 * max(singular[0], np.finfo(float).tiny):
        raise ValueError("insufficient local identifiability")
    trials = []
    candidate = initial
    normalizer = max(1.0, float(np.linalg.norm(observed)))
    for start in [initial, bounds.mean(axis=1)]:
        optimization = least_squares(lambda values: evaluate(values)["residual"], start,
                                     jac=lambda values: evaluate(values, True)["jacobian"],
                                     bounds=(bounds[:, 0], bounds[:, 1]), method="trf", x_scale="jac",
                                     ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=150)
        error = float(np.linalg.norm(evaluate(optimization.x)["residual"]) / normalizer)
        trials.append({"success": bool(optimization.success), "nfev": int(optimization.nfev), "fit_relative": error})
        candidate = optimization.x.copy()
        if error <= 1e-9:
            break
    final = evaluate(candidate)
    prediction_loads = np.asarray(task["prediction_loads"], dtype=float)
    if prediction_loads.ndim != 2 or prediction_loads.shape[1] != network.n or not np.isfinite(prediction_loads).all():
        raise ValueError("invalid prediction loads")
    predictions = network.states(final["factor"], prediction_loads)
    return {"status": "complete", "parameters": candidate.tolist(), "states": final["states"].tolist(),
            "prediction_states": predictions.tolist(), "optimizer_trials": trials}


def design(task: dict[str, Any], network: Network, loads: np.ndarray, bounded: Any) -> dict[str, Any]:
    specification = task["design"]
    indices = np.asarray(specification["edge_indices"], dtype=int)
    upper = np.asarray(specification["upper_bounds"], dtype=float)
    costs = np.asarray(specification["costs"], dtype=float)
    budget = float(specification["resource_budget"])
    m = len(indices)
    if not 1 <= m <= 80 or len(np.unique(indices)) != m or np.any(indices < 0) or np.any(indices >= len(network.base)):
        raise ValueError("invalid design edges")
    if upper.shape != (m,) or costs.shape != (m,) or not np.isfinite(upper).all() or not np.isfinite(costs).all():
        raise ValueError("invalid design limits")
    if not np.isfinite(budget) or budget < 0 or np.any(upper < 0) or np.any(costs <= 0):
        raise ValueError("invalid resource specification")
    cache: dict[str, Any] = {}

    def evaluate(allocation: np.ndarray) -> dict[str, Any]:
        bounded()
        if "allocation" not in cache or not np.array_equal(allocation, cache["allocation"]):
            weights = network.base.copy()
            weights[indices] += allocation
            states = network.states(network.factor(weights), loads)
            values = np.einsum("ij,ij->i", loads, states)
            delta = states[:, network.left[indices]] - states[:, network.right[indices]]
            cache.clear()
            cache.update(allocation=allocation.copy(), states=states, values=values, gradients=-delta**2)
        return cache

    reference = max(1.0, float(np.max(evaluate(np.zeros(m))["values"])))
    costscale = max(1.0, budget)
    normalized_costs = costs * upper / costscale
    initial_fraction = min(1.0, budget / max(float(costs @ upper), np.finfo(float).tiny))
    initial = np.full(m, initial_fraction)
    initial_value = float(np.max(evaluate(initial * upper)["values"])) / reference
    start = np.r_[initial, initial_value]

    def inequalities(values: np.ndarray) -> np.ndarray:
        state = evaluate(values[:-1] * upper)
        return np.r_[budget / costscale - normalized_costs @ values[:-1], values[-1] - state["values"] / reference]

    def jacobian(values: np.ndarray) -> np.ndarray:
        state = evaluate(values[:-1] * upper)
        return np.row_stack((np.r_[-normalized_costs, 0.0],
                             np.column_stack((-state["gradients"] * upper[None, :] / reference, np.ones(len(loads))))))

    trials = []
    allocation = initial * upper
    for iteration in range(2):
        if budget == 0 or initial_fraction == 1:
            break
        optimization = minimize(lambda values: values[-1], start, jac=lambda values: np.r_[np.zeros(m), 1.0],
                                method="SLSQP", bounds=[(0.0, 1.0)] * m + [(0.0, None)],
                                constraints=[{"type": "ineq", "fun": inequalities, "jac": jacobian}],
                                options={"ftol": 1e-12, "maxiter": 500, "disp": False})
        allocation = np.clip(optimization.x[:-1], 0.0, 1.0) * upper
        spent = float(costs @ allocation)
        if spent > budget:
            allocation *= budget / spent
        state = evaluate(allocation)
        gradients = state["gradients"]
        matrix = np.row_stack((np.column_stack((gradients, -np.ones(len(loads)))), np.r_[costs, 0.0]))
        right = np.r_[-state["values"] + gradients @ allocation, budget]
        bound = linprog(np.r_[np.zeros(m), 1.0], A_ub=matrix, b_ub=right,
                        bounds=[(0.0, float(value)) for value in upper] + [(0.0, None)], method="highs")
        high = float(np.max(state["values"]))
        gap = float(max(0.0, high - bound.fun) / max(1.0, high)) if bound.success else None
        trials.append({"iteration": iteration, "success": bool(optimization.success), "iterations": int(optimization.nit),
                       "relative_bound_gap": gap, "message": str(optimization.message)})
        if gap is not None and gap < 1e-6:
            break
        start = np.r_[np.divide(allocation, upper, out=np.zeros_like(allocation), where=upper > 0), high / reference]
    state = evaluate(allocation)
    return {"status": "complete", "allocation": allocation.tolist(), "states": state["states"].tolist(),
            "optimizer_trials": trials}
