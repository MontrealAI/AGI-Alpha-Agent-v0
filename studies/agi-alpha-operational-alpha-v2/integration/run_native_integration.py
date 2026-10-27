# SPDX-License-Identifier: Apache-2.0
"""Reuse frozen native/lifecycle interfaces with the new workflow's actual bytes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT.parents[1] / "agi-alpha-capability-opportunity-v1" / "integration"
PINS = {
    "bridge.py": "6acad454931d3a7b86e254a365a732dba5d0f5866a04f45dbce6c5890de4446a",
    "replay.mjs": "21424aca2d4cbd5ed2553875e5f8120de2a51dcdbf21bdedc12b01534cc969c7",
    "run_integration.py": "9e553e42a4301d107e487e762525e1941dcb80a44fbec43f64f879bb0a7b1251",
    "crypto_controls.mjs": "7767b56c6938ca4353ce5f99e7ad5fdff8212e7029958283498b9d956924db68",
    "source_manifest.json": "3489b4bc2870a1fa17af17566f58d16ef190e8039cc71382dcdb9cfabcbd5ba6",
}
CATEGORIES = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False, sort_keys=True) + "\n", encoding="utf-8")


def load_upstream() -> tuple[Any, Any]:
    for name, expected in PINS.items():
        if sha256(UPSTREAM / name) != expected:
            raise ValueError("Frozen upstream adapter changed: " + name)
    current = sys.modules.get("bridge")
    if current is not None:
        current_file = getattr(current, "__file__", None)
        if not current_file or Path(current_file).resolve() != UPSTREAM / "bridge.py":
            raise ValueError("Unrelated bridge module already imported")
    sys.path.insert(0, str(UPSTREAM))
    import bridge

    bridge.verify_sources()
    spec = importlib.util.spec_from_file_location("preserved_opportunity_conformance", UPSTREAM / "run_integration.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen conformance adapter")
    conformance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conformance)
    return bridge, conformance


def unknown_cost_commands(artifact_digest: str) -> list[dict[str, Any]]:
    commands = []
    for bucket, mission in [("A", "hosted-agent-pilot"), ("B", "workflow-assessment-retention"), ("C", "method-development")]:
        for category in CATEGORIES:
            evidence = hashlib.sha256((artifact_digest + bucket + category).encode()).hexdigest()
            commands.append(
                {
                    "action": "charge",
                    "record": {
                        "activity_id": "unmetered-" + bucket + "-" + category,
                        "mission_id": mission,
                        "bucket": bucket,
                        "category": category,
                        "accrued_micro_usd": None,
                        "paid_micro_usd": 0,
                        "basis": "unknown",
                        "evidence_digest": evidence,
                        "note": "Unreconciled research cost placeholder; no payment evidence is not zero expense.",
                    },
                }
            )
    return commands


def run(artifact: Path, out: Path) -> dict[str, Any]:
    artifact = artifact.resolve()
    if not artifact.is_file():
        raise ValueError("Actual nonempty workflow artifact required")
    artifact_bytes = artifact.read_bytes()
    if not artifact_bytes:
        raise ValueError("Actual nonempty workflow artifact required")
    out.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    snapshot = out / ("source-workflow" + artifact.suffix)
    snapshot.write_bytes(artifact_bytes)
    protocol = {
        "schema": "operational-alpha-native-integration-protocol/v1",
        "source_commit": "231834269599d85e49cfe1ca9917a1a874522d44",
        "native_commit": "80b345828f34fd8a6e592977dd17ef37141305f4",
        "research_lifecycle_commit": "2727262caa52766a78916f2ed81f5afaf668edce",
        "upstream_adapter_pins": PINS,
        "runner_sha256": sha256(Path(__file__)),
        "artifact_name": artifact.name,
        "artifact_sha256": digest,
        "artifact_bytes": len(artifact_bytes),
        "declared_before_execution": True,
        "authority": "Modeled ENS members; actual local encryption and ephemeral signature checks only.",
        "positive_admission": "Artificial monetary conformance fixture, not measured Operational Alpha.",
        "production_scope": "Unsupported arbitrary software workflow; original native scope is not renamed.",
    }
    write(out / "protocol.json", protocol)
    started = time.perf_counter()
    try:
        bridge, conformance = load_upstream()
        original = conformance.run(snapshot, out / "preserved-conformance")
        recovered = out / "preserved-conformance" / ("received-v2" + artifact.suffix)
        received = out / "received-workflow.bin"
        received.write_bytes(recovered.read_bytes())
        ordinary = out / "ordinary-library-workflow.bin"
        ordinary.write_bytes(artifact_bytes)
        native = bridge.replay_native(unknown_cost_commands(digest))
        write(out / "actual-cost-uncertainty.json", native)
        checks = list(original["checks"])
        checks.extend(
            [
                {
                    "name": "actual-workflow-and-recovered-and-library-bytes-equal",
                    "passed": original["artifact_sha256"] == digest
                    and artifact_bytes == received.read_bytes() == ordinary.read_bytes(),
                },
                {
                    "name": "all-actual-cost-buckets-unreconciled",
                    "passed": native["report"]["complete_cost_profit"] is None
                    and native["report"]["available_funds"] is None
                    and native["report"]["unknown_costs"] is True
                    and native["report"]["collected_revenue"] == 0,
                },
            ]
        )
        summary = {
            "schema": "operational-alpha-native-integration/v1",
            "artifact_sha256": digest,
            "passed": sum(c["passed"] for c in checks),
            "total": len(checks),
            "checks": checks,
            "source_files": len(bridge.verify_sources()["files"]),
            "elapsed_seconds": time.perf_counter() - started,
            "retrieved_workflow": received.name,
            "ordinary_library_workflow": ordinary.name,
            "actual_collections_usd": 0,
            "actual_complete_cost_profit": None,
            "live_ens_authentications": 0,
            "frontier_calls_in_this_fixture": 0,
            "empirical_alpha_admission": False,
            "production_admission": "NOT_QUALIFIED_UNSUPPORTED_SOFTWARE_WORKFLOW_SCOPE",
            "recipient_benefit": "Requires separate unfamiliar-task execution; byte transfer is not outcome benefit.",
            "graph_specific_advantage": "Not established; same-content ordinary library carries identical bytes.",
            "historical_labels": "Unchanged upstream conformance retains its earlier scientific namespace and received-v2 name.",
            "no_changes": "Existing registry, native scope, Jobs roles, governance, settlement and upstream sources unchanged.",
        }
        write(out / "summary.json", summary)
        return summary
    except Exception as exc:
        write(
            out / "failed-attempt.json",
            {"type": type(exc).__name__, "error": str(exc), "elapsed_seconds": time.perf_counter() - started},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.artifact, args.out)
    print(json.dumps({k: result[k] for k in ["passed", "total", "artifact_sha256", "production_admission"]}))
    raise SystemExit(0 if result["passed"] == result["total"] else 1)
