# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, copy, hashlib, importlib.metadata, json, os, platform, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
COMMIT = "47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4"
sys.dont_write_bytecode = True

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def read_json(path: Path) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("Duplicate JSON key: " + key)
            out[key] = value
        return out
    def nonfinite(value: str) -> None:
        raise ValueError("Non-finite input: " + value)
    raw = path.read_bytes()
    if len(raw) > 250_000:
        raise ValueError("Study input exceeds 250 KB")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)

def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")

def verify_sources(repo: Path) -> dict[str, Any]:
    lock = read_json(ROOT / "source-lock.json")
    if lock["commit"] != COMMIT:
        raise ValueError("Wrong pinned upstream commit")
    for row in lock["files"]:
        target = repo / row["path"]
        if not target.is_file() or target.is_symlink():
            raise ValueError("Missing or nonordinary upstream source: " + row["path"])
        raw = target.read_bytes()
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError("Changed upstream source: " + row["path"])
    if (repo / ".git").exists():
        observed = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        if observed != COMMIT:
            raise ValueError("Repository HEAD differs from pinned research source")
    return lock

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=ROOT / "upstream")
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.absolute()
    lock = verify_sources(repo)
    request = read_json(args.input)
    required = {"study_id", "opportunity", "milestones", "cost_sample", "rights"}
    if not isinstance(request, dict) or not required <= set(request):
        raise ValueError("Input requires study_id, opportunity, milestones, cost_sample, rights")
    if not isinstance(request["opportunity"], dict) or not isinstance(request["milestones"], list):
        raise ValueError("Opportunity must be an object and milestones a list")
    if request["rights"].get("public_research_only") is not True:
        raise ValueError("This adapter accepts public research content only")
    if request["rights"].get("contains_customer_secrets") is not False:
        raise ValueError("Public seed cannot contain customer secrets")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output must be a new directory; previous evidence is preserved")
    output.mkdir(parents=True)
    write_json(output / "input.json", request)
    write_json(output / "source-lock.json", lock)
    sys.path.insert(0, str(repo))
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge, CostLedger, CATEGORIES
    from alpha_factory_v1.core.runtime.successor.flywheel_capsules import CapsuleManifest
    from alpha_factory_v1.core.runtime.successor.flywheel_access import AccessRequest, ENSAuthority, ENSPins, ResourceAccess, ServiceIdentity
    from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

    checks: list[dict[str, Any]] = []
    def refused(name: str, operation: Any) -> None:
        try:
            operation()
        except (ValueError, RuntimeError, KeyError) as exc:
            checks.append({"name": name, "passed": True, "observed": "refused", "reason": str(exc)})
        else:
            raise AssertionError("Expected refusal was accepted: " + name)

    jobs = []
    for milestone in request["milestones"]:
        jobs.append({"goal": milestone["goal"], "successMetric": milestone["acceptance"],
                     "bounty": milestone.get("fixture_bounty_base_units", "100"),
                     "duration": milestone.get("duration_seconds", 86400), "priceWeight": milestone.get("price_weight", 6000)})
    plan = compile_plan(jobs)
    plan_check = verify_plan(plan)
    checks.append({"name": "native_fusionplan_rebuild", "passed": plan_check["valid"], "jobs": plan_check["jobs"]})
    tampered = copy.deepcopy(plan)
    tampered["jobs"][0]["spec"]["successMetric"] += " changed"
    refused("fusionplan_metric_substitution", lambda: verify_plan(tampered))
    write_json(output / "fusion-plan.json", plan)
    write_json(output / "fusion-plan-verification.json", {**plan_check, "economic_status": "Minimum parser-valid token bounties are fixture commitments only, unrelated to USD pricing; no funds or on-chain action."})
    genome = {"schema": "agialpha.novaseed.genome.v1", "study_id": request["study_id"],
              "title": request["opportunity"].get("title", request["study_id"]),
              "data_mode": "public_research_opportunity", "opportunity": request["opportunity"],
              "fusion_plan": plan, "experiment_milestones": request["milestones"], "rights": request["rights"],
              "source_commit": COMMIT, "admission": "Research-only; no current protected production scope or live ENS authority established."}
    write_json(output / "novaseed-payload.json", genome)
    node = subprocess.run(["node", str(ROOT / "seed_roundtrip.mjs"), str(repo), str(output / "novaseed-payload.json"), str(output)], capture_output=True, text=True)
    (output / "node-execution.txt").write_text(node.stdout + node.stderr, encoding="utf-8")
    if node.returncode:
        raise RuntimeError("Native Nova-Seed adapter failed; see node-execution.txt")
    seed_report = read_json(output / "novaseed-report.json")
    checks.append({"name": "native_novaseed_roundtrip", "passed": seed_report["roundtrip_equal"]})
    for name, reason in seed_report["refusals"].items():
        checks.append({"name": "novaseed_" + name, "passed": True, "observed": "refused", "reason": reason})

    with tempfile.TemporaryDirectory(prefix="agialpha-offline-journal-") as temporary:
        journal = Journal.initialize(Path(temporary) / "journal")
        fixture_key = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"PUBLIC-RESEARCH-ACCOUNTING-FIXTURE").digest())
        public = fixture_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        trust = TrustRegistry({"study-accountant-fixture": TrustAnchor(public, frozenset({"accounting"}), provenance="local")})
        ledger = CostLedger(journal, trust)
        def apply(action: str, record: Any, operation_id: str) -> dict[str, Any]:
            payload = {"journal_identity": journal.identity, "operation_id": operation_id, "action": action, "record": record}
            signed = sign_record(fixture_key, "study-accountant-fixture", "flywheel-cost-command", payload)
            return ledger.apply(signed)
        charges = []
        for index, row in enumerate(request["cost_sample"]):
            amount = row["estimated_micro_usd"]
            record = {"activity_id": row["activity_id"], "mission_id": request["study_id"], "bucket": row["bucket"],
                      "category": row["category"], "accrued_micro_usd": amount, "paid_micro_usd": 0,
                      "basis": "unknown" if amount is None else "attested", "evidence_digest": sha(canonical(row)),
                      "note": "Research accounting sample; amounts are assumed, not billed or paid. " + row["note"]}
            charge = Charge.model_validate(record)
            apply("charge", charge.model_dump(), f"sample-charge-{index}")
            charges.append(record)
        if {r["bucket"] for r in charges} != {"A", "B", "C"}:
            raise ValueError("Cost sample must include all A/B/C buckets")
        report = ledger.report(request["study_id"])
        if charges:
            duplicate = dict(charges[0], bucket="B" if charges[0]["bucket"] != "B" else "C")
            refused("same_activity_cannot_be_recharged_in_another_bucket", lambda: apply("charge", duplicate, "duplicate-negative-control"))
        refused("unknown_cost_cannot_be_labeled_zero", lambda: Charge.model_validate({**charges[0], "accrued_micro_usd": None, "basis": "attested"}))
        if report["unknown_costs"] or not report["complete"]:
            checks.append({"name": "incomplete_costs_do_not_produce_profit", "passed": report["complete_cost_profit"] is None})
        if report["collected_revenue"] != 0:
            raise AssertionError("Offline sample cannot acquire customer receipts")
        checks.append({"name": "no_customer_collection_record", "passed": True})
        write_json(output / "cost-ledger.json", {"evidence_class": "executed_native_ledger_over_assumed_sample", "amounts_are_not_actual_invoices": True,
                   "actual_customer_collections_usd": 0, "actual_complete_cost_usd": None, "sample_report": report,
                   "native_signed_snapshot": ledger.snapshot(), "temporary_fixture_identity": journal.identity,
                   "fixture_private_keys_persisted": False, "sample_activity_count": len(charges)})
        manifest = {"skill_id": request["study_id"], "version": 1, "origin_mission": request["study_id"],
                    "origin_record_digest": sha(canonical(request)), "origin_agent": "research-fixture.agent.agi.eth",
                    "origin_wallet": "0x" + "11" * 20, "content_digest": seed_report["payload_sha256"],
                    "supported_scope": "new-research-instrument/v1", "prerequisites": [],
                    "limitations": "Public research only; proposed scientific scope is not a native production capability.",
                    "rights": "cleared-for-authenticated-network", "rights_evidence": sha(canonical(request["rights"])),
                    "dependency_digests": [sha(canonical(lock))], "export_policy": "controlled-invocation-only"}
        refused("new_instrument_scope_not_production_admitted", lambda: CapsuleManifest.model_validate(manifest))
        invalid_rights = {**manifest, "supported_scope": "bounded-public-source-selection/v1", "rights": "unreviewed"}
        refused("unreviewed_rights_not_production_admitted", lambda: CapsuleManifest.model_validate(invalid_rights))
        read_attempts: list[dict[str, str]] = []
        class OfflineReader:
            def __init__(self, label: str) -> None:
                self.label = label
            def call(self, method: str, params: list[Any]) -> Any:
                read_attempts.append({"reader": self.label, "method": method})
                raise RuntimeError("Offline research: live ENS reads are unavailable; authority denied.")
        pins = ENSPins(registry_sha256="0" * 64, wrapper_sha256="0" * 64, registrar_sha256="0" * 64)
        authority = ENSAuthority((OfflineReader("local-denier-1"), OfflineReader("local-denier-2")), pins)
        access = ResourceAccess(journal, ServiceIdentity(origin="https://offline-study.invalid"), authority)
        wallet = Account.from_key("0x" + "11" * 32)
        resource = seed_report["payload_sha256"]
        challenge = access.challenge("research-fixture.agent.agi.eth", wallet.address, resource, "invoke", sha(canonical(request)))
        signature = wallet.sign_message(encode_defunct(text=challenge["message"])).signature.hex()
        proof = AccessRequest(challenge_id=challenge["challenge_id"], signature=signature)
        refused("valid_local_signature_without_live_ENS_authority_denied", lambda: access.prepare(proof, resource, "invoke", sha(canonical(request))))
        challenge_state = journal.latest("@flywheel-challenge:" + challenge["challenge_id"])
        checks.append({"name": "denied_authority_does_not_consume_challenge", "passed": challenge_state["used"] is False})
        journal_check = journal.verify()
        write_json(output / "admission.json", {"production_admission": "DENIED", "protected_scope": "unsupported new research instrument",
                   "rights_clearance": "unreviewed rights rejected in separate control", "live_ENS_authority": "DENIED",
                   "live_RPC_calls": 0, "local_denier_attempts": read_attempts,
                   "fixture_pins": True, "test_signature_is_not_live_ENS_ownership": True,
                   "new_authority_granted": False, "native_journal_verification": journal_check,
                   "checks": [r for r in checks if any(term in r["name"] for term in ("admitted", "authority", "challenge"))]})

    write_json(output / "mark-review-packet.json", {"evidence_class": "inspectable_offline_research_artifacts", "MARK_execution": "NOT_EXECUTED",
               "live_funding": False, "minted": False, "listed": False, "traded": False, "token_movements": 0,
               "plan_root": plan["planRoot"], "novaseed_payload_sha256": seed_report["payload_sha256"],
               "current_production_admission": "DENIED", "validator_votes": 0,
               "existing_contract_sources": [r for r in lock["files"] if r["path"].startswith("contracts/")],
               "review_requirements": ["Independent interpretation of each acceptance criterion", "Rights clearance for actual content", "Current mission-specific authority", "Separate approval for any future funding or chain action"]})
    imports = sorted({str(Path(m.__file__).resolve().relative_to(repo)) for m in list(sys.modules.values())
                      if getattr(m, "__file__", None) and Path(m.__file__).resolve().is_relative_to(repo)})
    pinned = {r["path"] for r in lock["files"]}
    if not set(imports) <= pinned:
        raise AssertionError("Unpinned upstream import: " + str(set(imports) - pinned))
    package_versions = {}
    for package in ["pydantic", "cryptography", "numpy", "httpx", "PyYAML", "eth-hash", "eth-utils", "eth-account", "pycryptodome"]:
        package_versions[package] = importlib.metadata.version(package)
    if not all(row["passed"] for row in checks):
        raise AssertionError("An integration check did not pass")
    write_json(output / "run-report.json", {"schema": "agialpha.study.offline-integration.v1", "upstream_commit": COMMIT,
               "input_sha256": sha(args.input.read_bytes()), "source_lock_sha256": sha((ROOT / "source-lock.json").read_bytes()),
               "passed": len(checks), "failed": 0, "checks": checks, "actual_upstream_imports": imports,
               "environment": {"python": platform.python_version(), "node": seed_report["node"], "packages": package_versions},
               "scientific_result_certified": False, "commercial_result_certified": False, "model_calls": 0, "on_chain_actions": 0,
               "production_admission": "DENIED", "source_qualification": "Scoped offline component execution only; not installed/released repository qualification."})
    artifacts = [{"path": str(p.relative_to(output)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(output.iterdir()) if p.is_file()]
    write_json(output / "artifact-manifest.json", {"excludes": ["artifact-manifest.json"], "files": artifacts})
    print(json.dumps({"passed": len(checks), "failed": 0, "production_admission": "DENIED", "output": str(output)}))

if __name__ == "__main__":
    main()
