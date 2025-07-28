# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

Alpha conversion stub.

Given a text description of an opportunity, output a short JSON plan
for how one might capitalise on it. Works fully offline via a canned
response but will query OpenAI when ``OPENAI_API_KEY`` is set and the
``openai`` package is available. Compatible with either the
``openai_agents`` package or the ``agents`` backport.
"""
from __future__ import annotations

import argparse
import json
import os
import contextlib
from pathlib import Path
from typing import Any, Dict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# Initialize `openai` to `None` as a fallback in case the module import fails.
openai = None
with contextlib.suppress(ModuleNotFoundError):
    import openai  # type: ignore

OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

try:
    from openai_agents import OpenAIAgent  # noqa: F401
except ImportError:
    try:  # pragma: no cover - fallback for legacy package
        from agents import OpenAIAgent  # noqa: F401
    except Exception as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "openai-agents or agents package is required. Install with `pip install openai-agents`"
        ) from exc

SAMPLE_PLAN: Dict[str, Any] = {
    "steps": [
        "Validate market potential and regulatory constraints",
        "Prototype a minimal solution to capture early demand",
        "Deploy iteratively while measuring ROI",
    ]
}

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
    plan: Dict[str, Any] = SAMPLE_PLAN.copy()
    if openai is not None and os.getenv("OPENAI_API_KEY"):
        prompt = (
            f"Given the opportunity: {alpha}\n" "Provide a short JSON plan with three concise steps to realise value."
        )
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                timeout=OPENAI_TIMEOUT_SEC,
            )
            plan = json.loads(resp.choices[0].message.content)
            if not isinstance(plan, dict):
                plan = SAMPLE_PLAN
        except openai.OpenAIError as e:
            logging.error(f"OpenAI API call failed: {e}. Falling back to SAMPLE_PLAN.")
            plan = SAMPLE_PLAN
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}. Falling back to SAMPLE_PLAN.")
            plan = SAMPLE_PLAN
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
