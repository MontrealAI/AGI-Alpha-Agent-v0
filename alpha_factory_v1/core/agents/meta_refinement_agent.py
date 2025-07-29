# SPDX-License-Identifier: Apache-2.0
"""Analyse orchestrator logs and propose refinement patches.

This module currently **simulates** repository improvements. The
`MetaRefinementAgent` fabricates diff proposals based on a naive
heuristic without measuring real performance. It exists purely as a
prototype to demonstrate self-healing logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Mapping, cast

from alpha_factory_v1.core.governance.stake_registry import StakeRegistry
from alpha_factory_v1.core.self_evolution import harness
from alpha_factory_v1.core.tools.diff_mutation import propose_diff
from alpha_factory_v1.core.tools import test_scribe

__all__ = ["MetaRefinementAgent"]


class MetaRefinementAgent:
    """Generate diff proposals based on orchestrator log analysis.

    This agent does **not** actually optimise the repository. It fabricates
    diffs from log heuristics as a proof of concept. Future versions may
    integrate real profiling and optimisation logic.
    """

    def __init__(self, repo: str | Path, log_dir: str | Path, registry: StakeRegistry | None = None) -> None:
        self.repo = Path(repo)
        self.log_dir = Path(log_dir)
        self.registry = registry or StakeRegistry()
        if "meta" not in self.registry.stakes:
            self.registry.set_stake("meta", 1.0)

    # ------------------------------------------------------------------
    def _load_logs(self) -> List[Mapping[str, object]]:
        records: List[Mapping[str, object]] = []
        for file in sorted(self.log_dir.glob("*.json")):
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    @staticmethod
    def _detect_bottleneck(entries: Iterable[Mapping[str, object]]) -> str | None:
        prev_ts: float | None = None
        max_delta = -1.0
        target: str | None = None
        for rec in entries:
            ts = float(cast(float, rec.get("ts", 0.0)))
            if prev_ts is not None:
                delta = ts - prev_ts
                if delta > max_delta:
                    max_delta = delta
                    target = str(rec.get("hash", ""))
            prev_ts = ts
        return target

    def _create_patch(self, entries: Iterable[Mapping[str, object]]) -> str:
        """Create a diff targeting the slowest or error-prone module.

        A basic heuristic inspects ``agent.cycle`` logs and suggests increasing
        the cycle period when average latency exceeds five seconds. This is a
        placeholder until a real adaptive scheduler is implemented.
        """
        stats: dict[str, dict[str, float]] = {}
        cycle_latency: dict[str, list[float]] = {}
        for rec in entries:
            module = str(rec.get("module") or rec.get("agent") or rec.get("hash") or "")
            if not module:
                continue
            data = stats.setdefault(module, {"lat": 0.0, "count": 0.0, "err": 0.0})
            if "latency" in rec:
                data["lat"] += float(cast(float, rec["latency"]))
                data["count"] += 1.0
            if "agent" in rec and "latency_ms" in rec:
                cycle_latency.setdefault(str(rec["agent"]), []).append(float(cast(float, rec["latency_ms"])))
            if rec.get("level") == "error" or rec.get("error"):
                data["err"] += 1.0

        for agent, samples in cycle_latency.items():
            if samples:
                avg_ms = sum(samples) / len(samples)
                if avg_ms > 5000:
                    metric = self.repo / "metric.txt"
                    goal = f"increase cycle to {int(avg_ms/1000)}s for {agent}"
                    return propose_diff(str(metric), goal)

        if not stats:
            metric = self.repo / "metric.txt"
            return propose_diff(str(metric), "optimise performance")

        def avg_latency(d: dict[str, float]) -> float:
            return d["lat"] / d["count"] if d["count"] else -1.0

        target = max(stats.items(), key=lambda kv: (avg_latency(kv[1]), kv[1]["err"]))[0]

        path = self.repo / target
        goal = f"improve {target}"
        if not path.exists():
            path = self.repo / "metric.txt"
            goal = f"optimise around {target}"

        return propose_diff(str(path), goal)

    # ------------------------------------------------------------------
    def refine(self) -> bool:
        """Generate and apply a patch addressing the detected bottleneck.

        Returns:
            bool: ``True`` if the patch was merged, ``False`` otherwise.
        """
        logs = self._load_logs()
        if not logs:
            return False
        diff = self._create_patch(logs)
        accepted = harness.vote_and_merge(self.repo, diff, self.registry, agent_id="meta")
        if accepted:
            test_scribe.generate_test(self.repo, "True")
        return accepted
