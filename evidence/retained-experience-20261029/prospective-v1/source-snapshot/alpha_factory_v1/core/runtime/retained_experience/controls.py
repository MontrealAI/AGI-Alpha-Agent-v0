# SPDX-License-Identifier: Apache-2.0
"""Conventional controls with the same historical LP inputs as the treatment."""

from __future__ import annotations

from typing import Any

import numpy as np
import scipy
from scipy.sparse import csr_matrix

from .solver import arrays, primal_artifact, signature, solve


class WarmStart:
    """Freeze ordinary HiGHS bases; restore them before EACH fresh observation.

    This research adapter uses the bundled HiGHS API in the existing SciPy 1.17
    dependency. Other versions refuse instead of silently omitting this control.
    """

    def __init__(self, history: list[dict[str, Any]]) -> None:
        if not scipy.__version__.startswith("1.17."):
            raise ValueError("warm-start control requires the declared SciPy 1.17 research profile")
        from scipy.optimize._highspy import _core

        self.core: Any = _core
        self.sessions: dict[str, Any] = {}
        for record in history:
            from ..structural_transfer.eadarp import compile_model

            for item in compile_model(record["target"])["vehicles"]:
                matrix, rhs, objective = arrays(item)
                sparse = csr_matrix(matrix)
                lp = _core.HighsLp()
                lp.num_col_, lp.num_row_ = matrix.shape[1], matrix.shape[0]
                lp.col_cost_ = objective
                lp.col_lower_ = np.full(len(objective), -np.inf)
                lp.col_upper_ = np.full(len(objective), np.inf)
                lp.row_lower_ = np.full(len(rhs), -np.inf)
                lp.row_upper_ = rhs
                lp.a_matrix_.format_ = _core.MatrixFormat.kRowwise
                lp.a_matrix_.start_, lp.a_matrix_.index_, lp.a_matrix_.value_ = (
                    sparse.indptr,
                    sparse.indices,
                    sparse.data,
                )
                native = _core._Highs()
                native.setOptionValue("output_flag", False)
                native.setOptionValue("time_limit", 10.0)
                native.setOptionValue("solver", "simplex")
                if native.passModel(lp) != _core.HighsStatus.kOk or native.run() != _core.HighsStatus.kOk:
                    raise ValueError("conventional HiGHS setup failed")
                if native.getModelStatus() == _core.HighsModelStatus.kOptimal:
                    self.sessions[signature(item)] = (native, native.getBasis())

    def run(self, target: dict[str, Any], model: dict[str, Any], method: str, presolve: bool) -> dict[str, Any]:
        """Permit conventional re-optimization but no evaluation-to-evaluation learning."""
        points, duals, calls = [], [], 0
        for item in model["vehicles"]:
            retained = self.sessions.get(signature(item))
            if retained is None:
                return {**solve(target, model, method, presolve), "warm_calls_discarded": calls}
            native, basis = retained
            for index, row in enumerate(item["rows"]):
                if native.changeRowBounds(index, -np.inf, float(row["rhs"])) != self.core.HighsStatus.kOk:
                    raise ValueError("conventional bound update failed")
            if native.setBasis(basis) != self.core.HighsStatus.kOk:
                raise ValueError("conventional basis restore failed")
            calls += 1
            if native.run() != self.core.HighsStatus.kOk:
                raise ValueError("conventional warm solve failed")
            if native.getModelStatus() != self.core.HighsModelStatus.kOptimal:
                return {**solve(target, model, method, presolve), "warm_calls_discarded": calls}
            result = native.getSolution()
            points.append(np.array(result.col_value))
            duals.append(
                {
                    row["name"]: format(float(y), ".15g")
                    for row, y in zip(item["rows"], result.row_dual)
                    if abs(y) > 1e-12
                }
            )
        return {"artifact": primal_artifact(target, model, points), "duals": duals, "solver_calls": calls, "reuse": []}
