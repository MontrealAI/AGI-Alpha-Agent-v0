"""Independent complete numerical acceptance; never trusts solver status alone."""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any

import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve

TOLERANCES = {"state_relative": 1e-7, "balance_backward": 1e-10, "inverse_fit_relative": 1e-7, "inverse_prediction_relative": 1e-5, "identifiability_relative_singular": 1e-8, "design_relative_gap": 5e-5, "design_true_state_relative": 2e-5, "feasibility": 1e-8}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _array(value: Any, shape: tuple[int, ...]) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError("nonfinite or wrong-shape numerical array")
    return result


def _network(task: dict[str, Any], coefficients: np.ndarray | None = None) -> sparse.csr_matrix:
    network = task["network"]
    count = network["node_count"]
    if isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= 4096:
        raise ValueError("node-count scope")
    ground = _array(network["ground"], (count,))
    if np.any(ground < 0):
        raise ValueError("negative ground conductance")
    edges = network["edges"]
    if coefficients is None:
        coefficients = _array([edge[2] for edge in edges], (len(edges),))
    if np.any(coefficients <= 0):
        raise ValueError("nonpositive conductance")
    matrix = sparse.lil_matrix((count, count), dtype=float)
    matrix.setdiag(ground)
    seen = set()
    for index, edge in enumerate(edges):
        if len(edge) != 3:
            raise ValueError("edge arity")
        left, right = edge[0], edge[1]
        if any(isinstance(node, bool) or not isinstance(node, int) or not 0 <= node < count for node in (left, right)) or left == right:
            raise ValueError("edge endpoints")
        key = tuple(sorted((left, right)))
        if key in seen:
            raise ValueError("duplicate edge")
        seen.add(key)
        weight = float(coefficients[index])
        matrix[left, left] += weight
        matrix[right, right] += weight
        matrix[left, right] -= weight
        matrix[right, left] -= weight
    output = matrix.tocsr()
    _, labels = connected_components(output, directed=False)
    for label in np.unique(labels):
        if not np.any(ground[labels == label] > 0):
            raise ValueError("ungrounded connected component")
    return output


def _relative(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.linalg.norm(actual - expected) / max(1.0, float(np.linalg.norm(expected))))


def _solve_rows(operator: sparse.csr_matrix, loads: np.ndarray) -> np.ndarray:
    return np.atleast_2d(np.asarray(spsolve(operator, loads.T)).T)


def _state_checks(operator: sparse.csr_matrix, loads: np.ndarray, reported: Any) -> dict[str, Any]:
    expected = _solve_rows(operator, loads)
    states = _array(reported, expected.shape)
    residual = operator @ states.T - loads.T
    matrix_norm = float(abs(operator).sum(axis=1).max())
    denominator = matrix_norm * float(np.max(np.abs(states))) + float(np.max(np.abs(loads)))
    backward = float(np.max(np.abs(residual)) / max(1.0, denominator))
    relative = _relative(states, expected)
    return {"state_relative_error": relative, "balance_backward_error": backward, "state_ok": relative <= TOLERANCES["state_relative"] and backward <= TOLERANCES["balance_backward"]}


def _inverse_operator(task: dict[str, Any], parameters: np.ndarray) -> sparse.csr_matrix:
    coefficients = np.asarray([edge[2] for edge in task["network"]["edges"]], dtype=float)
    groups = task["parameters"]["groups"]
    seen = set()
    for group, multiplier in zip(groups, parameters):
        if not group or len(set(group)) != len(group) or seen.intersection(group):
            raise ValueError("invalid overlapping parameter groups")
        if any(isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= len(coefficients) for index in group):
            raise ValueError("parameter index scope")
        seen.update(group)
        coefficients[group] *= multiplier
    return _network(task, coefficients)


def _identifiability(task: dict[str, Any], operator: sparse.csr_matrix, states: np.ndarray) -> dict[str, float]:
    count = task["network"]["node_count"]
    sensor_nodes = task["observations"]["nodes"]
    derivatives = []
    for group in task["parameters"]["groups"]:
        force = np.zeros((count, len(states)))
        for edge_index in group:
            left, right, base = task["network"]["edges"][edge_index]
            difference = base * (states[:, left] - states[:, right])
            force[left] -= difference
            force[right] += difference
        derivative = np.atleast_2d(np.asarray(spsolve(operator, force)).T)[:, sensor_nodes].ravel()
        derivatives.append(derivative)
    singular = np.linalg.svd(np.asarray(derivatives).T, compute_uv=False)
    if len(singular) < len(derivatives) or not len(singular) or singular[0] == 0:
        relative = 0.0
    else:
        relative = float(singular[-1] / singular[0])
    return {"jacobian_min_relative_singular": relative}


def _design_certificate(task: dict[str, Any], operator: sparse.csr_matrix, allocation: np.ndarray, loads: np.ndarray) -> dict[str, Any]:
    design = task["design"]
    states = _solve_rows(operator, loads)
    objectives = np.sum(loads * states, axis=1)
    gradients = np.empty((len(loads), len(allocation)))
    for column, edge_index in enumerate(design["edge_indices"]):
        left, right, _ = task["network"]["edges"][edge_index]
        gradients[:, column] = -(states[:, left] - states[:, right]) ** 2
    matrix = np.column_stack((gradients, -np.ones(len(loads))))
    right = -objectives + gradients @ allocation
    matrix = np.vstack((matrix, np.r_[np.asarray(design["costs"]), 0.0]))
    right = np.r_[right, design["resource_budget"]]
    lower_problem = linprog(np.r_[np.zeros(len(allocation)), 1.0], A_ub=matrix, b_ub=right, bounds=[(0.0, float(upper)) for upper in design["upper_bounds"]] + [(0.0, None)], method="highs")
    upper_bound = float(np.max(objectives))
    if not lower_problem.success or lower_problem.fun is None:
        return {"design_certificate_ok": False, "lower_bound_status": str(lower_problem.message), "worst_compliance": upper_bound}
    lower_bound = float(lower_problem.fun)
    gap = max(0.0, upper_bound - lower_bound) / max(1.0, abs(upper_bound))
    return {"design_certificate_ok": math.isfinite(gap) and lower_bound <= upper_bound + 1e-7 * max(1.0, abs(upper_bound)) and gap <= TOLERANCES["design_relative_gap"], "worst_compliance": upper_bound, "supporting_plane_lower_bound": lower_bound, "relative_global_gap": gap, "scenario_compliances": objectives.tolist(), "certificate_scope": "convex-finite-scenario-model-floating-point-numerical-bound"}


def _check_materialization(task: dict[str, Any], oracle: dict[str, Any], parent_task: dict[str, Any] | None, parent_result: dict[str, Any] | None) -> None:
    if parent_task is None or parent_result is None:
        raise ValueError("connected design requires sealed parent task and result")
    materialization = task["lineage"]["materialization"]
    template = deepcopy(task)
    template["network"] = deepcopy(oracle["template_network"])
    del template["lineage"]["materialization"]
    template_hash = hashlib.sha256(_canonical(template)).hexdigest()
    if template_hash != oracle["task_sha256"] or template_hash != materialization["template_sha256"]:
        raise ValueError("design template identity mismatch")
    parent_hash = hashlib.sha256(_canonical(parent_task)).hexdigest()
    if parent_hash != oracle["predecessor_task_sha256"] or parent_hash != materialization["parent_task_sha256"]:
        raise ValueError("inverse task identity mismatch")
    if hashlib.sha256(_canonical(parent_result)).hexdigest() != materialization["parent_result_sha256"]:
        raise ValueError("inverse result identity mismatch")
    if parent_result.get("status") != "complete" or materialization["inherited_parameters"] != parent_result["parameters"]:
        raise ValueError("inherited parameter identity mismatch")
    expected = deepcopy(parent_task["network"])
    for group, multiplier in zip(parent_task["parameters"]["groups"], parent_result["parameters"]):
        for edge_index in group:
            expected["edges"][edge_index][2] *= multiplier
    if expected != task["network"]:
        raise ValueError("design did not consume actual inherited calibration")


def verify(task: dict[str, Any], result: dict[str, Any], oracle: dict[str, Any] | None = None, *, parent_task: dict[str, Any] | None = None, parent_result: dict[str, Any] | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"task_id": task.get("id"), "family": task.get("family"), "accepted": False, "status": "rejected", "tolerances": dict(TOLERANCES)}
    try:
        if task.get("schema") != "agi-alpha-conductance-job/v1":
            raise ValueError("task schema")
        connected_design = task.get("family") == "design" and oracle is not None and "true_calibrated_network" in oracle
        if connected_design:
            _check_materialization(task, oracle, parent_task, parent_result)
        elif oracle is not None and oracle.get("task_sha256") != hashlib.sha256(_canonical(task)).hexdigest():
            raise ValueError("oracle/task identity mismatch")
        baseline = _network(task)
        size = baseline.shape[0]
        loads = np.asarray(task["loads"], dtype=float)
        if loads.ndim != 2 or loads.shape[1] != size or not 1 <= len(loads) <= 16 or not np.isfinite(loads).all():
            raise ValueError("load scope")
        family = task["family"]
        if family == "inverse":
            count = len(task["parameters"]["groups"])
            initial = _array(task["parameters"]["initial"], (count,))
            initial_operator = _inverse_operator(task, initial)
            initial_states = _solve_rows(initial_operator, loads)
            initial_identifiability = _identifiability(task, initial_operator, initial_states)
            if initial_identifiability["jacobian_min_relative_singular"] < TOLERANCES["identifiability_relative_singular"]:
                raise ValueError("insufficient local identifiability")
        if result.get("status") != "complete":
            report["reason"] = "solver did not deliver a complete outcome"
            return report
        if family == "forward":
            report.update(_state_checks(baseline, loads, result["states"]))
            report["accepted"] = report["state_ok"]
        elif family == "inverse":
            values = _array(result["parameters"], (count,))
            bounds = _array(task["parameters"]["bounds"], (count, 2))
            if np.any(values < bounds[:, 0] - TOLERANCES["feasibility"]) or np.any(values > bounds[:, 1] + TOLERANCES["feasibility"]):
                raise ValueError("parameter bound infeasibility")
            operator = _inverse_operator(task, values)
            report.update(_state_checks(operator, loads, result["states"]))
            state = _solve_rows(operator, loads)
            nodes = task["observations"]["nodes"]
            observed = _array(task["observations"]["states"], (len(loads), len(nodes)))
            fit = _relative(state[:, nodes], observed)
            prediction_loads = np.asarray(task["prediction_loads"], dtype=float)
            if prediction_loads.ndim != 2 or prediction_loads.shape[1] != size or not np.isfinite(prediction_loads).all():
                raise ValueError("prediction load scope")
            prediction_checks = _state_checks(operator, prediction_loads, result["prediction_states"])
            report["prediction_state_checks"] = prediction_checks
            if oracle is None:
                raise ValueError("independent inverse prediction reference required")
            predicted = np.asarray(result["prediction_states"], dtype=float)
            true_prediction = _array(oracle["prediction_states"], predicted.shape)
            prediction_error = _relative(predicted, true_prediction)
            report.update(_identifiability(task, operator, state))
            report.update({"fit_relative_error": fit, "prediction_relative_error": prediction_error, "accepted": report["state_ok"] and prediction_checks["state_ok"] and fit <= TOLERANCES["inverse_fit_relative"] and prediction_error <= TOLERANCES["inverse_prediction_relative"] and report["jacobian_min_relative_singular"] >= TOLERANCES["identifiability_relative_singular"]})
        elif family == "design":
            design = task["design"]
            indices = design["edge_indices"]
            if len(set(indices)) != len(indices) or any(isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= len(task["network"]["edges"]) for index in indices):
                raise ValueError("invalid design edge map")
            allocation = _array(result["allocation"], (len(design["edge_indices"]),))
            upper = _array(design["upper_bounds"], allocation.shape)
            costs = _array(design["costs"], allocation.shape)
            budget = float(design["resource_budget"])
            if not math.isfinite(budget) or budget < 0 or np.any(costs <= 0) or np.any(upper < 0):
                raise ValueError("invalid design resource specification")
            allowance = TOLERANCES["feasibility"] * max(1.0, budget)
            if np.any(allocation < -allowance) or np.any(allocation > upper + allowance) or np.dot(costs, allocation) > budget + allowance:
                raise ValueError("allocation infeasibility")
            coefficients = np.asarray([edge[2] for edge in task["network"]["edges"]], dtype=float)
            for edge_index, addition in zip(design["edge_indices"], allocation):
                coefficients[edge_index] += addition
            operator = _network(task, coefficients)
            report.update(_state_checks(operator, loads, result["states"]))
            report["fitted_model_certificate"] = _design_certificate(task, operator, allocation, loads)
            if connected_design:
                true_task = deepcopy(task)
                true_task["network"] = deepcopy(oracle["true_calibrated_network"])
                true_coefficients = np.asarray([edge[2] for edge in true_task["network"]["edges"]], dtype=float)
                for edge_index, addition in zip(design["edge_indices"], allocation):
                    true_coefficients[edge_index] += addition
                true_operator = _network(true_task, true_coefficients)
                true_states = _solve_rows(true_operator, loads)
                true_state_error = _relative(np.asarray(result["states"]), true_states)
                report.update(_design_certificate(true_task, true_operator, allocation, loads))
                report["true_model_state_relative_error"] = true_state_error
                report["inherited_calibration_verified"] = True
            else:
                true_state_error = 0.0
                report.update(report["fitted_model_certificate"])
            report["resource_used"] = float(np.dot(costs, allocation))
            report["accepted"] = report["state_ok"] and report["design_certificate_ok"] and report["fitted_model_certificate"]["design_certificate_ok"] and true_state_error <= TOLERANCES["design_true_state_relative"]
        else:
            raise ValueError("unsupported task family")
        report["status"] = "accepted" if report["accepted"] else "rejected"
        return report
    except (ValueError, KeyError, TypeError, IndexError, np.linalg.LinAlgError) as error:
        report["reason"] = str(error)
        return report
