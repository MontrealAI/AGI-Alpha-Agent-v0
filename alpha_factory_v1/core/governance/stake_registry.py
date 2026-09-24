# SPDX-License-Identifier: Apache-2.0
"""Simple stake registry supporting stake-weighted voting."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, MutableMapping


@dataclass
class StakeRegistry:
    """In-memory stake and vote tracking."""

    stakes: MutableMapping[str, float] = field(default_factory=dict)
    votes: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    thresholds: Dict[str, float] = field(default_factory=dict)

    def set_stake(self, agent_id: str, amount: float) -> None:
        """Register ``agent_id`` with ``amount`` tokens."""
        if not agent_id or not math.isfinite(amount) or amount < 0:
            raise ValueError("stake requires an identity and a finite nonnegative amount")
        self.stakes[agent_id] = float(amount)

    def set_threshold(self, proposal_id: str, fraction: float) -> None:
        """Set custom acceptance threshold for ``proposal_id``."""
        if not math.isfinite(fraction) or not 0 <= fraction <= 1:
            raise ValueError("threshold must be in [0, 1]; zero is the demo auto-promotion mode")
        self.thresholds[proposal_id] = float(fraction)

    def burn(self, agent_id: str, fraction: float) -> None:
        """Burn ``fraction`` of ``agent_id``'s stake if present."""
        if not math.isfinite(fraction) or not 0 <= fraction <= 1:
            raise ValueError("burn fraction must be in [0, 1]")
        if agent_id in self.stakes:
            self.stakes[agent_id] = max(0.0, self.stakes[agent_id] * (1.0 - fraction))

    def archive_accept(self, agent_id: str) -> None:
        """Burn 1% of ``agent_id`` stake when a candidate is accepted."""
        self.burn(agent_id, 0.01)

    def total(self) -> float:
        """Return total stake across all agents."""
        return float(sum(self.stakes.values()))

    def vote(self, proposal_id: str, agent_id: str, support: bool) -> None:
        """Record ``agent_id``'s vote for ``proposal_id``."""
        if agent_id not in self.stakes:
            raise ValueError(f"unknown agent {agent_id}")
        self.votes.setdefault(proposal_id, {})[agent_id] = bool(support)

    def accepted(self, proposal_id: str) -> bool:
        """Return ``True`` when yes-votes reach the required threshold."""
        total = self.total()
        if total == 0:
            return False
        votes = self.votes.get(proposal_id, {})
        yes = sum(self.stakes[a] for a, v in votes.items() if v)
        required = self.thresholds.get(proposal_id, 2 / 3)
        return yes / total >= required
