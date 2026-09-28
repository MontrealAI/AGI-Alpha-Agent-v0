# SPDX-License-Identifier: Apache-2.0
"""Toy environments for the Meta Agentic Tree Search demo.

The module exposes :class:`NumberLineEnv` used throughout the tests and demo
loop and :class:`LiveBrokerEnv`, a stub showing how live market data could be
plugged in.
"""
from __future__ import annotations

import random
from typing import List


class NumberLineEnv:
    """Toy environment where agents aim for a target integer."""

    def __init__(self, target: int = 5, rng: random.Random | None = None) -> None:
        """Initialize the environment.

        Args:
            target: Desired integer agents should match.
        """

        self.target = target
        self.rng = rng

    def rollout(self, agents: List[int]) -> float:
        """Return a pseudo reward after a single rollout.

        Args:
            agents: Candidate integer policies.

        Returns:
            Simulated reward value.
        """
        distance = sum(abs(a - self.target) for a in agents)
        noise = (self.rng.random() if self.rng is not None else random.random()) * 0.1
        return -distance + noise


class LiveBrokerEnv(NumberLineEnv):
    """Placeholder environment that could connect to a live broker.

    Args:
        target: Target integer used by :class:`NumberLineEnv` logic.
        market_data: Optional sequence of prices that override ``target``.
    """

    def __init__(self, target: int = 5, market_data: List[int] | None = None, rng: random.Random | None = None) -> None:
        """Initialize the environment.

        Args:
            target: Desired integer agents should match.
            market_data: Optional price sequence used as live targets.
        """

        super().__init__(target=target, rng=rng)
        self.market_data = list(market_data) if market_data else []

    def rollout(self, agents: List[int]) -> float:
        """Return reward using current market data if available."""

        if self.market_data:
            self.target = self.market_data.pop(0)
        return super().rollout(agents)
