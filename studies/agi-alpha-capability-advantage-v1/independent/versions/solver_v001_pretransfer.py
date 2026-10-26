"""Independent conductance solver, constructed without transferred task skills.

The public interface is solve(task) -> JSON-serializable outcome.
All optimizations are based solely on the supplied task; no oracle is read.
"""
from __future__ import annotations

import time
from contextlib import nullcontext

import numpy as np
from scipy import sparse
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import least_squares, linprog, minimize
from scipy.sparse.linalg import splu

try:
    from threadpoolctl import threadpool_limits
except ImportError:  # Optional performance guard, not a numerical dependency.
    threadpool_limits = None


class Deadline(Exception):
    pass


def _factor(operator):
    return splu(operator.tocsc(), permc_spec="MMD_AT_PLUS_A",
                diag_pivot_thresh=0.0, options={"SymmetricMode": True})


class Network:
    def __init__(self, task):
        self.n = int(task["network"]["node_count"])
        edges = np.asarray(task["network"]["edges"], dtype=float)
        self.u = edges[:, 0].astype(np.int64)
        self.v = edges[:, 1].astype(np.int64)
        self.base = edges[:, 2]
        self.ground = np.asarray(task["network"]["ground"], dtype=float)
        self.loads = np.asarray(task["loads"], dtype=float).T
        self.rows = np.r_[self.u, self.v, self.u, self.v, np.arange(self.n)]
        self.cols = np.r_[self.u, self.v, self.v, self.u, np.arange(self.n)]

    def matrix(self, coefficients=None):
        c = self.base if coefficients is None else coefficients
        values = np.r_[c, c, -c, -c, self.ground]
        return sparse.coo_matrix((values, (self.rows, self.cols)),
                                 shape=(self.n, self.n)).tocsc()

    def group_matrix(self, indices):
        u, v, c = self.u[indices], self.v[indices], self.base[indices]
        return sparse.coo_matrix((np.r_[c, c, -c, -c],
                                  (np.r_[u, v, u, v], np.r_[u, v, v, u])),
                                 shape=(self.n, self.n)).tocsr()


def _inverse(task, net, deadline):
    specification = task["parameters"]
    groups = [np.asarray(g, dtype=np.int64) for g in specification["groups"]]
    matrices = [net.group_matrix(g) for g in groups]
    sensors = np.asarray(task["observations"]["nodes"], dtype=np.int64)
    observed = np.asarray(task["observations"]["states"], dtype=float)
    bounds = np.asarray(specification["bounds"], dtype=float)
    p = len(groups)
    count = net.loads.shape[1]
    cached = {}
    evaluations = 0
    jacobians = 0

    def evaluate(parameters):
        nonlocal evaluations
        if "parameters" not in cached or not np.array_equal(parameters, cached["parameters"]):
            if time.perf_counter() >= deadline:
                raise Deadline("inverse reconstruction exceeded internal time budget")
            coefficients = net.base.copy()
            for group, value in zip(groups, parameters):
                coefficients[group] *= value
            factor = _factor(net.matrix(coefficients))
            states = factor.solve(net.loads)
            cached.clear()
            cached.update(parameters=np.array(parameters, copy=True),
                          factor=factor, states=states,
                          residual=(states[sensors, :].T-observed).ravel())
            evaluations += 1
        return cached

    def residual(parameters):
        return evaluate(parameters)["residual"]

    def jacobian(parameters):
        nonlocal jacobians
        current = evaluate(parameters)
        if "jacobian" not in current:
            forces = np.empty((net.n, p * count), dtype=float, order="F")
            for column, matrix in enumerate(matrices):
                forces[:, column*count:(column+1)*count] = -(matrix @ current["states"])
            sensitivities = current["factor"].solve(forces)
            derivative = np.empty((len(sensors)*count, p), dtype=float)
            for column in range(p):
                derivative[:, column] = sensitivities[sensors, column*count:(column+1)*count].T.ravel()
            current["jacobian"] = derivative
            jacobians += 1
        return current["jacobian"]

    initial = np.clip(np.asarray(specification["initial"], dtype=float), bounds[:, 0], bounds[:, 1])
    fit = least_squares(residual, initial, jac=jacobian,
                        bounds=(bounds[:, 0], bounds[:, 1]), method="trf",
                        x_scale="jac", ftol=1e-12, xtol=1e-12, gtol=1e-12,
                        max_nfev=120)
    current = evaluate(fit.x)
    fit_relative = float(np.linalg.norm(current["residual"])/max(1.0, np.linalg.norm(observed)))
    if fit_relative > 3e-8:
        return {"status": "failed", "reason": "inverse fit did not reach required accuracy",
                "fit_relative_error": fit_relative, "optimizer_status": str(fit.message)}
    prediction = current["factor"].solve(np.asarray(task["prediction_loads"], dtype=float).T)
    return {"status": "complete", "parameters": fit.x.tolist(),
            "states": current["states"].T.tolist(), "prediction_states": prediction.T.tolist(),
            "diagnostics": {"factorizations": evaluations, "jacobian_evaluations": jacobians,
                            "fit_relative_error": fit_relative, "optimizer_status": str(fit.message)}}


def _design(task, net, deadline):
    specification = task["design"]
    selected = np.asarray(specification["edge_indices"], dtype=np.int64)
    upper = np.asarray(specification["upper_bounds"], dtype=float)
    costs = np.asarray(specification["costs"], dtype=float)
    budget = float(specification["resource_budget"])
    m = len(selected)
    factor = _factor(net.matrix())
    incidence = np.zeros((net.n, m), dtype=float, order="F")
    incidence[net.u[selected], np.arange(m)] = 1.0
    incidence[net.v[selected], np.arange(m)] = -1.0
    solved = factor.solve(np.column_stack((net.loads, incidence)))
    load_count = net.loads.shape[1]
    baseline = solved[:, :load_count]
    response = solved[:, load_count:]
    kernel = response[net.u[selected], :] - response[net.v[selected], :]
    kernel = 0.5*(kernel+kernel.T)
    differences = baseline[net.u[selected], :] - baseline[net.v[selected], :]
    initial_objectives = np.sum(net.loads*baseline, axis=0)
    cached = {}
    evaluations = 0

    def evaluate(allocation):
        nonlocal evaluations
        if "allocation" not in cached or not np.array_equal(allocation, cached["allocation"]):
            if time.perf_counter() >= deadline:
                raise Deadline("design optimization exceeded internal time budget")
            allocation = np.maximum(allocation, 0.0)
            root = np.sqrt(allocation)
            small = np.eye(m) + root[:, None]*kernel*root[None, :]
            multiplier = root[:, None]*cho_solve(cho_factor(small, lower=True, check_finite=False),
                                                 root[:, None]*differences, check_finite=False)
            updated_differences = differences-kernel@multiplier
            objectives = initial_objectives-np.sum(differences*multiplier, axis=0)
            gradients = -(updated_differences.T**2)
            cached.clear()
            cached.update(allocation=np.array(allocation, copy=True), objectives=objectives,
                          gradients=gradients, multiplier=multiplier)
            evaluations += 1
        return cached

    def feasible(allocation):
        output = np.clip(allocation, 0.0, upper)
        used = float(costs@output)
        if used > budget and used > 0:
            output *= max(0.0, budget)/used
        return output

    def certificate(allocation):
        current = evaluate(allocation)
        objective, gradient = current["objectives"], current["gradients"]
        rhs = np.r_[-objective+gradient@allocation, budget]
        matrix = np.vstack((np.column_stack((gradient, -np.ones(load_count))), np.r_[costs, 0.0]))
        lower = linprog(np.r_[np.zeros(m), 1.0], A_ub=matrix, b_ub=rhs,
                        bounds=[(0.0, float(value)) for value in upper]+[(0.0, None)],
                        method="highs")
        if not lower.success:
            return float("inf"), None
        gap = max(0.0, float(np.max(objective)-lower.fun))/max(1.0, float(np.max(objective)))
        return gap, lower.x[:m]

    allocation = feasible(upper * min(1.0, budget/max(float(costs@upper), 1e-300)))
    if budget > 0 and np.any(upper > 0):
        # A scenario that is below the box-wide lower bound even at zero
        # cannot be the maximum anywhere in the feasible box.
        box_lower = float(np.max(evaluate(upper)["objectives"]))
        active = np.flatnonzero(initial_objectives >= box_lower-1e-10*max(1.0, abs(box_lower)))
        gradient_at_zero = differences.T**2
        scale = max(1.0, float(np.max(gradient_at_zero@upper)))
        offset = float(np.min(initial_objectives[active]))
        resource_scale = max(1.0, budget)
        if len(active) == 1:
            scenario = int(active[0])
            def value(x):
                return float((evaluate(x)["objectives"][scenario]-offset)/scale)
            def gradient(x):
                return evaluate(x)["gradients"][scenario]/scale
            constraint = {"type": "ineq", "fun": lambda x: (budget-costs@x)/resource_scale,
                          "jac": lambda x: -costs/resource_scale}
            optimum = minimize(value, allocation, jac=gradient, method="SLSQP",
                               bounds=list(zip(np.zeros(m), upper)), constraints=[constraint],
                               options={"ftol": 1e-12, "maxiter": 600})
            allocation = feasible(optimum.x)
        else:
            def inequalities(z):
                return z[-1]-(evaluate(z[:-1])["objectives"][active]-offset)/scale
            def inequalities_jacobian(z):
                return np.column_stack((-evaluate(z[:-1])["gradients"][active]/scale,
                                        np.ones(len(active))))
            constraints = [{"type": "ineq", "fun": inequalities, "jac": inequalities_jacobian},
                           {"type": "ineq", "fun": lambda z: (budget-costs@z[:-1])/resource_scale,
                            "jac": lambda z: np.r_[-costs/resource_scale, 0.0]}]
            z0 = np.r_[allocation, np.max((evaluate(allocation)["objectives"][active]-offset)/scale)]
            optimum = minimize(lambda z: z[-1], z0, jac=lambda z: np.r_[np.zeros(m), 1.0],
                               method="SLSQP", bounds=list(zip(np.zeros(m), upper))+[(None, None)],
                               constraints=constraints, options={"ftol": 1e-12, "maxiter": 600})
            allocation = feasible(optimum.x[:-1])
    else:
        active = np.arange(load_count)

    gap, toward = certificate(allocation)
    # A direct supporting-plane check protects against premature SLSQP stops.
    # Conditional-gradient refinement uses the same feasible LP minimizer.
    refinements = 0
    while gap > 1e-5 and toward is not None and refinements < 150:
        from scipy.optimize import minimize_scalar
        direction = toward-allocation
        start_objective = float(np.max(evaluate(allocation)["objectives"]))
        search = minimize_scalar(lambda step: float(np.max(evaluate(allocation+step*direction)["objectives"])),
                                 bounds=(0.0, 1.0), method="bounded", options={"xatol": 1e-12})
        if search.fun >= start_objective-1e-13*max(1.0, abs(start_objective)):
            break
        allocation = feasible(allocation+float(search.x)*direction)
        gap, toward = certificate(allocation)
        refinements += 1
    current = evaluate(allocation)
    # Reconstruct states using the exact low-rank identity, then one residual
    # correction with the final sparse operator if needed for backward stability.
    states = baseline-response@current["multiplier"]
    coefficients = net.base.copy()
    coefficients[selected] += allocation
    operator = net.matrix(coefficients)
    residual = net.loads-operator@states
    denominator = max(1.0, float(abs(operator).sum(axis=1).max())*float(np.max(np.abs(states)))+
                      float(np.max(np.abs(net.loads))))
    if float(np.max(np.abs(residual)))/denominator > 1e-12:
        states += _factor(operator).solve(residual)
    return {"status": "complete", "allocation": allocation.tolist(), "states": states.T.tolist(),
            "diagnostics": {"reduced_evaluations": evaluations, "active_scenarios": active.tolist(),
                            "relative_supporting_plane_gap": gap, "refinement_steps": refinements}}


def solve(task):
    """Deliver forward states, inverse calibration, or resource-limited design."""
    started = time.perf_counter()
    limit = 43.0
    try:
        with (threadpool_limits(limits=1) if threadpool_limits is not None else nullcontext()):
            network = Network(task)
            if task["family"] == "forward":
                states = _factor(network.matrix()).solve(network.loads)
                result = {"status": "complete", "states": states.T.tolist()}
            elif task["family"] == "inverse":
                result = _inverse(task, network, started+limit)
            elif task["family"] == "design":
                result = _design(task, network, started+limit)
            else:
                return {"status": "failed", "reason": "unsupported task family"}
            result.setdefault("diagnostics", {})["solver_elapsed_seconds"] = time.perf_counter()-started
            return result
    except Deadline as error:
        return {"status": "timeout", "reason": str(error),
                "solver_elapsed_seconds": time.perf_counter()-started}

