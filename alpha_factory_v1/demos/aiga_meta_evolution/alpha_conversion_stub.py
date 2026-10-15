# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

Alpha conversion stub.

Given a text description of an opportunity, output a short JSON plan
for how one might evaluate it. The offline path uses explicit keyword rules,
not AI inference. Provider calls require ALPHA_CONVERSION_ALLOW_PROVIDER=1
and an installed SDK and key; credentials alone never enable calls.
"""
from __future__ import annotations

import argparse
import json
import os
import contextlib
import hashlib
import re
from pathlib import Path
from typing import Any, Dict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# Initialize `openai` to `None` as a fallback in case the module import fails.
openai = None
with contextlib.suppress(ModuleNotFoundError):
    import openai  # type: ignore

OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

DEFAULT_LEDGER = Path.home() / ".aiga" / "alpha_conversion_log.json"


def _ledger_path(path: str | os.PathLike[str] | None) -> Path:
    if path:
        ledger = Path(path).expanduser().absolute()
    else:
        env = os.getenv("ALPHA_CONVERSION_LEDGER")
        if env:
            ledger = Path(env).expanduser().absolute()
        else:
            ledger = DEFAULT_LEDGER.expanduser()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    return ledger


def convert_alpha(alpha: str, *, ledger: Path | None = None, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Generate a short execution plan for ``alpha``.

    Args:
        alpha: Opportunity description to convert.
        ledger: Optional path to write the resulting JSON plan.
        model: OpenAI model name when an API key is configured.

    Returns:
        Dictionary representation of the plan steps.
    """
    if not isinstance(alpha, str) or not alpha.strip() or len(alpha) > 10000:
        raise ValueError("alpha must be a nonempty description of at most 10000 characters")
    alpha = " ".join(alpha.split())
    # A deterministic, inspectable rule-based planner, not model inference.
    words = set(re.findall(r"[a-z]+", alpha.lower()))
    rules = [
        (
            {"inventory", "supply", "warehouse", "stock"},
            "inventory",
            "Measure stockouts, excess units and lead times from supplied inventory records",
            "Compare reorder points against demand and carrying-cost assumptions",
        ),
        (
            {"energy", "solar", "electricity", "power"},
            "energy",
            "Collect interval demand, tariffs and generation assumptions",
            "Calculate avoided energy cost against installation and maintenance cost",
        ),
        (
            {"trade", "trading", "market", "finance", "arbitrage"},
            "finance",
            "Collect timestamped prices, fees and liquidity assumptions",
            "Backtest a paper-only strategy including fees, slippage and downside limits",
        ),
        (
            {"software", "automation", "support", "workflow"},
            "automation",
            "Measure task volume, handling time and error rates in the supplied workflow",
            "Compare a bounded prototype with the current workflow on held-out tasks",
        ),
    ]
    matched = [
        (len(words & keys), category, evidence, experiment)
        for keys, category, evidence, experiment in rules
        if words & keys
    ]
    if matched:
        _, category, evidence, experiment = max(matched, key=lambda item: item[0])
    else:
        category = "general"
        evidence = "Collect customer demand, unit cost and capacity evidence for the stated opportunity"
        experiment = "Compare a small reversible prototype against the current baseline"
    plan: Dict[str, Any] = {
        "mode": "local_rule_based_plan",
        "status": "proposal_only",
        "input_id": hashlib.sha256(alpha.encode()).hexdigest(),
        "opportunity": alpha,
        "category": category,
        "steps": [
            evidence,
            experiment,
            "Obtain independent review and explicit authorization before any external action",
        ],
        "required_evidence": ["baseline measurements", "cost assumptions", "measured trial outcomes"],
        "external_actions_performed": False,
    }
    if os.getenv("ALPHA_CONVERSION_ALLOW_PROVIDER") == "1":
        if openai is None or not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Provider explicitly requested but OpenAI SDK or credentials are unavailable")
        client = openai.OpenAI(timeout=OPENAI_TIMEOUT_SEC)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"Draft a proposal for {alpha}. Return JSON with three nonempty string steps. Do not claim actions occurred.",
                }
            ],
        )
        proposed = json.loads(resp.choices[0].message.content)
        steps = proposed.get("steps") if isinstance(proposed, dict) else None
        if not isinstance(steps, list) or len(steps) != 3 or not all(isinstance(x, str) and x.strip() for x in steps):
            raise ValueError("Provider returned an invalid proposal schema")
        plan["steps"] = steps
        plan["mode"] = "provider_generated_proposal"
    if ledger is not None:
        _ledger_path(ledger).write_text(json.dumps(plan, indent=2))
    return plan


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - CLI wrapper
    """CLI for converting an opportunity into a plan."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--alpha", default="Generic opportunity", help="text description of the opportunity")
    p.add_argument("--ledger", help="path to ledger JSON file")
    p.add_argument(
        "--model",
        default=os.getenv("ALPHA_CONVERSION_MODEL", "gpt-4o-mini"),
        help="OpenAI model when API key present",
    )
    p.add_argument("--no-log", action="store_true", help="do not write ledger file")
    args = p.parse_args(argv)

    ledger = None if args.no_log else _ledger_path(args.ledger)
    plan = convert_alpha(args.alpha, ledger=ledger, model=args.model)
    print(json.dumps(plan, indent=2))
    if ledger is not None:
        print(f"Logged to {ledger}")
    else:
        print("Ledger write skipped")


if __name__ == "__main__":  # pragma: no cover
    main()
