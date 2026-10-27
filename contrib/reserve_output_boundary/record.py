# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge, CostLedger
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

from .run import load, save


def record(summary: Path, destination: Path, private_journal: Path) -> dict[str, Any]:
    if load(summary).get("stage") != "confirmation":
        raise ValueError("this handoff requires the actual fresh confirmation summary")
    journal = Journal.initialize(private_journal)
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    ledger = CostLedger(
        journal, TrustRegistry({"boundary-fixture-accountant": TrustAnchor(public_key, frozenset({"accounting"}))})
    )
    evidence = hashlib.sha256(summary.read_bytes()).hexdigest()
    mission = "reserve-output-boundary-confirmation"
    request = {
        "opportunity_id": "research-reserve-feasibility",
        "mission_id": mission,
        "artifact_sha256": evidence,
        "mode": "public-synthetic-only",
        "execution": load(summary)["stage"],
        "acceptance": "separate executable reference, not customer acceptance",
        "authority": "none",
    }
    with journal.transaction() as connection:
        journal.append(connection, "@reserve-output-boundary:mission", request)
    charge = Charge(
        activity_id="boundary-complete-incremental-assessment",
        mission_id=mission,
        bucket="B",
        category="overhead",
        accrued_micro_usd=None,
        paid_micro_usd=0,
        basis="unknown",
        evidence_digest=evidence,
        note="Complete incremental engineering assessment including model/tool use, development, failed clone, tests, retries, verification and handoff. Aggregate allocation unknown; not charged again to originating delivery A.",
    )
    command = {
        "journal_identity": journal.identity,
        "operation_id": "boundary-assessment-cost-once",
        "action": "charge",
        "record": charge.model_dump(),
    }
    signed = sign_record(key, "boundary-fixture-accountant", "flywheel-cost-command", command)
    ledger.apply(signed)
    ledger.apply(signed)
    duplicate_refused = False
    try:
        ledger.apply(
            sign_record(
                key,
                "boundary-fixture-accountant",
                "flywheel-cost-command",
                {**command, "operation_id": "boundary-duplicate-cost"},
            )
        )
    except Conflict:
        duplicate_refused = True
    report = ledger.report(mission)
    assert duplicate_refused and len(ledger.snapshot()["charges"]) == 1
    assert report["complete_cost_profit"] is None and report["unknown_costs"]
    result = {
        "schema": "reserve-output-boundary-native-record/v1",
        "mode": "local-fixture-not-live-ens",
        "mission": request,
        "accounting_public_key": public_key,
        "signed_cost": signed.model_dump(mode="json"),
        "report": report,
        "idempotent_replay_charged_once": True,
        "duplicate_activity_refused": duplicate_refused,
        "checkpoint": journal.verify(),
        "private_keys_exported": False,
        "recovery_limit": "Uses existing local Journal. This packet is not authority and cannot recover or roll back private operator state.",
    }
    save(destination, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("summary", "destination", "private-journal"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    result = record(args.summary, args.destination, args.private_journal)
    print(
        json.dumps(
            {
                "unknown_costs": result["report"]["unknown_costs"],
                "complete_profit": result["report"]["complete_cost_profit"],
            }
        )
    )


if __name__ == "__main__":
    main()
