# SPDX-License-Identifier: Apache-2.0
"""Minimal mutation operators for MATS demos."""
from __future__ import annotations

import random
from typing import Any, List

import ast
from alpha_factory_v1.core.self_edit.safety import is_code_safe
from alpha_factory_v1.core.simulation.selector import select_parent

MEME_USAGE: dict[str, int] = {}


class GaussianParam:
    """Add Gaussian noise to numeric genomes within bounds."""

    def __init__(
        self,
        std: float = 0.1,
        bounds: tuple[float, float] = (-1.0, 1.0),
        rng: random.Random | None = None,
    ) -> None:
        self.std = std
        self.bounds = bounds
        self.rng = rng or random.Random()

    def __call__(self, genome: List[float]) -> List[float]:
        """Return ``genome`` perturbed by Gaussian noise within bounds."""
        low, high = self.bounds
        return [min(high, max(low, g + self.rng.gauss(0.0, self.std))) for g in genome]


class PromptRewrite:
    """Basic text rewrite inserting a simple synonym."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.synonyms = {"improve": "enhance", "quick": "fast", "test": "trial"}

    def __call__(self, text: str) -> str:
        """Replace a random word in ``text`` with a simple synonym."""
        words = text.split()
        if not words:
            return text
        idx = self.rng.randrange(len(words))
        w = words[idx].lower()
        words[idx] = self.synonyms.get(w, words[idx])
        return " ".join(words)


class CodePatch:
    """Return code with a small comment appended."""

    def __call__(self, code: str) -> str:
        """Append a ``# patched`` comment to ``code``."""
        suffix = "# patched"
        if not code.endswith("\n"):
            code += "\n"
        return code + suffix + "\n"


class SelfRewriteOperator:
    """Apply ``PromptRewrite`` multiple times.

    Parameters
    ----------
    steps:
        Number of rewrite iterations to perform.
    rng:
        Optional random generator for deterministic behaviour.
    templates:
        Optional list of meme templates reused during mutation.
    reuse_rate:
        Probability of selecting a meme template instead of rewriting.
    """

    def __init__(
        self,
        steps: int = 2,
        rng: random.Random | None = None,
        *,
        templates: list[str] | None = None,
        reuse_rate: float = 0.0,
    ) -> None:
        self.steps = steps
        self.rng = rng or random.Random()
        self.templates = templates or []
        self.reuse_rate = reuse_rate
        self.reuse_count = 0
        self._op = PromptRewrite(rng=self.rng)

    def __call__(self, text: str) -> str:
        """Return ``text`` after applying a series of rewrites."""
        for _ in range(self.steps):
            if self.templates and self.rng.random() < self.reuse_rate:
                text = self.rng.choice(self.templates)
                self.reuse_count += 1
                MEME_USAGE[text] = MEME_USAGE.get(text, 0) + 1
                continue
            candidate = self._op(text)
            safe = is_code_safe(candidate)
            if not safe:
                try:
                    ast.parse(candidate)
                    parse_error = False
                except SyntaxError:
                    parse_error = True
                if not parse_error:
                    break

            # Only validate candidate patches that look like diffs
            if candidate.lstrip().startswith(("---", "diff")):
                if not self._validate_patch(candidate):
                    break

            text = candidate
        return text

    def _validate_patch(self, patch: str) -> bool:
        """Apply ``patch`` in a temporary clone and run quality checks."""

        from pathlib import Path
        import shutil
        import subprocess
        import tempfile

        try:
            root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
        except subprocess.CalledProcessError:
            return False

        with tempfile.TemporaryDirectory() as tmp:
            try:
                subprocess.run(
                    ["git", "clone", "--local", str(root), tmp],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                apply = subprocess.run(
                    ["git", "apply", "-"],
                    input=patch.encode(),
                    cwd=tmp,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if apply.returncode != 0:
                    return False

                checks = [
                    ["pytest", "-q"],
                    ["ruff", "."],
                    ["bandit", "-q", "-r", "."],
                ]
                for cmd in checks:
                    if shutil.which(cmd[0]) is None:
                        continue
                    proc = subprocess.run(
                        cmd,
                        cwd=tmp,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if proc.returncode != 0:
                        return False
            except Exception:
                return False

        return True


def backtrack_boost(
    pop: List[Any],
    archive: List[Any],
    rate: float,
    *,
    beta: float = 1.0,
    gamma: float = 0.0,
) -> Any:
    """Return a parent possibly selected from weaker individuals.

    With probability ``rate`` the parent is drawn uniformly from the
    lower half of ``archive`` based on fitness.  Otherwise the regular
    ``select_parent`` mechanism chooses from ``pop``.
    """

    if not pop:
        raise ValueError("population is empty")
    if rate <= 0.0:
        return select_parent(pop, epsilon=0.1)
    if random.random() < rate:
        ranked = sorted(archive, key=lambda c: getattr(c, "fitness", 0.0))
        bottom = ranked[: max(1, len(ranked) // 2)]
        return random.choice(bottom)
    return select_parent(pop, epsilon=0.1)
