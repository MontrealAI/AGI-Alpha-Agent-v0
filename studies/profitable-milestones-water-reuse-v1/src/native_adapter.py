# SPDX-License-Identifier: Apache-2.0
"""Rehearse the existing native accounting and FusionPlan interfaces locally."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


STUDY = Path(__file__).resolve().parents[1]
REPOSITORY = STUDY.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPOSITORY))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat  # noqa: E402
from alpha_factory_v1.core.runtime.store import Conflict, Journal  # noqa: E402
from alpha_factory_v1.core.runtime.successor.flywheel_costs import (  # noqa: E402
    CATEGORIES,
    Charge,
    CompletenessSeal,
    CostLedger,
)
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest  # noqa: E402
from alpha_factory_v1.core.runtime.successor.trust import (  # noqa: E402
    TrustAnchor,
    TrustRegistry,
    sign_record,
)


NATIVE_COMPONENTS = (
    "alpha_factory_v1/core/runtime/store.py",
    "alpha_factory_v1/core/runtime/successor/flywheel_costs.py",
    "alpha_factory_v1/core/runtime/successor/protocol.py",
    "alpha_factory_v1/core/runtime/successor/trust.py",
    "alpha_factory_v1/core/runtime/successor/signatures.py",
    "docs/assets/nova-studio/plan.mjs",
    "docs/assets/nova-studio/vendor/ethers-6.17.0.mjs",
    "docs/assets/ascension/crypto.mjs",
    "docs/assets/ascension-wallet/protocol.mjs",
)


def file_hash(path: Path) -> str:
    """Identify exact local source or evidence bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refusal(action: Callable[[], Any]) -> dict[str, Any]:
    """Keep the actual native refusal instead of replacing its rule."""
    try:
        action()
    except (ValueError, Conflict) as exc:
        return {"refused": True, "exception": type(exc).__name__, "reason": str(exc)}
    raise AssertionError("A declared negative control was accepted")


def accounting_rehearsal(root: Path) -> dict[str, Any]:
    """Use isolated native journals; never export generated private identities."""
    principal = "research-local-accountant"
    key = Ed25519PrivateKey.generate()
    anchor = TrustAnchor(
        key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
        frozenset({"accounting"}),
        provenance="local",
    )
    trust = TrustRegistry({principal: anchor})
    journal = Journal.initialize(root / "unknown-actual-costs")
    ledger = CostLedger(journal, trust)
    mission = "reuse-investment-gate-study"

    def apply(target: CostLedger, action: str, record: Any, operation: str) -> dict[str, Any]:
        return target.apply(
            sign_record(
                key,
                principal,
                "flywheel-cost-command",
                {
                    "journal_identity": target.journal.identity,
                    "operation_id": operation,
                    "action": action,
                    "record": record,
                },
            )
        )

    charges = []
    for category in sorted(CATEGORIES):
        charge = Charge(
            activity_id="study/" + category,
            mission_id=mission,
            bucket="A",
            category=category,
            accrued_micro_usd=None,
            paid_micro_usd=0,
            basis="unknown",
            evidence_digest=digest("study-cost-observation", {"category": category, "metered_amount": None}),
            note=(
                "Actual complete monetary amount is unmetered. Zero paid records means no payment evidence "
                "was supplied to this local journal, not that this category or the study was free."
            ),
        ).model_dump()
        apply(ledger, "charge", charge, "charge/" + category)
        charges.append(charge)
    seal = CompletenessSeal(
        mission_id=mission,
        evidence_digest=digest("study-seal-attempt", {"mission": mission}),
        categories=sorted(CATEGORIES),
    )
    unknown_seal = refusal(lambda: apply(ledger, "seal", seal.model_dump(), "cannot-seal-unknown"))
    unknown_to_zero = refusal(lambda: Charge.model_validate({**charges[0], "accrued_micro_usd": 0}))
    duplicate_activity = refusal(
        lambda: apply(ledger, "charge", {**charges[0], "bucket": "B"}, "cannot-double-count-learning")
    )
    incomplete_categories = refusal(
        lambda: CompletenessSeal.model_validate({**seal.model_dump(), "categories": sorted(CATEGORIES)[:-1]})
    )
    actual = ledger.report()
    assert actual["unknown_costs"] and not actual["complete"]
    assert actual["collected_revenue"] == 0
    assert actual["delivery_profit"] is None and actual["complete_cost_profit"] is None
    assert actual["available_funds"] is None and actual["obligations"] is None
    actual_integrity = journal.verify()

    pending_journal = Journal.initialize(root / "synthetic-unearned-claims")
    pending_ledger = CostLedger(pending_journal, trust)
    for index, action in enumerate(("offer", "invoice", "pending"), start=1):
        apply(
            pending_ledger,
            action,
            {
                "record_id": f"fictional-{action}",
                "mission_id": "fictional-pending-only",
                "amount_micro_usd": index * 1_000_000_000,
                "evidence_digest": digest("fictional-unearned-claim", {"kind": action}),
            },
            action,
        )
    before_deposit = pending_ledger.report()
    deposit = refusal(
        lambda: apply(
            pending_ledger,
            "deposit",
            {
                "record_id": "fictional-deposit",
                "mission_id": "fictional-pending-only",
                "amount_micro_usd": 1_000_000_000,
                "evidence_digest": digest("fictional-deposit", {"scope": "unsupported-on-pinned-main"}),
            },
            "deposit-refusal",
        )
    )
    pending = pending_ledger.report()
    assert before_deposit == pending
    assert pending["cash"] == pending["collected_revenue"] == pending["available_funds"] == 0
    pending_integrity = pending_journal.verify()

    false_claim = {"statement": "two plus two equals five", "lhs": 4, "claimed_rhs": 5}
    signed_false = sign_record(key, principal, "study-evidence", false_claim)
    verified_false = trust.verify(signed_false, "study-evidence", "accounting")
    assert verified_false == false_claim and verified_false["lhs"] != verified_false["claimed_rhs"]
    trust.revoke(principal)
    revoked = refusal(lambda: trust.verify(signed_false, "study-evidence", "accounting"))
    explicitly_regranted = TrustRegistry({principal: anchor})
    assert explicitly_regranted.verify(signed_false, "study-evidence", "accounting") == false_claim
    return {
        "scope": "Native local conformance with ephemeral rehearsal authority; no live service admission.",
        "actual_unknown_category_records": charges,
        "actual_observation_report": actual,
        "known_subtotals_warning": "Zero known accrual subtotals do not value the nine unknown actual amounts at zero.",
        "unknown_completeness_seal": unknown_seal,
        "unknown_to_zero_refusal": unknown_to_zero,
        "duplicate_A_B_activity_refusal": duplicate_activity,
        "incomplete_category_seal_refusal": incomplete_categories,
        "actual_journal_integrity": {"valid": actual_integrity["valid"], "events": actual_integrity["events"]},
        "synthetic_unearned_claims": {
            "status": "FICTIONAL_SCHEMA_CONFORMANCE",
            "offered_micro_usd": 1_000_000_000,
            "invoiced_micro_usd": 2_000_000_000,
            "pending_micro_usd": 3_000_000_000,
            "report": pending,
            "deposit_refusal": deposit,
            "deposit_boundary": (
                "Pinned main has no deposit action; the unsupported record is refused without changing funds. "
                "This does not qualify the separate active customer-funds extension or accepted deposit custody."
            ),
            "journal_integrity": {"valid": pending_integrity["valid"], "events": pending_integrity["events"]},
        },
        "integrity_is_not_truth": {
            "false_record": false_claim,
            "native_signature_verification": True,
            "independent_arithmetic_truth": False,
            "commercial_value_established": False,
        },
        "authority_replay": {
            "revoked_record_refusal": revoked,
            "explicit_new_local_registry_regrant_verified": True,
            "scope": "Simulated local regrant only; imported content alone never adds a trust anchor.",
            "live_ENS_verified": False,
            "production_authority": False,
        },
        "private_key_or_token_exported": False,
        "modeled_costs_posted_as_actual": False,
    }


def compile_native_plan() -> dict[str, Any]:
    """Invoke the unchanged existing JavaScript compiler and verifier."""
    specs = [
        {
            "goal": "Review the water-reuse investment gate packet and identify unresolved original obligations.",
            "successMetric": "Reconcile cash/depreciation, retain every missing-evidence reason and return a bounded decision.",
            "bounty": "100",
            "duration": 259200,
            "priceWeight": 5000,
        },
        {
            "goal": "If separately authorized, scope the next measurement milestone; no physical pilot is executed here.",
            "successMetric": "Specify quality, long-run operation, residuals, offtake and complete-cost evidence with a resource ceiling.",
            "bounty": "100",
            "duration": 259200,
            "priceWeight": 5000,
        },
    ]
    script = """
const {compilePlan, verifyPlan} = await import(process.argv[2]);
const specs = JSON.parse(process.argv[3]);
const plan = compilePlan(specs);
const verified = verifyPlan(plan);
const changed = structuredClone(plan);
changed.jobs[0].spec.successMetric += ' altered';
let changedRejected = false, reason = '';
try { verifyPlan(changed); } catch (error) { changedRejected = true; reason = String(error.message); }
if (!changedRejected) throw new Error('Altered plan was accepted');
console.log(JSON.stringify({plan, exactRebuild:JSON.stringify(plan)===JSON.stringify(verified),
 changedSpecRejected:changedRejected, changedSpecReason:reason, nodeVersion:process.version}));
"""
    run = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-",
            (REPOSITORY / "docs/assets/nova-studio/plan.mjs").as_uri(),
            json.dumps(specs),
        ],
        input=script,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    result = json.loads(run.stdout)
    assert result["exactRebuild"] and result["changedSpecRejected"]
    result["economic_boundary"] = (
        "The two 100-base-unit AGIALPHA bounties are fictional minimum-schema fixtures, not prices or funding. "
        "No EUR/USD/USDC conversion, customer revenue, ownership or future upside is inferred. "
        "The fixture's calendar-second duration is not a validated three-business-day service SLA."
    )
    result["MARK_status"] = "NOT_EXECUTED"
    result["NovaSeed_status"] = "LOCAL_UNMINTED_PLAN_ONLY"
    result["transaction_count"] = 0
    return result


def run() -> dict[str, Any]:
    """Record narrow interface execution while preserving all live-operation limits."""
    evidence = STUDY / "evidence"
    evidence.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="native-adapter-", dir=evidence) as temporary:
        accounting = accounting_rehearsal(Path(temporary))
    plan = compile_native_plan()
    ordinary = STUDY / "src/ordinary.py"
    ordinary_hash = file_hash(ordinary)
    if ordinary_hash != "4ba3b068d77892dcd54b07fa045e4b31510ddf806aaa53cdf9dcf15b23674fc1":
        raise ValueError("The original frozen ordinary evaluator has changed")
    spec = importlib.util.spec_from_file_location("native_adapter_frozen_ordinary", ordinary)
    if spec is None or spec.loader is None:
        raise ValueError("The frozen evaluator cannot be loaded")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    public_result = evaluator.evaluate(json.loads((STUDY / "inputs/published_case.json").read_text()))
    public_result_hash = hashlib.sha256(
        json.dumps(public_result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    bridge = {
        "schema": "study.reuse-gate-insight-review-envelope.v1",
        "status": "LOCAL_REVIEW_ENVELOPE_NOT_NATIVE_ADMISSION",
        "opportunity": "Industrial nonpotable reuse through paid, conditional evidence milestones",
        "mission": "Reuse Investment Gate Pack",
        "original_obligations": [
            "Same process analytes and actual buyer specifications",
            "No physical, operational or customer acceptance inferred from software checks",
            "Unknown costs retained; reserve, liability and funding constraints preserved",
            "Separate provider USD economics, historical project EUR economics and fictional AGIALPHA plan units",
        ],
        "protocol_sha256": file_hash(STUDY / "protocol/acceptance.json"),
        "source_case_sha256": file_hash(STUDY / "inputs/published_case.json"),
        "conditional_decision": public_result["decision"],
        "ordinary_evaluator_sha256": ordinary_hash,
        "public_result_sha256": public_result_hash,
        "meaning_recheck_required": True,
        "current_authority_regrant_required": True,
        "plan_root": plan["plan"]["planRoot"],
        "live_identity": "UNVERIFIED",
        "MARK": "NOT_EXECUTED",
    }
    commitment = digest("study-insight-review", bridge)
    changed = {**bridge, "conditional_decision": "CONDITIONAL_NEXT_MILESTONE"}
    assert digest("study-insight-review", changed) != commitment
    canonical(bridge)
    code = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()
    return {
        "schema": "study.native-interface-evidence.v1",
        "repository_commit": code,
        "scope": "Executed local interface reuse; not integration completion, canonical release or production authorization.",
        "native_source_bindings": [
            {"path": name, "sha256": file_hash(REPOSITORY / name)} for name in NATIVE_COMPONENTS
        ],
        "adapter_sha256": file_hash(Path(__file__)),
        "python_version": platform.python_version(),
        "accounting": accounting,
        "FusionPlan": plan,
        "public_result_reproduction": public_result,
        "Insight_NovaSeed_review_envelope": bridge,
        "review_envelope_commitment": commitment,
        "changed_decision_changes_commitment": True,
        "limitations": [
            "The review envelope is a local bridge record, not a newly registered Insight or minted Nova-Seed.",
            "Native cryptographic commitments and signatures authenticate content, not scientific or commercial truth.",
            "No live ENS, validator-role change, provider call, customer receipt, wallet request or transaction occurred.",
            "Actual project and model bills remain unmetered; modeled commercial economics are separate study outputs.",
            "Node 24.22.1 execution is scoped conformance, not the repository's pinned Node 22.17.1 release qualification.",
            "The existing main accounting action set does not implement the pending child branch's deposit-custody flow.",
        ],
    }


def main() -> None:
    """Save the safe public result without private journal material."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=STUDY / "evidence/native_adapter.json")
    args = parser.parse_args()
    target = args.output.resolve()
    if not target.is_relative_to(STUDY):
        raise ValueError("Output must remain inside the study directory")
    result = run()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(target),
                "native_source_count": len(NATIVE_COMPONENTS),
                "status": "LOCAL_CONFORMANCE_COMPLETE",
            }
        )
    )


if __name__ == "__main__":
    main()
