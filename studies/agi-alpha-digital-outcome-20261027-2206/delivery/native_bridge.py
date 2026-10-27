# SPDX-License-Identifier: Apache-2.0
"""Bind observed research checks to the existing local journal and unknown-cost ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "native_reuse"))

SOURCE_COMMIT = "3947e4ec8fd74ad40e13e8ff825a149fa98a10e9"
ARMS = ("ordinary", "expert", "conventional")


def capture(experiment: Path, temporary_root: Path | None = None) -> dict[str, Any]:
    """Record research acceptance and explicitly unknown actual costs, without customer approval."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from alpha_factory_v1.core.eval.fitness import compute_fitness
    from alpha_factory_v1.core.runtime.store import Journal, digest
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, Charge, CostLedger
    from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

    evidence = {}
    rows = []
    for arm in ARMS:
        path = experiment / f"{arm}_score.json"
        evidence[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        scores = json.loads(path.read_text())
        for check in scores["checks"]:
            rows.append(
                {
                    "task_id": f"{arm}/{check['id']}",
                    "pass": check["pass"],
                    "time_ms": check["wall_seconds"] * 1000,
                }
            )
    binding = digest(evidence)
    mission_id = "digital-beta-20261027"
    with tempfile.TemporaryDirectory(prefix="alpha-local-journal-", dir=temporary_root) as temporary:
        journal = Journal.initialize(Path(temporary) / "journal")
        key = Ed25519PrivateKey.generate()
        principal = "local-research-accounting"
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        trust = TrustRegistry({principal: TrustAnchor(public, frozenset({"accounting"}))})
        ledger = CostLedger(journal, trust)
        with journal.transaction() as connection:
            journal.append(
                connection,
                "@research:" + mission_id,
                {
                    "record_kind": "local_research_evidence",
                    "evidence_digest": binding,
                    "public_missions": 1,
                    "implementation_trials_per_arm": 1,
                    "unique_confirmation_cases": 64,
                    "implementation_checks": len(rows),
                    "passed_checks": sum(row["pass"] for row in rows),
                    "native_customer_acceptance": False,
                    "observed_customer_receipts_micro_usd": 0,
                    "provider_cost_meter_available": False,
                },
            )
        for category in sorted(CATEGORIES):
            charge = Charge(
                activity_id=f"{mission_id}:{category}",
                mission_id=mission_id,
                bucket="A",
                category=category,
                accrued_micro_usd=None,
                paid_micro_usd=0,
                basis="unknown",
                evidence_digest=binding,
                note=(
                    "Actual complete study allocation is unmetered. Zero paid amounts mean no receipt recorded, "
                    "not zero cost. Hypothetical commercial scenarios remain outside this actual-cost ledger."
                ),
            )
            command = {
                "journal_identity": journal.identity,
                "operation_id": "record-" + category,
                "action": "charge",
                "record": charge.model_dump(),
            }
            ledger.apply(sign_record(key, principal, "flywheel-cost-command", command))
        with journal.transaction() as connection:
            events = [
                {
                    "sequence": row[0],
                    "mission": row[1],
                    "body_json": row[2],
                    "sha256": row[3],
                    "signature": row[4],
                }
                for row in connection.execute(
                    "SELECT seq, mission, body, hash, signature FROM events ORDER BY seq"
                ).fetchall()
            ]
        return {
            "edition": "DIGITAL-20261027-R1",
            "source_commit": SOURCE_COMMIT,
            "evidence_file_hashes": evidence,
            "evidence_digest": binding,
            "fitness": compute_fitness(rows),
            "actual_costs": ledger.report(mission_id),
            "journal_verification": journal.verify(),
            "public_signed_events": events,
            "local_accounting_public_key": public,
            "identity_scope": "Ephemeral local test identity. No ENS, external authority or customer identity claim.",
            "acceptance_scope": "Research contract accepted; native commercial delivery/approval not asserted.",
            "receipts_micro_usd": 0,
            "known_actual_complete_cost_micro_usd": None,
            "model_scenarios_location": "economics/; assumptions are not inserted as measured actual charges.",
        }


def main() -> None:
    """Emit a public-only journal capture; destroy its temporary private keys afterward."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=Path(__file__).resolve().parents[1] / "experiment")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    result = capture(arguments.experiment, arguments.output.parent)
    arguments.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"journal_verification": result["journal_verification"], "receipts_micro_usd": 0}))


if __name__ == "__main__":
    main()
