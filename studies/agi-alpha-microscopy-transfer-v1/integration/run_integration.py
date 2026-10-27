# SPDX-License-Identifier: Apache-2.0
"""Exercise inherited interfaces for microscopy artifact transfer with labeled fixtures.

Adapted from immutable capability-opportunity-v1 integration/run_integration.py at 231834269599d85e49cfe1ca9917a1a874522d44.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from bridge import ROOT, replay_native, run_lifecycle, verify_sources


def fixture_candidate(path: Path, shared: bool = True, delta: int = 100) -> dict[str, Any]:
    """Artificial monetary pairs test the lifecycle, never empirical Alpha."""
    return {
        "id": "microscopy-instrument",
        "version": 1,
        "artifact_path": str(path),
        "shared": shared,
        "expected_artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "paired_trials": [
            {
                "probeId": f"synthetic-control-{i}",
                "clusterId": f"synthetic-{i}",
                "fresh": True,
                "baseline": {"netMissionValueCents": 0},
                "candidate": {"netMissionValueCents": delta},
            }
            for i in range(8)
        ],
        "lifecycle_cost_cents": 100,
        "evaluation_cost_cents": 100,
        "forecast_uses": 10,
        "correctness_passed": True,
        "replay_available": True,
        "boundary_passed": True,
        "provenance_digest": "ARTIFICIAL_MONETARY_CONTROL_NOT_EMPIRICAL_ALPHA",
    }


def conformance_commands() -> list[dict[str, Any]]:
    """Construct a wholly synthetic complete A/B/C ledger fixture."""
    categories = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]

    def digest(value: Any) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    commands: list[dict[str, Any]] = []
    for action, amount in [("capital", 10_000_000), ("invoice", 9_000_000)]:
        commands.append(
            {
                "action": action,
                "record": {
                    "record_id": action,
                    "mission_id": "synthetic-enterprise",
                    "amount_micro_usd": amount,
                    "evidence_digest": digest(action),
                },
            }
        )
    for bucket in ["A", "B", "C"]:
        mission = "synthetic-" + bucket
        for category in categories:
            amount = {"A": 100_000, "B": 20_000, "C": 30_000}[bucket]
            commands.append(
                {
                    "action": "charge",
                    "record": {
                        "activity_id": bucket + "-" + category,
                        "mission_id": mission,
                        "bucket": bucket,
                        "category": category,
                        "accrued_micro_usd": amount,
                        "paid_micro_usd": amount // 2,
                        "basis": "attested",
                        "evidence_digest": digest([bucket, category]),
                        "note": "SYNTHETIC CONFORMANCE AMOUNT; not a price, invoice or research expense.",
                    },
                }
            )
        commands.append(
            {
                "action": {"A": "seal", "B": "seal-retention", "C": "seal-investment"}[bucket],
                "record": {
                    "mission_id": mission,
                    "categories": categories,
                    "evidence_digest": digest(["seal", bucket]),
                },
            }
        )
    commands.append(
        {
            "action": "collection",
            "record": {
                "record_id": "synthetic-collection",
                "mission_id": "synthetic-A",
                "amount_micro_usd": 5_000_000,
                "evidence_digest": digest("synthetic-collection"),
            },
        }
    )
    commands.append({"action": "reserve", "record": 1_000_000})
    return commands


def run(path: Path, out: Path) -> dict[str, Any]:
    """Run source, bytes, access and accounting controls; preserve declared scope."""
    if out.exists() or out.is_symlink():
        raise FileExistsError("choose a new output directory; prior attempts are immutable")
    manifest = verify_sources()
    candidate = fixture_candidate(path)
    key = "microscopy-instrument@1"
    ops = [
        {"action": "retrieve", "key": key, "member": m}
        for m in ["atlas.agent.agi.eth", "lyra.agent.agi.eth", "orion.agent.agi.eth", "validator.agent.agi.eth"]
    ]
    ops += [
        {"action": "retrieve", "key": key, "member": m}
        for m in ["unknown.agent.agi.eth", "nested.atlas.agent.agi.eth", "validator.club.agi.eth"]
    ]
    ops += [
        {"action": "export", "key": key},
        {"action": "execute", "key": key},
        {"action": "revoke", "key": key},
        {"action": "retrieve", "key": key},
    ]
    shared = run_lifecycle([candidate], ops)
    checks = [{"name": "unchanged-upstream-source-closure", "passed": True, "files": len(manifest["files"])}]
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    transfer = None
    for i, row in enumerate(shared["operations"]):
        result = row["result"]
        if i < 4:
            received = result.get("transferredArtifact", {})
            raw = base64.b64decode(received.get("content", ""))
            passed = result.get("ok") is True and raw == data and received.get("sha256") == sha
            checks.append(
                {
                    "name": "network-member-identical-byte-retrieval",
                    "member": row["operation"]["member"],
                    "passed": passed,
                }
            )
            if i == 1 and passed:
                transfer = raw
        elif i != 9:
            checks.append(
                {
                    "name": [
                        "unknown-member-refused",
                        "nested-name-refused",
                        "jobs-club-role-unmodified",
                        "export-right-refused",
                        "separate-execution-authority-required",
                        "revoke-transition",
                        "revoked-capability-refused",
                    ][i - 4],
                    "passed": result.get("ok") is False,
                    "result": result,
                }
            )
    private = run_lifecycle(
        [fixture_candidate(path, shared=False)],
        [
            {"action": "retrieve", "key": key, "member": "atlas.agent.agi.eth"},
            {"action": "retrieve", "key": key, "member": "lyra.agent.agi.eth"},
        ],
    )
    checks.append(
        {
            "name": "private-owner-only",
            "passed": private["operations"][0]["result"].get("ok") is True
            and private["operations"][1]["result"].get("ok") is False,
        }
    )
    negative = run_lifecycle([fixture_candidate(path, delta=-100)], [{"action": "retrieve", "key": key}])
    checks.append(
        {
            "name": "negative-conditional-alpha-refused",
            "passed": negative["candidates"][0]["assessment"]["verdict"] == "reject"
            and negative["operations"][0]["result"].get("ok") is False,
        }
    )
    changed_beta = run_lifecycle(
        [candidate], [{"action": "beta-update", "beta_version": "stronger-beta-v2"}, {"action": "retrieve", "key": key}]
    )
    checks.append(
        {
            "name": "changed-beta-invalidates-prior-admission",
            "passed": changed_beta["operations"][1]["result"].get("ok") is False,
        }
    )
    changed_mission = run_lifecycle(
        [candidate],
        [{"action": "retrieve", "key": key, "mission": {"scopeDigest": "0" * 64}}],
    )
    checks.append(
        {
            "name": "new-mission-meaning-requires-fresh-scope",
            "passed": changed_mission["operations"][0]["result"].get("ok") is False,
            "reason": "A prior microscopy scope cannot authorize a different measurement meaning.",
        }
    )
    duplicate = run_lifecycle([candidate, candidate])
    checks.append(
        {
            "name": "version-history-cannot-overwrite",
            "passed": "VERSION_ALREADY_EXISTS" in duplicate["candidates"][1].get("error", ""),
        }
    )
    selective = fixture_candidate(path)
    selective["rights"] = {
        "shareable": True,
        "retrieve": ["lyra.agent.agi.eth"],
        "execute": "network",
        "compose": "network",
        "export": False,
    }
    rights = run_lifecycle([selective])
    checks.append(
        {
            "name": "shareable-means-all-authorized-members",
            "passed": "SHAREABLE_REQUIRES_NETWORK_AVAILABILITY" in rights["candidates"][0].get("error", ""),
        }
    )
    leaked = run_lifecycle([candidate], protected_material=[base64.b64encode(data).decode("ascii")])
    checks.append(
        {
            "name": "registered-protected-material-excluded",
            "passed": "PROTECTED_EVALUATION_MATERIAL" in leaked["candidates"][0].get("error", ""),
        }
    )
    mismatch = dict(candidate)
    mismatch["expected_artifact_sha256"] = "0" * 64
    try:
        run_lifecycle([mismatch])
        passed = False
    except ValueError:
        passed = True
    checks.append({"name": "changed-frozen-artifact-refused", "passed": passed})
    crypto = json.loads(
        subprocess.check_output([shutil.which("node") or "node", str(ROOT / "crypto_controls.mjs")], text=True)
    )
    checks += crypto["controls"]
    native = replay_native(conformance_commands(), controls=True)
    checks += native["controls"]
    checks.append(
        {
            "name": "capital-and-invoice-are-not-collected-revenue",
            "passed": native["reports_after_each_command"][1]["collected_revenue"] == 0,
        }
    )
    checks.append(
        {
            "name": "disjoint-complete-cost-profit-reconciles",
            "passed": native["report"]["costs"] == {"A": 900_000, "B": 180_000, "C": 270_000}
            and native["report"]["complete_cost_profit"] == 3_650_000
            and native["report"]["available_funds"] == 12_650_000,
        }
    )
    unknown = replay_native(
        [
            {
                "action": "charge",
                "record": {
                    "activity_id": "actual-authoring-unmetered",
                    "mission_id": "actual-research",
                    "bucket": "C",
                    "category": "human",
                    "accrued_micro_usd": None,
                    "paid_micro_usd": 0,
                    "basis": "unknown",
                    "evidence_digest": sha,
                    "note": "Actual authoring and review expense unknown; zero paid evidence is not zero cost.",
                },
            }
        ]
    )
    checks.append(
        {
            "name": "unknown-costs-block-complete-profit-and-available-funds",
            "passed": unknown["report"]["complete_cost_profit"] is None
            and unknown["report"]["available_funds"] is None
            and unknown["report"]["collected_revenue"] == 0,
        }
    )
    out.mkdir(parents=True, exist_ok=False)
    if transfer is not None:
        (out / ("received-artifact" + path.suffix)).write_bytes(transfer)
    records = {
        "shared": shared,
        "private": private,
        "negative": negative,
        "changed_beta": changed_beta,
        "changed_mission": changed_mission,
        "duplicate": duplicate,
        "selective_rights": rights,
        "registered_protected": leaked,
        "native_synthetic": native,
        "native_actual_unknown": unknown,
        "crypto": crypto,
    }
    for name, record in records.items():
        (out / (name + ".json")).write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    result = {
        "schema": "microscopy-integration-controls/v1",
        "artifact_sha256": sha,
        "artifact_bytes": len(data),
        "artifact_filename": path.name,
        "checks": checks,
        "passed": sum(c["passed"] for c in checks),
        "total": len(checks),
        "scope": "Executable interface conformance using actual microscopy artifact bytes and artificial monetary evidence.",
        "capability_provenance": "Constructed instrument implementing known measurement formulas; not trained model weights.",
        "empirical_alpha_admission": False,
        "fresh_transfer_claim": False,
        "live_ens_authentications": 0,
        "actual_model_calls": 0,
        "actual_revenue_usd": 0,
        "production_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
        "execution_boundary": "Lifecycle retrieval does not execute the artifact. A separate recipient replay must do so.",
        "copy_boundary": "Revocation blocks new mediated access; it cannot erase already retrieved bytes.",
        "graph_specific_advantage": "Not established; identical authorized library bytes are a parity control.",
    }
    (out / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    summary = run(arguments.artifact, arguments.out)
    print(json.dumps({k: summary[k] for k in ["passed", "total", "artifact_sha256", "production_admission"]}))
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
