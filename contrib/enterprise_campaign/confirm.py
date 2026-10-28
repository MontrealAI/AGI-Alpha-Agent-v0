# SPDX-License-Identifier: Apache-2.0
"""Freeze sources, issue fresh seeds, and execute finite independent confirmation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import random
import secrets
import subprocess
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

from .comparators import ACCEPTANCE_PROTOCOL, conventional_transform, parse_csv, sha256
from .verify import validate_delivery

ROOT = Path(__file__).resolve().parent
BASELINE_SHA256 = "7db64554909d1f90d6848a853ae8420c8add5ba2d4becdf93a58a8d0ead90ff8"


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, data: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def freeze(path: Path, baseline: Path) -> dict[str, Any]:
    baseline = baseline.resolve()
    if not baseline.is_relative_to(ROOT) or file_digest(baseline) != BASELINE_SHA256:
        raise ValueError("baseline must be the exact inspected source inside the campaign")
    files = sorted(ROOT.glob("*.py")) + [ROOT / "policy.json", ROOT / "protocol.json"]
    files += sorted(path for path in ROOT.glob("stages/*/*") if path.suffix in {".txt", ".json"})
    files.append(baseline)
    result = {
        "schema": "alpha-catalog-confirmation-freeze/v1",
        "campaign_id": "alpha-catalog-20261028-v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "git_head_at_freeze": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "files": {str(source.relative_to(ROOT)): file_digest(source) for source in files},
        "baseline": str(baseline.relative_to(ROOT)),
        "acceptance": ACCEPTANCE_PROTOCOL,
        "technical_protocol": {
            "cases": 128, "valid": 96, "invalid": 32,
            "valid_groups": "24 single-key,24 composite-key,24 alias/finite-decimal,24 selective-field; six include UTF-8 BOM",
            "invalid_groups": "8 duplicate-key,8 unterminated-quote,8 nonfinite-decimal,8 ambiguous-alias",
            "comparators": ["frozen-gen0", "frozen-gen1", "frozen-gen2", "independent-conventional", "independent-frontier-AI-code", "ordinary-identical-artifact-reuse"],
            "metric": "exact independent semantic target plus exact original rollback; refusal on invalid inputs",
            "rule": "No source or policy retuning after fresh seeds. Preserved cases permit replay, not fresh requalification.",
        },
        "economic_protocol": {"seeds_per_scenario": 128, "paired": ["investment-policy", "no-investment"],
                              "scenarios": list(json.loads((ROOT / "protocol.json").read_text())["scenarios"])},
    }
    save(path, result)
    return result


def verify_freeze(path: Path) -> dict[str, Any]:
    frozen = json.loads(path.read_text(encoding="utf-8"))
    for relative, expected in frozen["files"].items():
        source = ROOT / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts or file_digest(source) != expected:
            raise ValueError("frozen source drift: " + relative)
    return dict(frozen)


def issue_seeds(freeze_path: Path, output: Path) -> dict[str, Any]:
    frozen = verify_freeze(freeze_path)
    used: set[int] = set()

    def fresh(count: int) -> list[int]:
        values: list[int] = []
        while len(values) < count:
            candidate = secrets.randbits(63)
            if candidate not in used:
                used.add(candidate)
                values.append(candidate)
        return values

    result = {
        "schema": "alpha-catalog-fresh-seeds/v1", "campaign_id": frozen["campaign_id"],
        "issued_at": datetime.now(timezone.utc).isoformat(), "freeze_sha256": file_digest(freeze_path),
        "issuer_scope": "same-session independent verifier; OS CSPRNG after source, policy and acceptance freeze",
        "technical": fresh(128),
        "scenarios": {scenario: fresh(128) for scenario in frozen["economic_protocol"]["scenarios"]},
    }
    save(output, result)
    return result


def issue_extension_seed(directory: Path) -> dict[str, Any]:
    from .verify import audit_world

    report = audit_world(directory)
    if not report["passed"]:
        raise ValueError("extension seed requires complete independent financial/artifact audit")
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    decision, reserve = events[-2:]
    details = decision["details"]
    if (decision["type"] != "investment_decision" or details.get("selected") is not True
            or details.get("target_generation") != 3 or details.get("continuation_seed_not_yet_issued") is not True
            or reserve["type"] != "reserve" or reserve["amount_micro_usd"] != details["cost_micro_usd"]
            or reserve["details"].get("investment_id") != "generation-3"):
        raise ValueError("extension seed requires the exact selected and reserved third investment before new work")
    historical = json.loads((directory / "original-three-period-final-summary.json").read_text())
    if events[historical["event_count"] - 1]["hash"] != historical["event_head"]:
        raise ValueError("original three-period history changed")
    if sum(row["type"] == "opening_capital" for row in events) != 1:
        raise ValueError("extension cannot reset opening capital")
    result = {
        "schema": "alpha-catalog-extension-seed/v1", "seed": secrets.randbits(63),
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "decision_event_id": decision["id"], "decision_event_hash": decision["hash"],
        "reserve_event_id": reserve["id"], "journal_head": reserve["hash"],
        "policy_sha256": file_digest(ROOT / "policy.json"), "protocol_sha256": file_digest(ROOT / "protocol.json"),
        "operator_sha256": file_digest(ROOT / "operate.py"),
        "issuer_source_sha256": file_digest(Path(__file__)),
        "original_history_prefix_verified": True, "independent_audit_passed": True,
        "scope": "One unseen fourth-period seed after positive third-investment decision; not final confirmation seeds",
    }
    save(directory / "extension-seed.json", result)
    return result


def _csv(fields: list[str], rows: list[list[str]], ending: str = "\n") -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator=ending)
    writer.writerow(fields)
    writer.writerows(rows)
    return stream.getvalue()


def make_case(seed: int, index: int) -> dict[str, Any]:
    rng = random.Random(seed)
    valid = index < 96
    feature = index % 4 if valid else 2 if index % 4 in {2, 3} else index % 2
    composite = feature == 1 or feature == 2 and index % 2 == 0
    rows = [[f"SKU-{number // 2 if composite else number}", "fr" if number % 2 else "en",
             f"{rng.randint(-10000, 10000) / 100:.2f}", f"Pièce Ω, {number}", f"local-{number}"]
            for number in range(rng.randint(4, 40))]
    targets = [row[:] for row in reversed(rows[1:])]
    targets[0][3] = 'Nouveau "catalogue"\nQuébec'
    targets[-1][2] = "777.50"
    targets.append(["NEW", "fr", "12.50", "Édition α", "new-note"])
    fields = ["sku", "locale", "price", "name", "note"]
    after_fields = fields[:]
    options: dict[str, Any] = {}
    if feature == 2:
        options = {"decimal_columns": ["price"], "aliases": {"code": "sku", "prix": "price", "titre": "name"}}
        after_fields = ["titre", "prix", "locale", "code", "note"]
        for row in targets:
            row[2] = str(Decimal(row[2]).normalize())
    if feature == 3:
        options = {"update_fields": ["price", "name"]}
        for row in targets:
            row[4] = "external-note"
    kind = "valid"
    if not valid:
        kind = ["duplicate-key", "unterminated-quote", "nonfinite-decimal", "ambiguous-alias"][index % 4]
        if kind == "duplicate-key":
            targets.append(targets[0][:])
        elif kind == "nonfinite-decimal":
            targets[0][2] = "NaN"
        elif kind == "ambiguous-alias":
            options["aliases"]["prix"] = "sku"
    before = _csv(fields, rows, "\r\n" if index % 2 else "\n")
    aliases = options.get("aliases", {})
    if kind == "ambiguous-alias":
        # The invalid declaration must not change the supplier's actual source columns.
        aliases = {"code": "sku", "prix": "price", "titre": "name"}
    after = _csv(after_fields, [[row[fields.index(aliases.get(field, field))] for field in after_fields] for row in targets])
    if kind == "unterminated-quote":
        after += '"unterminated'
    if valid and index % 17 == 0:
        before = "\ufeff" + before
    return {"index": index, "seed": seed, "expected_valid": valid, "kind": kind, "feature": feature,
            "before_csv": before, "after_csv": after, "keys": ["sku", "locale"] if composite else ["sku"],
            "options": options, "generation": 3}


def _load(name: str, path: Path) -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise ValueError("unable to prepare frozen source loader")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def technical(freeze_path: Path, seed_path: Path, output: Path) -> dict[str, Any]:
    frozen = verify_freeze(freeze_path)
    seeds = json.loads(seed_path.read_text(encoding="utf-8"))
    if seeds["freeze_sha256"] != file_digest(freeze_path) or len(seeds["technical"]) != 128:
        raise ValueError("fresh seeds do not bind this freeze")
    output.mkdir(parents=True, exist_ok=False)
    from . import catalog_product as product

    baseline = _load("frozen_direct_frontier_baseline", ROOT / frozen["baseline"])
    gen0 = _load("frozen_generation_zero", ROOT / "stages/gen0/catalog_product.py.txt")
    gen1 = _load("frozen_generation_one", ROOT / "stages/gen1/catalog_product.py.txt")
    gen2 = _load("frozen_generation_two", ROOT / "stages/gen2/catalog_product.py.txt")
    results = []
    for index, seed in enumerate(seeds["technical"]):
        case = make_case(seed, index)
        before, after, keys, options = case["before_csv"], case["after_csv"], case["keys"], case["options"]
        measurements: dict[str, Any] = {}
        package = None
        for name in ["product", "conventional", "direct_frontier", "gen0", "gen1", "gen2"]:
            started = time.process_time_ns()
            try:
                if name == "product":
                    package = product.reconcile(before, after, keys, 3, **options)
                    accepted = validate_delivery(before, after, keys, 3, package, options)
                    value = {"accepted": accepted["accepted"], "output_sha256": package["output_sha256"],
                             "rollback_sha256": sha256(package["rollback_csv"]), "acceptance": accepted}
                elif name == "conventional":
                    text = conventional_transform(before, after, keys, 3, options)
                    value = {"accepted": True, "output_sha256": sha256(text), "rollback_sha256": sha256(before)}
                elif name == "direct_frontier":
                    transformed = baseline.transform(before, after, keys, **options)
                    value = {"accepted": True, "output_sha256": sha256(transformed["output_csv"]),
                             "rollback_sha256": sha256(transformed["rollback_csv"])}
                else:
                    module, generation = {"gen0": (gen0, 0), "gen1": (gen1, 1), "gen2": (gen2, 2)}[name]
                    transformed = module.reconcile(before, after, keys, generation, **options)
                    value = {"accepted": True, "output_sha256": transformed["output_sha256"],
                             "rollback_sha256": sha256(transformed["rollback_csv"])}
            except (ValueError, TypeError, KeyError, csv.Error) as exc:
                value = {"accepted": False, "error": f"{type(exc).__name__}: {exc}"}
            value["cpu_time_ns"] = time.process_time_ns() - started
            measurements[name] = value
        expected_valid = case["expected_valid"]
        correct = measurements["product"]["accepted"] == expected_valid
        conventional_correct = measurements["conventional"]["accepted"] == expected_valid
        ties = {}
        if expected_valid and measurements["product"]["accepted"]:
            for name in ["conventional", "direct_frontier", "gen0", "gen1", "gen2"]:
                alternative = measurements[name]
                ties[name] = bool(alternative["accepted"] and
                                  alternative["output_sha256"] == measurements["product"]["output_sha256"] and
                                  alternative["rollback_sha256"] == sha256(before))
            if package is not None:
                ordinary = product.apply_patch(before, json.loads(json.dumps(package)), authorized=True)
                ties["ordinary_identical_artifact"] = ordinary == package["output_csv"]
        receipt = {"case": case, "package": package, "measurements": measurements, "ties": ties,
                   "product_correct": correct, "conventional_correct": conventional_correct}
        save(output / f"case-{index:03d}.json", receipt)
        results.append(receipt)
    verify_freeze(freeze_path)
    summary = {
        "schema": "alpha-catalog-fresh-technical-confirmation/v1", "freeze_sha256": file_digest(freeze_path),
        "seed_sha256": file_digest(seed_path), "cases": len(results),
        "product_correct": sum(row["product_correct"] for row in results),
        "conventional_correct": sum(row["conventional_correct"] for row in results),
        "valid_product_accepted": sum(row["case"]["expected_valid"] and row["measurements"]["product"]["accepted"] for row in results),
        "invalid_product_refused": sum(not row["case"]["expected_valid"] and not row["measurements"]["product"]["accepted"] for row in results),
        "valid_ties": {name: sum(row["ties"].get(name, False) for row in results)
                       for name in ["conventional", "direct_frontier", "gen0", "gen1", "gen2", "ordinary_identical_artifact"]},
        "passed": all(row["product_correct"] and row["conventional_correct"] for row in results),
        "limits": "Finite synthetic local tests; direct frontier is independently AI-constructed code, not repeated API inference; generation controls compare inherited range, not unique superiority. Actual AI consumption costs unknown.",
    }
    save(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("freeze")
    command.add_argument("--baseline", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("seeds")
    command.add_argument("--freeze", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("extension-seed")
    command.add_argument("--reference", type=Path, required=True)
    command = commands.add_parser("technical")
    command.add_argument("--freeze", type=Path, required=True)
    command.add_argument("--seeds", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze(args.output, args.baseline)
    elif args.command == "seeds":
        result = issue_seeds(args.freeze, args.output)
    elif args.command == "extension-seed":
        result = issue_extension_seed(args.reference)
    else:
        result = technical(args.freeze, args.seeds, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
