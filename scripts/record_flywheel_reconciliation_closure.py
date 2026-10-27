# SPDX-License-Identifier: Apache-2.0
"""Replay cancelled-permit refusal and fresh finite delivery with fixture resources."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import tempfile
from typing import Any

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Enterprise, key
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.utils.disclaimer import DISCLAIMER

ROOT = Path(__file__).resolve().parents[1]


def record() -> dict[str, Any]:
    """Close one caught preflight failure, refuse its old permit, and accept fresh local work."""
    sys.path.insert(0, str(ROOT / "tests/runtime"))
    import test_flywheel_reconciliation_closure as r
    import test_flywheel_enterprise as e
    import test_flywheel_protected as f
    import test_flywheel_specialists as s

    with tempfile.TemporaryDirectory(prefix="flywheel-reconciliation-closure-") as work:
        state = f.setup.__wrapped__(Path(work))
        executor, mission, profile, permit = r.caught(state)
        enterprise = Enterprise(state["service"])
        failed = enterprise.inspect("launch", "placement-origin")
        r.pause(state)
        s.seal(state, mission.mission_id, "A")
        costs_before = state["costs"].snapshot()
        reconciled = enterprise.apply(r.reconciliation(state))
        closure = state["journal"].latest(operation_key("placement-origin"))
        accounting_unchanged = costs_before == state["costs"].snapshot()
        r.pause(state, False)
        try:
            executor.run(mission, profile, permit)
        except Conflict as exc:
            refusal = str(exc)
        else:
            raise AssertionError("cancelled permit regained execution")
        fresh = e.decision(state, "fresh-authority")
        enterprise.run("fresh-authority", *e.execution(state, "fresh-delivery"))
        delivered = state["journal"].latest(operation_key("fresh-delivery"))
        s.seal(state, "fresh-delivery", "A")
        accepted = state["service"].accept_general_origin(
            f.signed(
                state,
                "general-acceptance",
                "acceptor",
                {
                    "operation_id": "fresh-delivery",
                    "execution_record_digest": delivered["digest"],
                    "output_digest": digest("general-delivered-output", delivered["result"]),
                    "rights_evidence": f.ZERO,
                },
                "accept-fresh-delivery",
            )
        )
        assert accounting_unchanged and reconciled["execution_digest"] is None
        assert reconciled["closure_digest"] == closure["digest"] and not closure["execution_started"]
        assert enterprise.inspect("decision", "first-decision")["consumed"]
        assert not state["journal"].latest(key("active", "capacity"))["reservations"]
        observations = {
            "caught_preflight_launch": failed,
            "reconciled_launch": reconciled,
            "non_execution_closure": closure,
            "old_permit_refusal_after_conditions_recover": refusal,
            "reconciliation_posts_no_charge": accounting_unchanged,
            "fresh_decision": fresh,
            "fresh_delivery": delivered,
            "independent_finite_acceptance": accepted,
            "fixture_accounting": state["costs"].report(),
            "journal_verification": state["journal"].verify(),
        }
    paths = [
        *sorted((ROOT / "alpha_factory_v1/core/runtime").rglob("*.py")),
        Path(__file__).resolve(),
        ROOT / "scripts/record_general_flywheel.py",
        *(
            ROOT / "tests/runtime" / (name + ".py")
            for name in (
                "test_flywheel_reconciliation_closure",
                "test_flywheel_enterprise",
                "test_flywheel_protected",
                "test_flywheel_specialists",
            )
        ),
    ]
    return {
        "schema": "flywheel-reconciliation-closure-conformance/v1",
        "disclaimer": DISCLAIMER,
        "scope": "Executed local tools and signatures; fictional model, identities, funding and billing",
        "actual_frontier_calls": 0,
        "actual_customer_collections_micro_usd": 0,
        "actual_complete_monetary_cost": None,
        "actual_profit": None,
        "live_or_commercial_qualification": False,
        "python": platform.python_version(),
        "dependencies": {
            name: importlib.metadata.version(name) for name in ("pydantic", "cryptography", "eth-account")
        },
        "sources": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "observations": observations,
    }


def main() -> None:
    """Write a new evidence file without replacing an earlier result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("preserve prior evidence; choose a new output")
    result = record()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
