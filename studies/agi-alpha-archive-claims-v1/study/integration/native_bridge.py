# SPDX-License-Identifier: Apache-2.0
"""Research adapter for unchanged, pinned AGI ALPHA components."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True
COMMIT = "47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4"
HERE = Path(__file__).resolve().parent
MANIFEST = HERE.parent / "provenance" / "native_sources.json"
SCOPE = (
    "Executed local research bridge using unchanged native code. Supplied neutral priority scores are not "
    "forecasts, truth, novelty judgments or commercial validation. Nova-Seeds remain plaintext research drafts; "
    "FusionPlan token amounts are inert commitment inputs. No minting, listing, payment, live ENS or MARK "
    "activation occurs. Local signing keys are temporary fixtures and are not shared or retained."
)


def canonical(value: Any) -> bytes:
    """Encode bounded JSON deterministically."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    """Commit to exact structured content."""
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Write an inspectable JSON artifact."""
    path.write_bytes(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n")


def verify_sources(root: Path) -> dict[str, Any]:
    """Verify every retained source byte before importing upstream code."""
    manifest = json.loads(MANIFEST.read_text())
    if manifest["commit"] != COMMIT:
        raise ValueError("Native source manifest does not name the frozen commit")
    for record in manifest["files"]:
        path = root / record["path"]
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Native source path is absent or not an ordinary contained file: " + record["path"])
        data = path.read_bytes()
        if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Pinned native source bytes differ: " + record["path"])
    return {
        "commit": COMMIT,
        "files": len(manifest["files"]),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
    }


def load_native(root: Path) -> dict[str, Any]:
    """Import exact retained native modules after their source verification."""
    verify_sources(root)
    sys.path.insert(0, str(root.resolve()))
    from alpha_factory_v1.demos.alpha_agi_insight_v0 import discovery
    from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.flywheel_capsules import CapsuleManifest
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge, CostLedger, CATEGORIES
    from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

    allowed = {record["path"] for record in json.loads(MANIFEST.read_text())["files"]}
    for name, module in list(sys.modules.items()):
        if name.startswith("alpha_factory_v1"):
            filename = getattr(module, "__file__", None)
            if filename and not Path(filename).resolve().is_relative_to(root.resolve()):
                raise ValueError(
                    "An installed or previously imported module displaced the pinned native source: " + name
                )
            if filename and str(Path(filename).resolve().relative_to(root.resolve())) not in allowed:
                raise ValueError("Loaded native module is absent from the verified dependency closure: " + name)
    return {
        "discovery": discovery,
        "compile_plan": compile_plan,
        "verify_plan": verify_plan,
        "Journal": Journal,
        "CapsuleManifest": CapsuleManifest,
        "Charge": Charge,
        "CostLedger": CostLedger,
        "CATEGORIES": CATEGORIES,
        "TrustAnchor": TrustAnchor,
        "TrustRegistry": TrustRegistry,
        "sign_record": sign_record,
    }


def validate_metadata(metadata: Any) -> dict[str, Any]:
    """Require an explicit research witness and executable milestone terms."""
    required = {"candidate", "sources", "witness", "rights", "uncertainty", "milestones"}
    if not isinstance(metadata, dict) or not required <= set(metadata):
        raise ValueError("Metadata requires candidate, sources, witness, rights, uncertainty and milestones")
    candidate = metadata["candidate"]
    if not isinstance(candidate, dict) or not {"id", "title", "thesis", "goal", "successMetric"} <= set(candidate):
        raise ValueError("Candidate is missing native Insight fields")
    if not isinstance(metadata["sources"], list) or not 1 <= len(metadata["sources"]) <= 32:
        raise ValueError("Supply 1 through 32 sources")
    for field in ("witness", "rights", "uncertainty"):
        if not metadata[field]:
            raise ValueError("Research sidecar field may not be empty: " + field)
    milestones = metadata["milestones"]
    if not isinstance(milestones, list) or not 1 <= len(milestones) <= 127:
        raise ValueError("Supply 1 through 127 construction/verification milestones")
    seen: set[str] = set()
    for item in milestones:
        if not isinstance(item, dict) or not {
            "id",
            "goal",
            "successMetric",
            "depends_on",
            "budget",
            "permissions",
            "falsifiers",
        } <= set(item):
            raise ValueError("Every milestone needs goal, acceptance, dependencies, budget, permissions and falsifiers")
        if item["id"] in seen or not isinstance(item["depends_on"], list) or not set(item["depends_on"]) <= seen:
            raise ValueError("Milestones require unique IDs and dependency order")
        if not item["budget"] or not item["permissions"] or not item["falsifiers"]:
            raise ValueError("A milestone cannot omit budgets, permissions or falsifiers")
        seen.add(item["id"])
    canonical(metadata)
    return metadata


def scenario_from(metadata: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    """Project research metadata into the existing strict Insight schema."""
    candidate = metadata["candidate"]
    sources = [
        {
            "id": source["id"],
            "title": source["title"],
            "url": source["url"],
            "excerpt": source["excerpt"],
            "kind": source.get("kind", "public-excerpt"),
        }
        for source in metadata["sources"]
    ]
    metrics = native["discovery"].METRICS
    return {
        "schema": native["discovery"].SCHEMA,
        "id": candidate["id"],
        "title": candidate["title"],
        "note": "Single already-selected research candidate; neutral supplied scores exercise native provenance, not comparative discovery or forecast accuracy.",
        "weights": dict.fromkeys(metrics, 2500),
        "policy": {"reviewMinutes": 60, "minScoreBps": 5000, "minCoverageBps": 10000, "jobBountyTokens": 1},
        "sources": sources,
        "opportunities": [
            {
                "id": candidate["id"],
                "sector": candidate.get("sector", "research instrument"),
                "title": candidate["title"],
                "thesis": candidate["thesis"],
                "goal": candidate["goal"],
                "successMetric": candidate["successMetric"],
                "reviewMinutes": 60,
                "signals": {
                    metric: {"low": 5000, "base": 5000, "high": 5000, "source": sources[i % len(sources)]["id"]}
                    for i, metric in enumerate(metrics)
                },
            }
        ],
    }


def scope_refusal(metadata: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    """Exercise the unchanged production capsule's unsupported-scope boundary."""
    from pydantic import ValidationError

    record = {
        "skill_id": "research-instrument-fixture",
        "version": 1,
        "origin_mission": "research-origin-fixture",
        "origin_record_digest": digest(metadata),
        "origin_agent": "fixture.agent.agi.eth",
        "origin_wallet": "0x" + "1" * 40,
        "content_digest": digest(metadata["witness"]),
        "supported_scope": "research-new-instrument/v1",
        "prerequisites": [],
        "limitations": "Synthetic schema probe; no origin, network identity, customer acceptance or production qualification is claimed.",
        "rights": "cleared-for-authenticated-network",
        "rights_evidence": digest(metadata["rights"]),
        "dependency_digests": [],
    }
    try:
        native["CapsuleManifest"].model_validate(record)
    except ValidationError as exc:
        errors = exc.errors(include_url=False, include_input=False)
        if not any(error["loc"] == ("supported_scope",) for error in errors):
            raise
        return {
            "unsupported_scope_refused": True,
            "errors": errors,
            "fixture_identity": True,
            "production_admission": "NOT_QUALIFIED",
        }
    raise AssertionError("Unsupported scientific scope was accepted by production capsule")


def unknown_accounting(native: dict[str, Any], metadata_digest: str) -> dict[str, Any]:
    """Run a temporary native accounting fixture without inventing a research bill."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    key = Ed25519PrivateKey.generate()
    principal = "local-research-accounting-fixture"
    public_key = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    trust = native["TrustRegistry"]({principal: native["TrustAnchor"](public_key, frozenset({"accounting"}))})
    with tempfile.TemporaryDirectory(prefix="agi-native-research-") as temporary:
        journal = native["Journal"].initialize(Path(temporary) / "journal")
        ledger = native["CostLedger"](journal, trust)
        charge = native["Charge"](
            activity_id="authoring-unknown-fixture",
            mission_id="research-origin-fixture",
            bucket="C",
            category="model",
            accrued_micro_usd=None,
            paid_micro_usd=0,
            basis="unknown",
            evidence_digest=metadata_digest,
            note="Accounting-boundary fixture for unavailable authoring telemetry; no actual bill, paid job or zero total cost is asserted.",
        )

        def command(action: str, record: dict[str, Any], operation: str) -> Any:
            payload = {
                "journal_identity": journal.identity,
                "operation_id": operation,
                "action": action,
                "record": record,
            }
            return ledger.apply(native["sign_record"](key, principal, "flywheel-cost-command", payload))

        command("charge", charge.model_dump(), "unknown-cost-fixture")
        report = ledger.report("research-origin-fixture")
        try:
            command(
                "seal-investment",
                {
                    "mission_id": "research-origin-fixture",
                    "evidence_digest": metadata_digest,
                    "categories": sorted(native["CATEGORIES"]),
                },
                "rejected-completeness-fixture",
            )
        except ValueError as exc:
            refusal = str(exc)
        else:
            raise AssertionError("Incomplete unknown-cost fixture acquired a complete-cost seal")
        if (
            report["unknown_costs"] is not True
            or report["complete_cost_profit"] is not None
            or report["available_funds"] is not None
            or report["collected_revenue"] != 0
        ):
            raise AssertionError("Native ledger converted unavailable costs into a complete profit")
        checked = journal.verify()
    return {
        "evidence_class": "executed native accounting boundary with temporary local fixture",
        "report": report,
        "complete_cost_seal_refused": True,
        "refusal": refusal,
        "signature_chain_verified": True,
        "journal_events": checked["events"],
        "actual_study_cost": "unknown; this fixture is not a substitute for actual accounting",
        "private_keys_persisted": False,
    }


def run(metadata: dict[str, Any], output: Path, repo: Path) -> dict[str, Any]:
    """Execute the bridge, save exact artifacts and retain adverse controls."""
    metadata = validate_metadata(metadata)
    source_check = verify_sources(repo)
    native = load_native(repo)
    if output.exists():
        raise ValueError("Output already exists; preserve it and choose a fresh destination")
    output.mkdir(parents=True)
    metadata_digest = digest(metadata)
    report = native["discovery"].evaluate(scenario_from(metadata, native))
    native["discovery"].verify(report)
    if report["result"]["selectedIds"] != [metadata["candidate"]["id"]]:
        raise AssertionError("The neutral single-candidate research mapping did not produce a review draft")
    native_dir = output / "insight"
    native_dir.mkdir()
    for filename, data in native["discovery"].artifacts(report).items():
        (native_dir / filename).write_bytes(data)
    jobs = list(report["result"]["jobs"])
    for milestone in metadata["milestones"]:
        jobs.append(
            {
                "goal": milestone["goal"],
                "successMetric": milestone["successMetric"],
                "bounty": "100",
                "duration": milestone.get("duration_seconds", 3600),
                "priceWeight": 5000,
            }
        )
    plan = native["compile_plan"](jobs)
    plan_check = native["verify_plan"](plan)
    altered = copy.deepcopy(plan)
    altered["jobs"][0]["spec"]["goal"] += " altered"
    try:
        native["verify_plan"](altered)
    except ValueError as exc:
        plan_refusal = str(exc)
    else:
        raise AssertionError("Tampered native FusionPlan was accepted")
    altered_dossier = copy.deepcopy(report)
    altered_dossier["result"]["ranking"][0]["scores"]["base"] += 1
    try:
        native["discovery"].verify(altered_dossier)
    except ValueError as exc:
        dossier_refusal = str(exc)
    else:
        raise AssertionError("Tampered native Insight score was accepted")
    sidecar = {
        "schema": "agi-alpha.research-opportunity-sidecar.v1",
        "metadata_sha256": metadata_digest,
        "metadata": metadata,
        "insight_dossier_sha256": report["sha256"],
        "fusion_plan_sha256": digest(plan),
        "fusion_plan_root": plan["planRoot"],
        "scope": SCOPE,
        "plan_job_mapping": [{"index": 0, "role": "native opportunity verification"}]
        + [
            {"index": i + 1, "role": "research milestone", "milestone_id": milestone["id"]}
            for i, milestone in enumerate(metadata["milestones"])
        ],
        "mark_state": "NOT_ACTIVATED; actual chain context is neither supplied nor invented",
        "commercial_commitment": "NONE",
        "token_amounts": "INERT_DRAFT_BASE_UNITS_NOT_USD_OR_REVENUE",
    }
    seed = {
        "schema": "agi-alpha.research-nova-seed.v1",
        "state": "UNMINTED_UNFUNDED_RESEARCH_DRAFT",
        "opportunity": metadata["candidate"],
        "native_nova_seed_draft": report["result"]["novaSeedDrafts"][0],
        "research_sidecar_sha256": digest(sidecar),
        "sources": metadata["sources"],
        "witness": metadata["witness"],
        "rights": metadata["rights"],
        "uncertainty": metadata["uncertainty"],
        "next_experiment": metadata["milestones"][0],
        "fusion_plan_root": plan["planRoot"],
        "fusion_plan_sha256": digest(plan),
        "scope": SCOPE,
    }
    controls = {
        "native_sources": source_check,
        "insight_verifies": True,
        "fusion_plan": plan_check,
        "tampered_plan_refused": True,
        "tampered_plan_reason": plan_refusal,
        "tampered_insight_refused": True,
        "tampered_insight_reason": dossier_refusal,
        "production_scope": scope_refusal(metadata, native),
        "accounting": unknown_accounting(native, metadata_digest),
        "scope": SCOPE,
    }
    for filename, value in (
        ("input.json", metadata),
        ("fusion-plan.json", plan),
        ("research-sidecar.json", sidecar),
        ("research-nova-seed.json", seed),
        ("native-controls.json", controls),
    ):
        write_json(output / filename, value)
    write_json(
        output / "environment.json",
        {
            "python": sys.version,
            "dependency_versions": {
                name: importlib.metadata.version(name)
                for name in ("pydantic", "cryptography", "eth-hash", "pycryptodome", "numpy", "PyYAML", "httpx")
            },
            "source_commit": COMMIT,
            "source_manifest_sha256": source_check["manifest_sha256"],
            "network_calls": 0,
        },
    )
    files = [
        {
            "path": str(path.relative_to(output)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        for path in sorted(output.rglob("*"))
        if path.is_file()
    ]
    write_json(
        output / "MANIFEST.json",
        {"schema": "agi-alpha.native-bridge-output.v1", "metadata_sha256": metadata_digest, "files": files},
    )
    return controls


def main() -> None:
    """Run a new research bridge output from declared JSON metadata."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=HERE / "upstream")
    args = parser.parse_args()
    result = run(json.loads(args.input.read_text()), args.output, args.repo.resolve())
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sources": result["native_sources"]["files"],
                "plan_valid": result["fusion_plan"]["valid"],
                "tamper_refused": result["tampered_plan_refused"],
                "production_admission": result["production_scope"]["production_admission"],
                "complete_profit": result["accounting"]["report"]["complete_cost_profit"],
            }
        )
    )


if __name__ == "__main__":
    main()
