# SPDX-License-Identifier: Apache-2.0
import argparse, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream"
sys.dont_write_bytecode = True
sys.path.insert(0, str(UPSTREAM))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def safe_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Study input path escapes the study root")
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Replay the unchanged upstream evidence components against current study artifacts."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence",
        help="Directory for all five generated native evidence files; defaults to explicit refresh of evidence/.",
    )
    args = parser.parse_args()
    manifest = json.loads((UPSTREAM / "manifest.json").read_text())
    verified = []
    for record in manifest["files"]:
        path = UPSTREAM / record["path"]
        data = path.read_bytes()
        git_sha = hashlib.sha1(
            b"blob " + str(len(data)).encode() + b"\0" + data
        ).hexdigest()
        assert sha(path) == record["sha256"] and git_sha == record["sha"]
        verified.append(
            {
                "path": record["path"],
                "sha256": record["sha256"],
                "git_blob": git_sha,
                "byte_exact": True,
            }
        )
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import (
        Charge,
        CATEGORIES,
    )
    import pydantic

    protocol = json.loads((ROOT / "protocol.json").read_text())
    cases = []
    execution = []
    for path in sorted((ROOT / "evidence").glob("*.json")):
        row = json.loads(path.read_text())
        if isinstance(row, dict) and row.get("schema") in [
            "capsule-execution/v1",
            "independent-notebook-acceptance/v1",
        ]:
            execution.append((path, row))
    for identity_path in sorted((ROOT / "deliveries").glob("*/identity.json")):
        identity = json.loads(identity_path.read_text())
        folder = identity_path.parent
        name = folder.name
        source = safe_path(identity["input"])
        recovered = folder / "recovered.ipynb"
        assert (
            sha(source) == identity["input_sha256"]
            and sha(recovered) == identity["output_sha256"]
        )
        records = []
        before = []
        for path, row in execution:
            if row.get("case") != name:
                continue
            recorded_hash = row.get("sha256", row.get("input_sha256"))
            reference = {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha(path),
                "schema": row["schema"],
                "reported_accepted": row.get("accepted") is True,
                "all_cells_completed": row.get("all_cells_completed") is True,
                "check_count": len(row.get("checks", [])),
                "checks_pass": len(row.get("checks", [])) >= 3
                and all(c.get("pass") is True for c in row.get("checks", [])),
                "outbound_attempt_count": len(
                    row.get("outbound_attempts", row.get("network_attempts", []))
                ),
                "checker_sha256": row.get("checker_sha256"),
                "checks_digest": digest(row.get("checks", [])),
            }
            if recorded_hash == identity["output_sha256"]:
                records.append(reference)
            elif recorded_hash == identity["input_sha256"]:
                before.append(reference)
        successful = [
            r
            for r in records
            if r["reported_accepted"]
            and r["all_cells_completed"]
            and r["checks_pass"]
            and r["outbound_attempt_count"] == 0
        ]
        independent = [
            r for r in successful if r["schema"] == "independent-notebook-acceptance/v1"
        ]
        files = [
            {"path": str(p.relative_to(ROOT)), "sha256": sha(p)}
            for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        ]
        cases.append(
            {
                "case": name,
                "phase": identity["phase"],
                "input_path": str(source.relative_to(ROOT)),
                "input_sha256": sha(source),
                "recovered_notebook_sha256": sha(recovered),
                "identity_sha256": sha(identity_path),
                "delivery_files": files,
                "before_records": before,
                "after_records": records,
                "passing_execution_reports": len(successful),
                "independent_passing_reports": len(independent),
                "paired_independent_check_records_equal": len(independent) >= 2
                and len({r["checks_digest"] for r in independent}) == 1,
                "technical_report_boundary": "Reported local computational checks only; no customer acceptance or native mission admission.",
            }
        )
    if not 1 <= len(cases) <= 6:
        raise ValueError("This bounded study binds one to six delivery cases")
    payload = {
        "schema": "recovery-study-native-bindings/v1",
        "protocol_sha256": sha(ROOT / "protocol.json"),
        "source_commit": manifest["source_commit"],
        "offer": protocol["offer"]["name"],
        "cases": cases,
        "economics_input_sha256": sha(ROOT / "economics/inputs.json"),
        "economic_summary_sha256": sha(ROOT / "economics/results/summary.json"),
        "actual_collections_usd": 0,
        "actual_complete_cost_usd": None,
        "model_billing_status": "unknown",
        "authority": "none; local public research fixture",
        "live_identity": "NOT_EXECUTED",
        "MARK": "NOT_EXECUTED",
    }
    bound_digest = digest(payload)
    charges = []
    for case in cases:
        for category in sorted(CATEGORIES):
            charges.append(
                Charge(
                    activity_id=case["case"] + "/" + category,
                    mission_id="recovery/" + case["case"],
                    bucket="A",
                    category=category,
                    accrued_micro_usd=None,
                    paid_micro_usd=0,
                    basis="unknown",
                    evidence_digest=bound_digest,
                    note="No complete allocated provider/resource bill is available. Zero new external payment recorded; total accrued cost remains unknown.",
                ).model_dump()
            )
    rejected_unknown_zero = False
    try:
        invalid = dict(charges[0])
        invalid["accrued_micro_usd"] = 0
        Charge.model_validate(invalid)
    except ValueError:
        rejected_unknown_zero = True
    assert rejected_unknown_zero
    native_input = {
        "bindings": payload,
        "binding_sha256": bound_digest,
        "charge_records": charges,
        "upstream": {"source_commit": manifest["source_commit"], "files": verified},
    }
    evidence = args.output.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    input_path = evidence / "native_inputs.json"
    input_path.write_text(json.dumps(native_input, indent=2) + "\n")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run(
        ["node", str(ROOT / "scripts/native_evidence_demo.mjs"), str(input_path)],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    native = json.loads(run.stdout)
    result = {
        "schema": "recovery-native-execution/v1",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        "pydantic": pydantic.__version__,
        "source_commit": manifest["source_commit"],
        "upstream_files_byte_verified": len(verified),
        "binding_sha256": bound_digest,
        "bound_delivery_cases": len(cases),
        "bound_passing_reports": sum(c["passing_execution_reports"] for c in cases),
        "bound_independent_reports": sum(
            c["independent_passing_reports"] for c in cases
        ),
        "native_charge": {
            "status": "EXECUTED_LOCAL_SCHEMA_VALIDATION",
            "records": len(charges),
            "all_accruals_unknown": all(
                r["accrued_micro_usd"] is None for r in charges
            ),
            "unknown_to_zero_rejected": rejected_unknown_zero,
            "complete_cost_profit": None,
            "complete_cost_seal": "NOT_REQUESTED_UNKNOWN_COSTS",
            "signed_cost_ledger": "NOT_EXECUTED_NO_CONFIGURED_ACCOUNTING_AUTHORITY",
        },
        **native,
        "MARK": {"status": "NOT_EXECUTED"},
        "live_ENS": {"status": "NOT_EXECUTED"},
        "live_services": {"status": "NOT_EXECUTED"},
        "payments": {
            "actual_collections_usd": 0,
            "new_external_spending_usd": 0,
            "token_transactions": 0,
            "USDC_transactions": 0,
        },
        "boundary": "Local exact-source hashing, encryption round-trip, plan proof checks and Charge validation execute. They do not prove scientific truth, paid acceptance, completeness of actual costs, live identity, settlement or production qualification.",
    }
    (evidence / "native_execution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
