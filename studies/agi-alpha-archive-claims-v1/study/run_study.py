# SPDX-License-Identifier: Apache-2.0
"""Reproduce the frozen, research-authored archive-claim experiment."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import platform
import random
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import Counter
from fractions import Fraction
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parent


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def case_from(rng: random.Random, index: int, successor: bool = False) -> dict[str, Any]:
    n = (4, 6)[index % 2] if successor else (4, 6, 8)[index % 3]
    group_count = (2, 3)[index % 2] if successor else (1, 2, 2)[index % 3]
    drift = rng.randint(-15, 15)
    baseline = rng.randint(150, 250)
    weights: list[Any]
    if successor:
        weights = [-1, 2, -2, 1] if n == 4 else [-2, -1, 3, -2, 4, -2]
        weights = [str(Fraction(w, n)) for w in weights]
    else:
        weights = [str(Fraction(-2 if i < n // 2 else 2, n)) for i in range(n)]
    groups = []
    for g in range(group_count):
        amplitude = Fraction(rng.randint(2, 10), 10)
        groups.append({"id": f"g{g}", "alternatives": [str(-amplitude), "0", str(amplitude)]})
    rows = []
    for i in range(n):
        base = Fraction(baseline + (drift if i >= n // 2 else 0) + rng.randint(-2, 2), 10)
        spread = Fraction(rng.randint(1, 9), 10)
        gid = i % group_count if successor else min(group_count - 1, i // (n // 2))
        rows.append(
            {
                "id": f"r{i}",
                "source_id": f"authored-{index:03d}-page-{gid}",
                "alternatives": [str(base), str(base + spread)],
                "weight": weights[i],
                "group_id": f"g{gid}",
                "error_bound": str(Fraction(rng.randint(0, 2), 10)),
            }
        )
    return {
        "schema": "agialpha.archive-claim.v1",
        "id": f"{'successor' if successor else 'confirmation'}-{index:03d}",
        "unit": "authored measurement units",
        "source_model": "research-authored",
        "rows": rows,
        "calibrations": groups,
        "error_budget": 2 if successor else index % 2,
        "threshold": str(Fraction(rng.randint(-8, 8), 10)),
    }


def witness_valid(case: dict[str, Any], witness: dict[str, Any], expected: str) -> bool:
    glyphs, offsets, errors = witness["glyph_choices"], witness["calibration_choices"], witness["errors"]
    assert set(glyphs) == {r["id"] for r in case["rows"]}
    assert set(offsets) == {g["id"] for g in case["calibrations"]}
    assert set(errors).issubset(glyphs)
    assert sum(Fraction(v) != 0 for v in errors.values()) <= case["error_budget"]
    for g in case["calibrations"]:
        assert Fraction(offsets[g["id"]]) in {Fraction(x) for x in g["alternatives"]}
    total = Fraction()
    for row in case["rows"]:
        rid = row["id"]
        glyph, error = Fraction(glyphs[rid]), Fraction(errors.get(rid, "0"))
        assert glyph in {Fraction(x) for x in row["alternatives"]}
        bound = Fraction(row["error_bound"])
        assert error in {-bound, Fraction(), bound}
        value = glyph + Fraction(offsets[row["group_id"]]) + error
        assert value == Fraction(witness["row_values"][rid])
        total += Fraction(row["weight"]) * value
    assert total == Fraction(expected) == Fraction(witness["query_value"])
    return True


def originating(shared: bool = True) -> dict[str, Any]:
    case: dict[str, Any] = {
        "schema": "agialpha.archive-claim.v1",
        "id": "origin-shared" if shared else "origin-independent",
        "unit": "authored measurement units",
        "source_model": "research-authored",
        "rows": [],
        "calibrations": [{"id": "g0", "alternatives": ["-2/5", "0", "2/5"]}],
        "error_budget": 1,
        "threshold": "7/20",
    }
    if not shared:
        case["calibrations"].append({"id": "g1", "alternatives": ["-2/5", "0", "2/5"]})
    for i, base in enumerate([200, 201, 202, 203, 210, 211, 212, 213]):
        case["rows"].append(
            {
                "id": f"r{i}",
                "source_id": "authored-origin",
                "alternatives": [str(Fraction(base, 10)), str(Fraction(base + 6, 10))],
                "weight": "-1/4" if i < 4 else "1/4",
                "group_id": "g0" if shared or i < 4 else "g1",
                "error_bound": "1/10",
            }
        )
    return case


def invalid_cases(base: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    edits: list[tuple[str, Callable[[dict[str, Any]], Any]]] = [
        ("missing_unit", lambda c: c.pop("unit")),
        ("unsupported_coupling", lambda c: c.update(constraints=["sum(x)=1"])),
        ("real_source_claim", lambda c: c.update(source_model="verified-physical-archive")),
        ("negative_budget", lambda c: c.update(error_budget=-1)),
        ("boolean_budget", lambda c: c.update(error_budget=True)),
        ("empty_rows", lambda c: c.update(rows=[])),
        ("duplicate_row", lambda c: c["rows"].append(copy.deepcopy(c["rows"][0]))),
        ("missing_source", lambda c: c["rows"][0].pop("source_id")),
        ("float_weight", lambda c: c["rows"][0].update(weight=0.25)),
        ("negative_error", lambda c: c["rows"][0].update(error_bound="-1")),
        ("unknown_group", lambda c: c["rows"][0].update(group_id="absent")),
        ("zero_denominator", lambda c: c["rows"][0].update(weight="1/0")),
    ]
    for name, edit in edits:
        case = copy.deepcopy(base)
        edit(case)
        yield name, case


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit("Choose a new output directory; original evidence is never overwritten.")
    freeze = json.loads((ROOT / "provenance/constructor_freeze.json").read_text())
    engine_path, oracle_path = ROOT / freeze["path"], ROOT / freeze["oracle_path"]
    assert sha(engine_path) == freeze["sha256"], "constructor differs from freeze"
    assert sha(oracle_path) == freeze["oracle_sha256"], "oracle differs from freeze"
    engine = module("archive_claim_engine", engine_path)
    oracle = module("archive_exhaustive_reference", oracle_path)
    protocol = json.loads((ROOT / "config/construction_protocol.json").read_text())["frozen_design"]
    out.mkdir(parents=True)
    records: list[dict[str, Any]]
    timings: list[dict[str, Any]]
    records, timings = [], []
    cases = [("origin", originating(True)), ("negative_control", originating(False))]
    for family, count_key, seed_key, successor in [
        ("confirmation", "number_confirmation_cases", "seed", False),
        ("successor", "number_successor_cases", "successor_seed", True),
    ]:
        rng = random.Random(protocol[seed_key])
        for i in range(protocol[count_key]):
            cases.append((family, case_from(rng, i, successor)))
    for family, case in cases:
        input_path = out / "inputs" / (case["id"] + ".json")
        write(input_path, case)
        start = time.perf_counter()
        result = engine.solve(case, sha(input_path))
        engine_time = time.perf_counter() - start
        start = time.perf_counter()
        reference = oracle.solve(case)
        oracle_time = time.perf_counter() - start
        fields = ["lower", "upper", "decision", "world_count"]
        equal = all(result[k] == reference[k] for k in fields)
        witnesses = all(witness_valid(case, result[label + "_witness"], result[label]) for label in ("lower", "upper"))
        relaxed = copy.deepcopy(case)
        original_groups = {g["id"]: g["alternatives"] for g in case["calibrations"]}
        relaxed["calibrations"] = []
        for row in relaxed["rows"]:
            relaxed["calibrations"].append({"id": row["id"], "alternatives": original_groups[row["group_id"]]})
            row["group_id"] = row["id"]
        interval = engine.solve(relaxed)
        assert (
            Fraction(interval["lower"])
            <= Fraction(result["lower"])
            <= Fraction(result["upper"])
            <= Fraction(interval["upper"])
        )
        point = sum(
            (
                Fraction(r["weight"]) * (Fraction(r["alternatives"][0]) + Fraction(original_groups[r["group_id"]][0]))
                for r in case["rows"]
            ),
            Fraction(),
        )
        point_decision = "TRUE" if point > Fraction(case["threshold"]) else "FALSE"
        record = {
            "family": family,
            "id": case["id"],
            "input_sha256": sha(input_path),
            **{k: result[k] for k in fields},
            "reference_equal": equal,
            "witnesses_valid": witnesses,
            "decorrelated_decision": interval["decision"],
            "decorrelated_lower": interval["lower"],
            "decorrelated_upper": interval["upper"],
            "point_decision": point_decision,
            "point_claim_not_universal": result["decision"] == "UNRESOLVED" or point_decision != result["decision"],
        }
        records.append(record)
        timings.append({"id": case["id"], "engine_seconds": engine_time, "oracle_seconds": oracle_time})
        write(out / "certificates" / (case["id"] + ".json"), result)
        write(out / "reference" / (case["id"] + ".json"), reference)
        print(case["id"], result["decision"], "PASS" if equal and witnesses else "FAIL", flush=True)
    refusals = []
    for name, case in invalid_cases(originating()):
        write(out / "invalid" / (name + ".json"), case)
        try:
            engine.solve(case)
            refused, error = False, "not refused"
        except ValueError as exc:
            refused, error = True, str(exc)
        refusals.append({"name": name, "refused": refused, "error": error})
    archive = out / "archive-claim-capability-v1.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo("claim_engine.py", (2026, 10, 27, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, engine_path.read_bytes())
        info = zipfile.ZipInfo("CAPABILITY.json", (2026, 10, 27, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(
            info,
            json.dumps(
                {
                    "version": "1.0.0",
                    "source_sha256": sha(engine_path),
                    "rights": "Apache-2.0",
                    "scope": "research-authored finite affine queries only",
                    "production_admitted": False,
                    "private_data": False,
                    "authority": "recipient must obtain fresh authorization",
                },
                sort_keys=True,
            ).encode(),
        )
    transfer = []
    with tempfile.TemporaryDirectory(prefix="archive-claim-recipient-") as td:
        temp = Path(td)
        recipient, ordinary = temp / "recipient", temp / "ordinary-library"
        recipient.mkdir()
        ordinary.mkdir()
        with zipfile.ZipFile(archive) as z:
            z.extractall(recipient)
        (ordinary / "claim_engine.py").write_bytes(engine_path.read_bytes())
        assert sha(recipient / "claim_engine.py") == sha(ordinary / "claim_engine.py") == sha(engine_path)
        for row in [r for r in records if r["family"] == "successor"]:
            paths = []
            for label, directory in (("retained", recipient), ("ordinary", ordinary)):
                output_path = directory / (row["id"] + ".json")
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(directory / "claim_engine.py"),
                        "--input",
                        str(out / "inputs" / (row["id"] + ".json")),
                        "--output",
                        str(output_path),
                    ],
                    cwd=temp,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert completed.returncode == 0, completed.stderr
                paths.append(output_path)
                write(out / "transfer" / label / (row["id"] + ".json"), json.loads(output_path.read_text()))
            transfer.append(
                {
                    "id": row["id"],
                    "fresh_processes": 2,
                    "byte_identical": paths[0].read_bytes() == paths[1].read_bytes(),
                    "matches_primary_certificate": json.loads(paths[0].read_text())
                    == json.loads((out / "certificates" / (row["id"] + ".json")).read_text()),
                }
            )
    groups = {}
    for family in ("origin", "negative_control", "confirmation", "successor"):
        rows = [r for r in records if r["family"] == family]
        groups[family] = {
            "cases": len(rows),
            "all_reference_equal": all(r["reference_equal"] for r in rows),
            "all_witnesses_valid": all(r["witnesses_valid"] for r in rows),
            "decisions": dict(Counter(r["decision"] for r in rows)),
            "worlds_enumerated": sum(r["world_count"] for r in rows),
            "decorrelation_lost_decisions": sum(
                r["decision"] != "UNRESOLVED" and r["decorrelated_decision"] == "UNRESOLVED" for r in rows
            ),
            "point_nonuniversal_claims": sum(r["point_claim_not_universal"] for r in rows),
        }
    summary = {
        "schema": "agialpha.archive-claim.study.v1",
        "evidence": "executed exact authored-world construction",
        "source_freeze": freeze,
        "groups": groups,
        "refusals": refusals,
        "transfer": transfer,
        "capability_archive_sha256": sha(archive),
        "flagship_admitted": False,
        "novelty": "No substantive advance over identified strongest prior art established.",
        "actual_customer_collections_usd": 0,
        "complete_actual_cost_usd": None,
        "operational_alpha": "Unmeasured; exact conventional method ties",
        "retained_alpha": "Technical execution observed; no measured incremental economic gain",
    }
    write(out / "case_results.json", records)
    write(out / "summary.json", summary)
    write(
        out / "timings.json",
        {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "observations": timings,
            "scope": "local CPU/wall timing only; excludes agent authoring, source validation and business costs",
        },
    )
    if (
        not all(r["reference_equal"] and r["witnesses_valid"] for r in records)
        or not all(r["refused"] for r in refusals)
        or not all(r["byte_identical"] and r["matches_primary_certificate"] for r in transfer)
    ):
        raise SystemExit("A prespecified check failed; preserve outputs and investigate without replacing this run.")
    print(json.dumps(groups, indent=2), flush=True)


if __name__ == "__main__":
    main()
