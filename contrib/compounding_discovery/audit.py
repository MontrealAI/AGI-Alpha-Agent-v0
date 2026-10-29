# SPDX-License-Identifier: Apache-2.0
"""Independent arithmetic, source identity and final-certificate audits.

This module does not import the candidate engine, solver, memory, or strategy
programs. Expected source identities must come from the reviewer's prior freeze.
A self-reported source manifest is not an authentication boundary.
"""

from __future__ import annotations

from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from alpha_factory_v1.core.runtime.structural_transfer import eadarp_check


class AuditError(ValueError):
    """A saved record does not satisfy independent consistency checks."""


def digest(value: Any) -> str:
    """Hash exact finite JSON without invoking any producer serialization."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def exact(value: Any) -> Fraction:
    """Read finite exact quantities, rejecting coercible booleans and floats."""
    if type(value) is int:
        return Fraction(value)
    if not isinstance(value, str) or len(value) > 200:
        raise AuditError("exact quantity required")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise AuditError("invalid exact quantity") from error
    if abs(result) > 10**18:
        raise AuditError("quantity magnitude")
    return result


def audit_frozen_files(expected: dict[str, str], repo_root: Path | None = None) -> dict[str, Any]:
    """Check reviewer-owned file bindings against actual current bytes."""
    if not expected:
        raise AuditError("empty source freeze")
    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    for name, sha256 in expected.items():
        path = Path(name)
        if not path.is_absolute():
            path = root / path
            if not path.resolve().is_relative_to(root):
                raise AuditError("relative source path escapes repository")
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
            raise AuditError("frozen evaluator/source file was altered or is missing")
    return {"audit_passed": True, "files": len(expected)}


def audit_costs(rows: Any, claimed_total: Any) -> dict[str, Any]:
    """Reprice every resource event once; do not trust claimed line totals."""
    if not isinstance(rows, list) or not rows:
        raise AuditError("nonempty charged resource events required")
    seen: set[str] = set()
    total = Fraction(0)
    for row in rows:
        if not isinstance(row, dict) or not {"id", "stage", "quantity", "rate", "amount", "basis"} <= set(row):
            raise AuditError("cost event schema")
        ident = row["id"]
        if not isinstance(ident, str) or not ident or ident in seen:
            raise AuditError("duplicate or empty resource event identity")
        seen.add(ident)
        if row["basis"] not in {"measured-cpu", "estimated-operation"}:
            raise AuditError("undeclared cost basis")
        quantity, rate, amount = (exact(row[key]) for key in ("quantity", "rate", "amount"))
        if min(quantity, rate, amount) < 0 or quantity * rate != amount:
            raise AuditError("cost quantity-times-rate mismatch")
        total += amount
    if total != exact(claimed_total):
        raise AuditError("aggregate cost mismatch")
    return {"events": len(seen), "cost_total": str(total)}


def audit_transfer_mapping(request: dict[str, Any]) -> None:
    """Check this registered capacity mapping without importing its constructor."""
    captures = request.get("captures", [])
    matches = [
        capture
        for capture in captures
        if capture.get("developmental_only") is False
        and capture.get("principle", {}).get("family") == "linear-capacity"
    ]
    if len(matches) != 1:
        raise AuditError("one checked applicable transfer experience required")
    capture = matches[0]
    if capture.get("capture_hash") != digest({key: value for key, value in capture.items() if key != "capture_hash"}):
        raise AuditError("source experience identity mismatch")
    variables = capture["principle"]["variables"]
    mapping = request.get("mapping", {})
    bindings = mapping.get("variables", {})
    destination_roles = {"total_energy": "capacity", "consumed_energy": "reserved", "terminal_energy": "remaining"}
    if (
        len(variables) != 3
        or set(bindings) != {item["name"] for item in variables}
        or set(bindings.values()) != set(destination_roles)
    ):
        raise AuditError("incomplete typed transfer mapping")
    expected = set()
    for variable in variables:
        if variable["role"] != destination_roles[bindings[variable["name"]]]:
            raise AuditError("transfer mapping changes resource causal role")
        if variable["dimension"] in {"unknown", "any", "?"} or variable["unit"] in {"unknown", "any", "?"}:
            raise AuditError("unknown source dimension or unit")
        expected.add((variable["dimension"], variable["unit"], "energy", "kWh", "structural-instantiation"))
    declared = mapping.get("bindings", [])
    actual = {
        (item["source_dimension"], item["source_unit"], item["target_dimension"], item["target_unit"], item["mode"])
        for item in declared
    }
    if len(actual) != len(declared) or actual != expected:
        raise AuditError("invalid unit binding or unauthorized numerical conversion")


def audit_critiques(target: dict[str, Any], artifact: dict[str, Any], critiques: Any) -> None:
    """Independently check retained criticisms and every claimed found boundary."""
    if not isinstance(critiques, list) or len(critiques) != 3:
        raise AuditError("declared three adversarial search records required")
    mutation, *boundaries = critiques
    if (
        mutation.get("kind") != "certificate-corruption"
        or mutation.get("independently_rejected") is not True
        or eadarp_check.check(target, mutation["artifact"])["accepted"] is not False
    ):
        raise AuditError("unsupported corruption criticism")
    for record in boundaries:
        if record.get("kind") != "operator-perturbation-boundary-search":
            raise AuditError("unknown boundary criticism")
        verdict = eadarp_check.check(record["target"], record["artifact"])
        found = (
            verdict["accepted"] is True
            and artifact["status"] == "FEASIBLE"
            and record["artifact"]["status"] == "INFEASIBLE"
        )
        if record.get("acceptance") != verdict or record.get("certified_boundary_found") is not found:
            raise AuditError("boundary claim differs from independent certificate")


def audit_result(
    request: dict[str, Any], result: dict[str, Any], expected_source_hashes: dict[str, str]
) -> dict[str, Any]:
    """Reconstruct certificate acceptance, budget, resource costs and provenance."""
    if not expected_source_hashes or result.get("source_hashes") != expected_source_hashes:
        raise AuditError("source identities differ from independent freeze")
    if result.get("request_hash") != digest(request):
        raise AuditError("request identity mismatch")
    if result.get("budget_cap") != request.get("budget"):
        raise AuditError("budget cap differs from authorized request")
    resources = result.get("resources")
    if not isinstance(resources, dict):
        raise AuditError("resource record missing")
    for name in ("operations", "solver_calls", "cpu_seconds"):
        used, cap = exact(resources[name]), exact(request["budget"][name])
        if used < 0 or cap < 0 or used > cap:
            raise AuditError(f"resource cap exceeded: {name}")
        if name != "cpu_seconds" and (used.denominator != 1 or cap.denominator != 1):
            raise AuditError("discrete resource must be integral")
    priced = audit_costs(result.get("costs"), result.get("cost_total"))
    if exact(resources["operations"]) != len(result["costs"]):
        raise AuditError("operation event count mismatch")
    metered_cpu = sum(
        (exact(row["quantity"]) for row in result["costs"] if row["basis"] == "measured-cpu"), Fraction(0)
    )
    if exact(resources["cpu_seconds"]) != metered_cpu:
        raise AuditError("CPU resource quantity differs from measured events")
    candidate_calls = sum(exact(row.get("solver_calls", 0)) for row in result.get("candidates", []))
    if exact(resources["solver_calls"]) < candidate_calls:
        raise AuditError("solver invocations underreported")
    artifact = result.get("artifact")
    if not isinstance(artifact, dict):
        raise AuditError("explicit target artifact or unresolved record required")
    verdict = eadarp_check.check(request["target"], artifact)
    claimed = result.get("acceptance")
    if not isinstance(claimed, dict) or type(claimed.get("accepted")) is not bool:
        raise AuditError("literal independent acceptance required")
    if claimed["accepted"] != verdict["accepted"]:
        raise AuditError("claimed acceptance differs from independent raw-task reconstruction")
    if claimed.get("artifact_hash") != verdict["artifact_hash"] or claimed.get("task_id") != verdict["task_id"]:
        raise AuditError("independent acceptance is not bound to exact task/artifact")
    if "accepted" in result and result["accepted"] is not verdict["accepted"]:
        raise AuditError("top-level acceptance differs")
    if verdict["accepted"] and request["capabilities"]["A"]:
        audit_transfer_mapping(request)
    if verdict["accepted"] and request["capabilities"]["C"]:
        audit_critiques(request["target"], artifact, result.get("critiques"))
    if result.get("funding") != {"earned": False, "source": "seed-funded-research"}:
        raise AuditError("unsubstantiated earned-funding attribution")
    if result.get("result_hash") != digest({key: value for key, value in result.items() if key != "result_hash"}):
        raise AuditError("result seal mismatch")
    return {
        "audit_passed": True,
        "target_accepted": verdict["accepted"],
        "task_id": verdict["task_id"],
        "artifact_hash": verdict["artifact_hash"],
        **priced,
        "scope": "saved source identity, exact arithmetic, matched resource cap and independent model certificate",
    }


def audit_matched_budgets(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Check complete factorial allocation within each paired task/seed block."""
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in records:
        request = row["request"]
        key = digest(request["target"]), request["seed"]
        groups.setdefault(key, []).append(request)
    expected = {(a, s, c) for a in (False, True) for s in (False, True) for c in (False, True)}
    for requests in groups.values():
        if len(requests) != 8:
            raise AuditError("factorial block must contain eight arms")
        arms = {tuple(request["capabilities"][key] for key in ("A", "S", "C")) for request in requests}
        if arms != expected or any(type(value) is not bool for arm in arms for value in arm):
            raise AuditError("incomplete or duplicate factorial arms")
        if len({digest(request["budget"]) for request in requests}) != 1:
            raise AuditError("unequal permitted resource budgets")
        if len({digest(request.get("captures", [])) for request in requests}) != 1:
            raise AuditError("unequal permitted historical source records")
    return {"audit_passed": True, "paired_blocks": len(groups), "arms_per_block": 8}


def audit_memory(memory: dict[str, Any], expected_source_hashes: dict[str, str]) -> dict[str, Any]:
    """Rebuild saved chronology and certificates without importing the learner."""
    body = {key: value for key, value in memory.items() if key != "memory_hash"}
    if memory.get("memory_hash") != digest(body):
        raise AuditError("memory seal mismatch")
    history, assets = memory.get("history"), memory.get("assets")
    if not isinstance(history, list) or not isinstance(assets, list) or len(history) != len(assets):
        raise AuditError("one retained strategy per checked experience required")
    if type(memory.get("version")) is not int or memory["version"] != len(history):
        raise AuditError("memory chronology length")
    prefix = {
        "schema": memory["schema"],
        "version": 0,
        "parent_hash": None,
        "history": [],
        "assets": [],
        "principles": [],
    }
    seen: set[str] = set()
    principles: list[dict[str, Any]] = []
    parent = None
    for position, (record, asset) in enumerate(zip(history, assets), 1):
        if record.get("id") != digest(record["task"]) or record["id"] in seen:
            raise AuditError("duplicate or changed historical task")
        seen.add(record["id"])
        if record.get("source_hashes") != expected_source_hashes:
            raise AuditError("historical source identity mismatch")
        if eadarp_check.check(record["task"], record["artifact"])["accepted"] is not True:
            raise AuditError("historical output lacks an independent certificate")
        if record.get("counterexamples"):
            audit_critiques(record["task"], record["artifact"], record["counterexamples"])
        if exact(record["cost_total"]) < 0:
            raise AuditError("negative historical cost")
        if asset.get("support") != record["id"] or asset.get("program") != record["program"]:
            raise AuditError("retained programme lacks corresponding checked support")
        expected_criticism_refs = [
            {"kind": item["kind"], "record_hash": digest(item)} for item in record.get("counterexamples", [])
        ]
        if asset.get("counterexamples") != expected_criticism_refs:
            raise AuditError("retained counterexample references differ from full checked history")
        for capture in record.get("captures", []):
            if capture.get("capture_hash") != digest(
                {key: value for key, value in capture.items() if key != "capture_hash"}
            ):
                raise AuditError("retained principle capture identity mismatch")
            if capture not in principles:
                principles.append(capture)
        parent = digest(prefix)
        prefix = {
            "schema": memory["schema"],
            "version": position,
            "parent_hash": parent,
            "history": history[:position],
            "assets": assets[:position],
            "principles": list(principles),
        }
    if memory.get("principles", []) != principles:
        raise AuditError("principle retention differs from chronological history")
    if memory.get("parent_hash") != parent:
        raise AuditError("memory parent lineage mismatch")
    return {"audit_passed": True, "version": len(history), "independently_checked_history": len(seen)}


def audit_storage_receipts(
    directory: Path,
    freeze: dict[str, Any],
    records: list[dict[str, Any]],
    promotions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify every executed edge has its own qualifying prospective storage record."""
    policy = freeze.get("resource_policy")
    if policy is None:
        return {
            "prospective_policy_present": False,
            "executed_edges_qualified": None,
            "scope": "No frozen prospective storage protocol; external qualification remains open",
        }
    expected = {"preserve_free_disk_bytes": 200_000_000, "guard_version": "pre-observation-and-promotion/v1"}
    if policy != expected:
        raise AuditError("unknown or weakened prospective storage policy")
    receipts: dict[str, dict[str, Any]] = {}
    current: list[dict[str, Any]] = []
    for name in ("resource-observations.jsonl", "historical-resource-observations.jsonl"):
        path = directory / name
        if not path.exists():
            if name == "resource-observations.jsonl":
                raise AuditError("prospective storage receipts are missing")
            continue
        if path.is_symlink():
            raise AuditError("storage receipt file cannot be a symlink")
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if (
                not isinstance(row.get("id"), str)
                or row["id"] in receipts
                or row.get("phase") not in {"observation", "promotion"}
                or not isinstance(row.get("identity"), str)
                or not row["identity"]
                or type(row.get("free_bytes")) is not int
                or row["free_bytes"] < 0
                or type(row.get("floor_bytes")) is not int
                or row["floor_bytes"] != 200_000_000
                or type(row.get("time_ns")) is not int
                or row["time_ns"] < 1
                or type(row.get("qualified")) is not bool
                or row["qualified"] is not (row["free_bytes"] >= 200_000_000)
            ):
                raise AuditError("invalid or forged prospective storage qualification receipt")
            receipts[row["id"]] = row
            if name == "resource-observations.jsonl":
                current.append(row)

    def require(guard_id: Any, phase: str, identity: str) -> None:
        row = receipts.get(guard_id)
        if row is None or row["phase"] != phase or row["identity"] != identity or row["qualified"] is not True:
            raise AuditError("executed work lacks a matching qualified prospective storage check")

    for record in records:
        require(record.get("storage_guard_id"), "observation", record["request"]["id"])
    if promotions is None:
        path = directory / "learning-costs.json"
        promotions = json.loads(path.read_text()) if path.exists() else []
    for event in promotions:
        if not event["id"].startswith("promotion-"):
            raise AuditError("invalid promotion event identity")
        require(event.get("storage_guard_id"), "promotion", event["id"][len("promotion-") :])
    recovery_count = 0
    for path in sorted((directory / "recovery-costs").glob("*.json")):
        event = json.loads(path.read_text())
        require(event.get("storage_guard_id"), "promotion", Path(event["original_promotion_cost_receipt"]).stem)
        audit_costs([event], event["amount"])
        recovery_count += 1
    if not current:
        raise AuditError("empty prospective storage receipt history")
    summary_path = directory / "summary.json"
    if summary_path.exists():
        actual = json.loads(summary_path.read_text()).get("storage_policy", {})
        expected_summary = {
            "qualified": all(row["qualified"] for row in current),
            "floor_bytes": 200_000_000,
            "checks": len(current),
            "minimum_observed_free_bytes": min(row["free_bytes"] for row in current),
        }
        if any(actual.get(key) != value for key, value in expected_summary.items()):
            raise AuditError("storage summary differs from prospective receipt history")
    return {
        "prospective_policy_present": True,
        "executed_edges_qualified": True,
        "observation_edges": len(records),
        "promotion_edges": len(promotions),
        "recovery_edges": recovery_count,
        "current_checks": len(current),
        "historical_checks": len(receipts) - len(current),
        "minimum_observed_free_bytes": min(row["free_bytes"] for row in current),
        "refused_prechecks": sum(not row["qualified"] for row in current),
        "scope": "Recorded prospective checks; concurrent allocation between checks remains outside the guarantee",
    }


def audit_campaign(directory: Path, repo_root: Path | None = None) -> dict[str, Any]:
    """Inspect preserved campaign records without executing a candidate or new task."""
    freeze = json.loads((directory / "freeze.json").read_text())
    sources = audit_frozen_files(freeze["sources"], repo_root)
    snapshots = freeze.get("source_snapshots", {})
    if snapshots:
        if set(snapshots) != set(freeze["sources"]):
            raise AuditError("source snapshot inventory differs from freeze")
        for name, relative in snapshots.items():
            path = directory / relative
            if (
                not path.resolve().is_relative_to(directory.resolve())
                or path.is_symlink()
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != freeze["sources"][name]
            ):
                raise AuditError("preserved frozen source snapshot differs")
    for name, key in (("base", "base_hash"), ("captures", "captures_hash"), ("mapping", "mapping_hash")):
        if digest(json.loads((directory / f"{name}.json").read_text())) != freeze[key]:
            raise AuditError("frozen input identity mismatch")
    records: list[dict[str, Any]] = []
    target_acceptances = 0
    cost = Fraction(0)
    for folder in ("factorial", "learning", "training"):
        for path in sorted((directory / folder).rglob("*.json*")):
            if path.suffix not in {".json", ".gz"}:
                raise AuditError("unsupported observation encoding")
            raw = path.read_bytes()
            record = json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)
            if record.get("schema") != "agialpha/discovery-observation/v1":
                raise AuditError("unexpected file in campaign observation tree")
            request, result = record["request"], record["result"]
            if request["budget"] != freeze["config"]["budget"]:
                raise AuditError("request budget differs from frozen task protocol")
            if digest(request.get("captures", [])) != freeze["captures_hash"]:
                raise AuditError("historical source availability differs from freeze")
            if digest(request.get("mapping", {})) != freeze["mapping_hash"]:
                raise AuditError("mapping differs from freeze")
            audited = audit_result(request, result, freeze["engine_source_hashes"])
            if record.get("accepted") is not audited["target_accepted"]:
                raise AuditError("observation acceptance differs from raw-task reconstruction")
            if record.get("cost_total") != result["cost_total"] or record.get("task_hash") != digest(request["target"]):
                raise AuditError("observation cost or task identity differs")
            records.append(record)
            target_acceptances += int(audited["target_accepted"])
            cost += exact(audited["cost_total"])
    if not records:
        raise AuditError("no executed observations")
    factorial = [
        record for record in records if record.get("phase") == "factorial" and record["arm"] != "frontier_program"
    ]
    matched = audit_matched_budgets(factorial)
    memories = [
        audit_memory(json.loads(path.read_text()), freeze["engine_source_hashes"])
        for path in sorted(directory.glob("memory-*.json"))
    ]
    storage = audit_storage_receipts(directory, freeze, records)
    return {
        "audit_passed": True,
        "storage": storage,
        "observations": len(records),
        "target_accepted": target_acceptances,
        "observed_execution_cost_usd": str(cost),
        "frozen_files": sources["files"],
        "preserved_source_snapshots": len(snapshots),
        "factorial_blocks": matched["paired_blocks"],
        "memory_snapshots": memories,
        "scope": "Independent saved evidence audit; no new experiment, market demand or operational validation",
    }


def main() -> int:
    """Audit one saved request/result pair against a separate source freeze."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, nargs="?")
    parser.add_argument("result", type=Path, nargs="?")
    parser.add_argument("source_freeze", type=Path, nargs="?")
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--repo-root", type=Path)
    args = parser.parse_args()
    if args.campaign:
        print(json.dumps(audit_campaign(args.campaign, args.repo_root), sort_keys=True))
        return 0
    if args.request is None or args.result is None or args.source_freeze is None:
        parser.error("provide request/result/freeze paths or --campaign DIRECTORY")
    expected = json.loads(args.source_freeze.read_text())
    if "source_hashes" in expected:
        expected = expected["source_hashes"]
    print(json.dumps(audit_result(json.loads(args.request.read_text()), json.loads(args.result.read_text()), expected)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
