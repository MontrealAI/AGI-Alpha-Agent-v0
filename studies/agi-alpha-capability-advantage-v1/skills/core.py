from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu


class Network:
    def __init__(self, task: dict[str, Any]) -> None:
        data = task['network']
        self.n = int(data['node_count'])
        edges = np.asarray(data['edges'], dtype=float)
        self.a, self.b = edges[:, 0].astype(int), edges[:, 1].astype(int)
        self.base = edges[:, 2]
        self.ground = np.asarray(data['ground'], dtype=float)
        if self.n < 2 or edges.ndim != 2 or edges.shape[1] != 3:
            raise ValueError('INVALID_NETWORK')
        if not np.all(np.isfinite(edges)) or not np.all(np.isfinite(self.ground)):
            raise ValueError('NONFINITE_NETWORK')
        if self.ground.shape != (self.n,) or np.any(self.ground < 0) or np.any(self.base <= 0):
            raise ValueError('INVALID_CONDUCTANCE')
        if np.any(self.a != edges[:, 0]) or np.any(self.b != edges[:, 1]):
            raise ValueError('NONINTEGER_NODE')
        if min(self.a.min(), self.b.min()) < 0 or max(self.a.max(), self.b.max()) >= self.n or np.any(self.a == self.b):
            raise ValueError('INVALID_EDGE')
        graph = sparse.coo_matrix((np.ones(len(self.a)), (self.a, self.b)), shape=(self.n, self.n))
        count, component = connected_components(graph, directed=False)
        if any(float(self.ground[component == k].sum()) <= 0 for k in range(count)):
            raise ValueError('UNGROUNDED_COMPONENT')
        idx = np.arange(len(self.a))
        self.incidence = sparse.csc_matrix((np.r_[np.ones(len(idx)), -np.ones(len(idx))],
                                           (np.r_[idx, idx], np.r_[self.a, self.b])), shape=(len(idx), self.n))
        self.factorizations = 0
        self.solves = 0

    def factor(self, conductance: np.ndarray) -> Any:
        self.factorizations += 1
        return splu((self.incidence.T @ sparse.diags(conductance) @ self.incidence + sparse.diags(self.ground)).tocsc())

    def states(self, factor: Any, loads: np.ndarray) -> np.ndarray:
        loads = np.asarray(loads, dtype=float)
        if loads.ndim != 2 or loads.shape[1] != self.n or not np.all(np.isfinite(loads)):
            raise ValueError('INVALID_FINITE_LOADS')
        self.solves += 1
        result = np.asarray(factor.solve(loads.T)).T
        if not np.all(np.isfinite(result)):
            raise ValueError('NONFINITE_SOLUTION')
        return result

