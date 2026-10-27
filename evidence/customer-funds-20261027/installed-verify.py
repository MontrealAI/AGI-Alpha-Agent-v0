# SPDX-License-Identifier: Apache-2.0
"""Check installed runtime first, then use the existing fictional conformance drivers."""
import sys
import json
import hashlib
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
import alpha_factory_v1.core.runtime.successor.flywheel_costs as costs

installed = Path(costs.__file__).parents[1]
assert not installed.is_relative_to(REPO)
expected = {
    p.relative_to(REPO / "alpha_factory_v1/core/runtime").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (REPO / "alpha_factory_v1/core/runtime").rglob("*.py")
}
assert all(hashlib.sha256((installed / p).read_bytes()).hexdigest() == sha for p, sha in expected.items())
sys.path.extend([str(REPO), str(REPO / "tests/runtime")])
import test_flywheel_enterprise as e
import test_flywheel_protected as f
from test_flywheel_customer import deposit, refund, apply
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY

with tempfile.TemporaryDirectory(prefix="installed-customer-funds-") as tmp:
    state = f.setup.__wrapped__(Path(tmp))
    origin = e.launch(state)
    e.accept(state, origin)
    apply(state, "customer-deposit", deposit(mission_id="placement-origin"))
    apply(
        state,
        "customer-earn",
        {
            "event_id": "installed-earned",
            "receipt_id": "service-receipt",
            "amount_micro_usd": 100,
            "delivery_kind": "general",
            "operation_id": "placement-origin",
            "execution_record_digest": origin["digest"],
            "acceptance_record_digest": state["journal"].latest(ACCEPTANCE_KEY + "placement-origin")["digest"],
        },
    )
    apply(state, "customer-refund-due", refund("due", allocation="earned", amount_micro_usd=30))
    due = state["costs"].report()["customer_funds_by_mode"]["synthetic"]
    apply(state, "customer-refund", refund(allocation="earned", amount_micro_usd=30))
    final = state["costs"].report()["customer_funds_by_mode"]["synthetic"]
    assert due["earned_revenue"] == final["earned_revenue"] == 70
    assert due["customer_obligations"] == 30 and final["customer_obligations"] == 0
    assert state["costs"].report()["accepted_service_revenue"] == 0
    print(
        json.dumps(
            {
                "passed": True,
                "installed_root": str(installed),
                "runtime_files_verified": len(expected),
                "accepted_local_artifact": origin["result"]["artifacts"][0]["digest"],
                "before_payment": due,
                "after_payment": final,
                "live_qualified": False,
                "scope": "Unpublished development wheel in separate hash-locked operator environment, plus pytest 8.4.1; local execution with synthetic money and identity",
            },
            indent=2,
        )
    )
