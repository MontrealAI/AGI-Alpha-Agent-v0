# SPDX-License-Identifier: Apache-2.0
"""Bounded offline opportunity-to-proposal workflow; optional legacy SDK server."""
from __future__ import annotations
import argparse
import json
from .alpha_conversion_stub import convert_alpha


def run_workflow(alpha: str) -> dict:
    """Evaluate a supplied description without discovery, inference or external actions."""
    return {"alpha": alpha, "plan": convert_alpha(alpha)}


def __getattr__(name: str):
    # Preserve legacy runtime imports without loading optional SDKs for local plans.
    if name in {"WorkflowAgent", "discover_alpha", "convert_alpha_tool", "OpenAIAgent", "AGENT_PORT"}:
        from . import workflow_runtime

        return getattr(workflow_runtime, name)
    raise AttributeError(name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alpha", help="supplied opportunity to evaluate locally")
    parser.add_argument("--serve", action="store_true", help="explicitly launch the optional legacy SDK runtime")
    args = parser.parse_args()
    if args.serve:
        from .workflow_runtime import main as serve

        serve()
    elif args.alpha:
        print(json.dumps(run_workflow(args.alpha), indent=2))
    else:
        parser.error("provide --alpha for a local proposal or --serve for the optional SDK runtime")


if __name__ == "__main__":
    main()
