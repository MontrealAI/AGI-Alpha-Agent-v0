# SPDX-License-Identifier: Apache-2.0
"""Legacy provider-backed propose/validate/solve curriculum.

Generated reference programs are validated in Docker. An independent provider
response solves deduction tasks without seeing the expected output. Learning
adjusts a bounded temperature heuristic and replay buffer; it is not PPO or
model-weight training. The primary offline experience is curriculum_lab.
"""

from __future__ import annotations

import ast
import json
import logging
import multiprocessing as _mp
import os
import random
import re
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------
# Optional deps – graceful degradation
try:
    import numpy as _np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    _np = None  # type: ignore

try:
    from radon.complexity import cc_visit  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    cc_visit = None  # type: ignore
# ---------------------------------------------------------------------

LOG = logging.getLogger("azr_engine")
LOG.addHandler(logging.NullHandler())

# ---------------------------------------------------------------------
#               Config (env‑tunable – all values have sane defaults)
# ---------------------------------------------------------------------
SOFT_T = int(os.getenv("AZR_SOFT_TIMEOUT", "6"))
HARD_T = int(os.getenv("AZR_HARD_TIMEOUT", "8"))
MEM_MB = int(os.getenv("AZR_MEM_LIMIT_MB", "256"))
MAX_PROG_LOC = int(os.getenv("AZR_MAX_PROG_LOC", "60"))
MAX_BUF = int(os.getenv("AZR_BUFFER_MAX", "4096"))
RNG_SEED = int(os.getenv("AZR_SEED", "2025"))

_BANNED = ("os.", "sys.", "subprocess", "socket", "threading", "multiprocessing")


# ---------------------------------------------------------------------
#                         Sandbox helpers
# ---------------------------------------------------------------------
def _exec_trusted(code: str, inp_json: str) -> Tuple[str, str]:
    """Evaluate the identity fixture or run generated code in Docker isolation."""
    from alpha_factory_v1.demos.utils.code_eval import evaluate

    try:
        value = json.loads(inp_json)
    except ValueError as exc:
        return "", str(exc)
    return evaluate(code, value)


# ---------------------------------------------------------------------
#                           Data structures
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class Triplet:
    """Deterministic reasoning task."""

    program: str
    inp: str
    out: str
    mode: str = "deduct"  # deduct | abduct | induct


@dataclass
class TaskResult:
    triplet: Triplet
    solved: bool
    latency: float
    stdout: str
    stderr: str
    complexity: float  # cyclomatic complexity proxy


def _json_equal(left: str, right: str) -> bool:
    from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import canonical, parse

    try:
        return canonical(parse(left.encode())) == canonical(parse(right.encode()))
    except (ValueError, TypeError):
        return False


def _complexity(py_src: str) -> float:  # noqa: D401
    """Return cyclomatic complexity; fallback to AST node count."""
    if cc_visit:
        try:
            return max((b.complexity for b in cc_visit(py_src) if b.lineno == 1), default=1.0)
        except Exception:
            pass
    # Fallback: #nodes / 10  (heuristic)
    try:
        return max(1.0, len(list(ast.walk(ast.parse(py_src)))) / 10.0)
    except Exception:
        return 10.0


# ---------------------------------------------------------------------
#                       Absolute‑Zero Engine
# ---------------------------------------------------------------------
class AZREngine:
    """Open‑ended self‑curriculum orchestrator."""

    _TRIPLE_RE = re.compile(
        r"""```python\s*#\s*program\s*\n(?P<prog>[\s\S]+?)```\s*```json\s*#\s*input\s*\n(?P<inp>[\s\S]+?)```\s*```json\s*#\s*output\s*\n(?P<out>[\s\S]+?)```""",  # noqa: E501
        re.MULTILINE,
    )

    _PROMPT = textwrap.dedent(
        """        Invent {n} deterministic Python *triplets* that challenge a
    GPT‑4‑level coder (~30‑60 % expected solve‑rate).

    Format **exactly**:
    ```python  # program
    def main(x):
        ...
    ```
    ```json  # input
    7
    ```
    ```json  # output
    49
    ```

    Constraints:
    • ≤ {max_loc} LOC, stdlib only, deterministic
    • input/output JSON‑serialisable (<256 chars)
    • Banned modules: os, sys, subprocess, socket, threading, multiprocessing

    Current buffer: {buf} tasks.
    Diversity reference (do not copy):
    {examples}
    """
    )

    def __init__(self, fm, *, buffer_max: int = MAX_BUF, logger: Optional[Callable[[str], None]] = None):
        if not 1 <= buffer_max <= 4096:
            raise ValueError("buffer_max must be from 1 through 4096")
        self.fm = fm
        self.buffer: List[Triplet] = []
        self.buffer_max = buffer_max
        self.temperature = 0.5
        self._baseline = 0.0  # moving scalar reward baseline
        self.log = logger or (lambda m: LOG.info(m))
        self._rng = random.Random(RNG_SEED)

    # ---------------------------- public API ------------------------
    def propose(self, k: int = 4) -> List[Triplet]:
        if not 1 <= k <= 32:
            raise ValueError("Task count must be from 1 through 32")
        prompt = self._build_prompt(k)
        raw = self.fm.chat(
            system="You are AZR‑Proposer, inventing new reasoning tasks.",
            user=prompt,
            temperature=self.temperature,
            max_tokens=2000,
        )
        triplets = [t for t in self._parse_triplets(raw)[:k] if self._validate(t)]
        self.log(f"[AZR] proposer: {len(triplets)}/{k} valid; T={self.temperature:.2f}")
        return triplets

    def solve(self, tasks: Sequence[Triplet]) -> List[TaskResult]:
        results: List[TaskResult] = []
        for t in tasks:
            start = time.perf_counter()
            stdout, stderr = "", ""
            try:
                stdout = self.fm.chat(
                    system="You are AZR-Solver. Infer the program output. Return only the JSON answer.",
                    user=json.dumps({"program": t.program, "input": json.loads(t.inp)}),
                    temperature=0.0,
                    max_tokens=256,
                ).strip()
                solved = _json_equal(stdout, t.out)
            except Exception as exc:
                stderr, solved = str(exc), False
            lat = time.perf_counter() - start
            complexity = _complexity(t.program)
            results.append(TaskResult(t, solved, lat, stdout, stderr, complexity))
        return results

    def learn(self, results: Sequence[TaskResult]) -> None:
        if not results:
            return
        # Multi‑objective scalarisation (simple): reward = unsolved_ratio * 0.7 + novelty * 0.3
        solved_frac = sum(r.solved for r in results) / len(results)
        diff_reward = 1.0 - solved_frac
        novelty = sum(r.complexity for r in results) / len(results)
        novelty_norm = min(1.0, novelty / 15.0)
        reward = 0.7 * diff_reward + 0.3 * novelty_norm

        beta = 0.1
        self._baseline = (1 - beta) * self._baseline + beta * reward
        adv = reward - self._baseline
        # Bounded heuristic temperature controller (no model-weight update)
        delta = -0.04 if adv > 0 else 0.04
        self.temperature = max(0.1, min(1.0, self.temperature + delta))

        # Buffer maintenance – keep correctly solved tasks
        for r in results:
            if r.solved:
                self._add(r.triplet)

        self.log(f"[AZR] reward={reward:.3f} adv={adv:+.3f} -> T={self.temperature:.2f}")

    def _parse_triplets(self, raw: str) -> List[Triplet]:
        """Parse fenced program/input/output groups from a proposer response."""
        return [Triplet(m["prog"].strip(), m["inp"].strip(), m["out"].strip()) for m in self._TRIPLE_RE.finditer(raw)]

    def _validate(self, t: Triplet) -> bool:
        if (
            len(t.program.splitlines()) > MAX_PROG_LOC
            or len(t.inp) > 256
            or len(t.out) > 256
            or any(b in t.program for b in _BANNED)
        ):
            return False
        stdout, stderr = _exec_trusted(t.program, t.inp)
        return stderr == "" and _json_equal(stdout, t.out)

    def _add(self, t: Triplet) -> None:
        if t in self.buffer:
            return
        self.buffer.append(t)
        if len(self.buffer) > self.buffer_max:
            self.buffer.pop(0)

    def _build_prompt(self, n: int) -> str:
        examples = (
            "\n\n".join(
                f"```python\n{t.program}```\n```json\n{t.inp}```\n```json\n{t.out}```"
                for t in self._rng.sample(self.buffer, k=min(3, len(self.buffer)))
            )
            or "(buffer empty)"
        )

        return self._PROMPT.format(
            n=n,
            max_loc=MAX_PROG_LOC,
            buf=len(self.buffer),
            examples=examples,
        )

    # ----------------------- serialisation --------------------------
    def to_json(self) -> str:
        state = {"T": self.temperature, "baseline": self._baseline, "buffer": [t.__dict__ for t in self.buffer[-128:]]}
        return json.dumps(state, separators=(",", ":"))

    # ------------------------ repr ----------------------------------
    def __repr__(self) -> str:
        return f"<AZREngine buf={len(self.buffer)} T={self.temperature:.2f}>"


# ---------------------------------------------------------------------
#                 factory expected by orchestrator
# ---------------------------------------------------------------------
def curriculum_factory(fm, **kwargs) -> AZREngine:  # noqa: D401
    return AZREngine(fm, **kwargs)


# ---------------------------------------------------------------------
#                      CLI smoke‑test
# ---------------------------------------------------------------------
if __name__ == "__main__":

    class _StubFM:
        def chat(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 1024) -> str:
            if "AZR-Solver" in system:
                return json.dumps(json.loads(user)["input"], separators=(",", ":"))
            # deterministically return identity task
            return """```python # program\ndef main(x):\n    return x\n```\n```json # input\n3```\n```json # output\n3```"""

    eng = AZREngine(_StubFM())
    new_tasks = eng.propose(2)
    res = eng.solve(new_tasks)
    eng.learn(res)
    print("[SMOKE]", eng, "solved", [r.solved for r in res])
