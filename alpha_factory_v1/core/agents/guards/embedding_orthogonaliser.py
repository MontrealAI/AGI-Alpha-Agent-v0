# SPDX-License-Identifier: Apache-2.0
"""Random orthogonal projection guard for embedding vectors."""

from __future__ import annotations

import random
from typing import Sequence, TYPE_CHECKING

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - type hints only
    import numpy as np

__all__ = ["EmbeddingOrthogonaliser"]


class EmbeddingOrthogonaliser:
    """Apply a random orthogonal projection every ``steps`` calls."""

    def __init__(self, dim: int, steps: int = 5000, rng: random.Random | None = None) -> None:
        self.dim = dim
        self.steps = steps
        self._rng = rng or random.Random()
        self._counter = 0
        self._proj = self._new_projection()

    def _new_projection(self) -> list[list[float]] | "np.ndarray":
        """Return a new random orthogonal projection matrix."""
        if np is not None:
            mat = np.asarray(
                [[self._rng.gauss(0.0, 1.0) for _ in range(self.dim)] for _ in range(self.dim)],
                dtype="float32",
            )
            q, _ = np.linalg.qr(mat)
            return np.asarray(q, dtype="float32")  # type: ignore[no-any-return]
        mat = [[self._rng.gauss(0.0, 1.0) for _ in range(self.dim)] for _ in range(self.dim)]
        for i in range(self.dim):
            for j in range(i):
                dot = sum(mat[i][k] * mat[j][k] for k in range(self.dim))
                for k in range(self.dim):
                    mat[i][k] -= dot * mat[j][k]
            norm = sum(x * x for x in mat[i]) ** 0.5 + 1e-12
            for k in range(self.dim):
                mat[i][k] /= norm
        return mat

    def project(self, vec: Sequence[float] | np.ndarray) -> np.ndarray | list[float]:
        """Return ``vec`` multiplied by the current projection matrix."""
        if self._counter % self.steps == 0:
            self._proj = self._new_projection()
        self._counter += 1
        if np is not None:
            arr = np.asarray(vec, dtype="float32")
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return (arr @ np.asarray(self._proj).T).reshape(-1)  # type: ignore[no-any-return]
        arr = [float(x) for x in vec]
        out = [sum(a * b for a, b in zip(arr, col)) for col in zip(*self._proj)]
        if np is not None:
            return np.asarray(out, dtype="float32")
        return out
