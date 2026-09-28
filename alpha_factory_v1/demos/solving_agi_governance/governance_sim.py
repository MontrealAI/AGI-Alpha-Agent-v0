# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""Legacy mean-field cooperation simulation with a stochastic initial population.

``delta`` is the numerical update rate, not a repeated-game discount factor.
The outcome depends on the supplied payoff and stake assumptions. This model
establishes neither a universal cooperation threshold nor a unique equilibrium.
Use the governance workbench for explicit proposal gates and reproducible evidence.
"""
from __future__ import annotations

import argparse
import random
import math
import os
from typing import cast

# Payoff matrix for a standard Prisoner's Dilemma (T > R > P > S)
R, T, P, S = 3.0, 5.0, 1.0, 0.0


def run_sim(
    agents: int,
    rounds: int,
    delta: float,
    stake: float,
    *,
    seed: int | None = None,
    verbose: bool = False,
) -> float:
    """Return the mean cooperation probability after ``rounds`` iterations.

    Parameters
    ----------
    agents:
        Number of agents in the simulation. Must be positive.
    rounds:
        Number of interaction rounds to simulate. Must be positive.
    delta:
        Numerical update rate in ``[0, 1]`` (legacy flag name).
    stake:
        Penalty applied when an agent defects. Must be non-negative.
    seed:
        Optional random seed for deterministic runs.
    verbose:
        If ``True`` prints progress every 10%% of the run.
    """

    if type(agents) is not int or not 1 <= agents <= 100_000:
        raise ValueError("agents must be an integer from 1 through 100000")
    if type(rounds) is not int or not 1 <= rounds <= 1_000_000:
        raise ValueError("rounds must be an integer from 1 through 1000000")
    if agents * rounds > 100_000_000:
        raise ValueError("Simulation exceeds 100000000 agent updates; reduce agents or rounds")
    if type(delta) not in (int, float) or not math.isfinite(delta) or not 0.0 <= delta <= 1.0:
        raise ValueError("delta must be between 0 and 1")
    if type(stake) not in (int, float) or not math.isfinite(stake) or not 0 <= stake <= 1_000_000:
        raise ValueError("stake must be finite and between 0 and 1000000")
    if seed is not None and type(seed) is not int:
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)

    probs = [rng.random() for _ in range(agents)]
    for r in range(1, rounds + 1):
        avg_p = sum(probs) / agents
        coop_payoff = R * avg_p + S * (1 - avg_p)
        defect_payoff = T * avg_p + P * (1 - avg_p) - stake
        for i, p in enumerate(probs):
            avg_payoff = p * coop_payoff + (1 - p) * defect_payoff
            p += delta * p * (coop_payoff - avg_payoff)
            probs[i] = max(0.0, min(1.0, p))
        if verbose and r % max(1, rounds // 10) == 0:
            print(f"round {r:>4}/{rounds} – mean cooperation {sum(probs) / agents:.3f}")
    return sum(probs) / agents


def summarise_with_agent(mean_coop: float, *, agents: int, rounds: int, delta: float, stake: float) -> str:
    """Return a natural-language summary of a simulation result.

    If the ``openai`` package and an API key are available, the summary is
    generated via the optional OpenAI Python client.  Otherwise a simple
    fallback string is returned.
    """

    base_msg = (
        "Simulation with {agents} agents, {rounds} rounds, delta={delta}, stake={stake} "
        "yielded mean cooperation ≈ {coop:.3f}."
    ).format(agents=agents, rounds=rounds, delta=delta, stake=stake, coop=mean_coop)

    try:  # optional dependency
        import openai
    except Exception:
        return base_msg

    if not os.getenv("OPENAI_API_KEY"):
        return base_msg + " (OPENAI_API_KEY not set; using offline summary)"
    try:
        timeout = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))
        if not 1 <= timeout <= 120:
            return base_msg + " (Invalid summary timeout; using offline summary)"
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=timeout)
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Summarise this toy mean-field simulation. Delta is an update rate, not a discount factor. "
                    "Do not claim unique equilibria, real AGI or validated safety.",
                },
                {"role": "user", "content": base_msg},
            ],
            max_tokens=60,
            timeout=timeout,
        )
        return cast(str, completion.choices[0].message.content).strip()
    except openai.AuthenticationError:
        return base_msg + " (OPENAI_API_KEY not set; using offline summary)"
    except openai.APIConnectionError:
        return base_msg + " (OpenAI connection error; using offline summary)"
    except openai.RateLimitError:
        return base_msg + " (OpenAI rate limit exceeded; using offline summary)"
    except Exception:
        return base_msg


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="AGIALPHA legacy mean-field cooperation simulation")
    ap.add_argument("-N", "--agents", type=int, default=100, help="number of agents")
    ap.add_argument("-r", "--rounds", type=int, default=1000, help="simulation rounds")
    ap.add_argument(
        "--delta", type=float, default=0.8, help="numerical update rate (legacy name, not a discount factor)"
    )
    ap.add_argument("--stake", type=float, default=2.5, help="stake penalty")
    ap.add_argument("--seed", type=int, help="optional RNG seed")
    ap.add_argument("-v", "--verbose", action="store_true", help="print progress")
    ap.add_argument(
        "--summary",
        action="store_true",
        help="opt in to an OpenAI API summary if credentials are configured",
    )
    args = ap.parse_args(argv)

    try:
        coop = run_sim(
            args.agents,
            args.rounds,
            args.delta,
            args.stake,
            seed=args.seed,
            verbose=args.verbose,
        )
    except ValueError as exc:
        ap.error(str(exc))
    print(f"mean cooperation ≈ {coop:.3f}")
    if args.summary:
        print(summarise_with_agent(coop, agents=args.agents, rounds=args.rounds, delta=args.delta, stake=args.stake))


if __name__ == "__main__":
    main()
