# SPDX-License-Identifier: Apache-2.0
"""Prospective synthetic confirmation of the exact frozen transferred capsule."""

from __future__ import annotations

import copy
import datetime
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import statistics
import time
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parent
STUDY = ROOT.parent.parent


def digest(path: Path) -> str:
    """Hash an actual file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, name: str) -> Any:
    """Load a source module without changing it."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def spec_for(case: dict[str, Any]) -> dict[str, Any]:
    """Materialize a frozen generated case in the engine's declared schema."""
    permutation = case["permutation"]
    scale, shift = case["scale"], case["shift"]
    remap = {old: permutation.index(old) for old in range(4)}
    return {
        "scenario": case["id"],
        "rounding_half_width": 0.005 * scale,
        "cell_means": [case["means"][i] * scale + shift for i in permutation],
        "count_candidates": [[counts[i] for i in permutation] for counts in case["candidates"]],
        "aggregates": [
            {"id": f"aggregate-{k}", "cells": [remap[i] for i in members], "mean": mean * scale + shift}
            for k, (members, mean) in enumerate(case["aggregates"])
        ],
        "contrast_positive_cells": [remap[0], remap[1]],
        "contrast_negative_cells": [remap[2], remap[3]],
        "assumptions": ["Synthetic declared cells are disjoint and share one endpoint and numeric scale."],
        "excluded_claims": ["Source truth, causal effect, customer acceptance and authority are not established."],
    }


def main() -> None:
    """Freeze generation, then execute the capsule and independent oracle."""
    plan = json.loads((ROOT / "plan.json").read_text())
    if digest(ROOT / "plan.json") != (ROOT / "plan.sha256").read_text().split()[0]:
        raise ValueError("plan identity mismatch")
    rng = random.Random(plan["seed"])
    cases = []
    for index in range(12):
        means = [rng.randint(-10000, 10000) / 100 for _ in range(4)]
        true = [Fraction(str(m)) + Fraction(rng.randint(-4, 4), 1000) for m in means]
        counts = [rng.randint(3, 40) for _ in range(4)]
        candidates = [counts, [n + 1 for n in counts], [max(2, n - 1) for n in counts]]
        aggregates = []
        for members in ([0, 1], [2, 3], [0, 2], [1, 3], [0, 1, 2, 3]):
            average = sum(counts[i] * true[i] for i in members) / sum(counts[i] for i in members)
            aggregates.append([members, float(round(average, 2))])
        permutation = list(range(4))
        if 4 <= index <= 7:
            rng.shuffle(permutation)
        cases.append(
            {
                "id": f"{index + 1:02}",
                "kind": "bounds",
                "means": means,
                "true_means": [str(v) for v in true],
                "candidates": candidates,
                "aggregates": aggregates,
                "permutation": permutation,
                "scale": 1000.0 if index == 10 else 0.001 if index == 11 else 1.0,
                "shift": 273.15 if index == 8 else -10000.0 if index == 9 else 0.0,
            }
        )
    for index in range(4):
        case = copy.deepcopy(cases[index])
        case.update(id=f"{13 + index:02}", kind="conflict")
        case["aggregates"].append([[0, 1], max(case["means"][:2]) + 0.1])
        cases.append(case)
    samples = [[rng.gauss(10, 2) for _ in range(11)], [rng.gauss(16, 4) for _ in range(17)]]
    names = [
        "pool ordinary",
        "pool translated",
        "pool SE conversion",
        "pool permuted",
        "NaN",
        "infinity",
        "Boolean",
        "unknown top-level field",
        "paired missing covariance",
        "unknown dispersion",
        "overlap contrast",
        "unknown aggregate field",
        "JATS spans and digest",
        "digest mismatch",
        "XML entity declaration",
        "unequal semantic units",
    ]
    cases.extend(
        {"id": f"{17 + i:02}", "kind": name, "samples": samples if i < 4 else None} for i, name in enumerate(names)
    )
    generated = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "plan_sha256": digest(ROOT / "plan.json"),
        "seed": plan["seed"],
        "cases": cases,
    }
    (ROOT / "generated-cases.json").write_text(json.dumps(generated, indent=2) + "\n")
    (ROOT / "generation-freeze.json").write_text(
        json.dumps(
            {
                "generated_cases_sha256": digest(ROOT / "generated-cases.json"),
                "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "engine_executed": False,
            },
            indent=2,
        )
        + "\n"
    )
    capsule = STUDY / "instrument/capability-v1.zip"
    if digest(capsule) != plan["capsule_sha256"]:
        raise ValueError("capsule identity mismatch")
    runtime = ROOT / "received"
    runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(capsule) as z:
        for name in z.namelist():
            if Path(name).name != name:
                raise ValueError("unexpected capsule path")
        z.extractall(runtime)
    if digest(runtime / "evidence_engine.py") != plan["engine_sha256"]:
        raise ValueError("engine identity mismatch")
    engine = load_module(runtime / "evidence_engine.py", "confirmed_engine")
    oracle = load_module(ROOT.parent / "development-review/check_development.py", "independent_exact_oracle")
    fixture = ROOT / "table-fixture.xml"
    fixture.write_text(
        '<article><body><p>Endpoint meaning requires review.</p><table-wrap id="t1"><caption><p>Test</p></caption><table><tr><td rowspan="2">A</td><td colspan="2">B</td></tr><tr><td>1</td><td>2</td></tr></table></table-wrap></body></article>'
    )
    entity = ROOT / "entity-fixture.xml"
    entity.write_text('<!DOCTYPE article [<!ENTITY x "bad">]><article><body>&x;</body></article>')
    results = []
    start = time.perf_counter()
    for case in cases:
        record: dict[str, Any] = {"id": case["id"], "kind": case["kind"]}
        try:
            kind = case["kind"]
            if kind in {"bounds", "conflict"}:
                expected = []
                for counts in case["candidates"]:
                    vertices = oracle.exact_vertices(
                        [str(m) for m in case["means"]], counts, [(ids, str(m)) for ids, m in case["aggregates"]]
                    )
                    if vertices:
                        values = [
                            ((v[0] + v[1]) / sum(counts[:2]) - (v[2] + v[3]) / sum(counts[2:]))
                            * Fraction(str(case["scale"]))
                            for v in vertices
                        ]
                        expected.append(
                            {
                                "counts": [counts[i] for i in case["permutation"]],
                                "lower_exact": str(min(values)),
                                "upper_exact": str(max(values)),
                                "lower": float(min(values)),
                                "upper": float(max(values)),
                            }
                        )
                actual = engine.rounded_mean_model(spec_for(case))
                record.update(actual=actual, oracle=expected)
                tolerance = 1e-6 * case["scale"]
                record["passed"] = (
                    len(actual["feasible"]) == len(expected)
                    and all(
                        a["counts"] == e["counts"]
                        and abs(a["lower"] - e["lower"]) <= tolerance
                        and abs(a["upper"] - e["upper"]) <= tolerance
                        for a, e in zip(actual["feasible"], expected)
                    )
                    and actual["status"] == ("CONDITIONAL_BOUNDS" if expected else "INCONSISTENT_HOLD")
                    and not actual["semantic_acceptance"]
                    and not actual["source_truth_established"]
                )
            elif kind.startswith("pool "):
                data = copy.deepcopy(case["samples"])
                if kind == "pool translated":
                    data = [[x + 273.15 for x in group] for group in data]
                if kind == "pool permuted":
                    data.reverse()
                groups = [
                    {
                        "n": len(g),
                        "mean": statistics.mean(g),
                        "dispersion": statistics.stdev(g) / math.sqrt(len(g))
                        if kind == "pool SE conversion"
                        else statistics.stdev(g),
                        "dispersion_kind": "SE" if kind == "pool SE conversion" else "SD",
                    }
                    for g in data
                ]
                actual = engine.pool(groups, mutually_exclusive=True, same_endpoint=True)
                all_data = sum(data, [])
                expected = {"n": len(all_data), "mean": statistics.mean(all_data), "sd": statistics.stdev(all_data)}
                record.update(
                    actual=actual, oracle=expected, passed=all(abs(actual[k] - expected[k]) <= 1e-9 for k in expected)
                )
            elif kind == "paired missing covariance":
                actual = engine.mean_difference({"mean": 12.0}, {"mean": 9.0}, design="paired_unknown_covariance")
                record.update(
                    actual=actual,
                    passed=actual["se"] is None
                    and actual["status"] == "POINT_ONLY_COVARIANCE_MISSING"
                    and actual["difference"] == 3,
                )
            elif kind == "JATS spans and digest":
                actual = engine.read_jats(fixture, digest(fixture))
                record.update(
                    actual=actual,
                    passed=actual["tables"]["t1"]["rows"] == [["A", "B", "B"], ["A", "1", "2"]]
                    and actual["semantic_acceptance"] is False,
                )
            elif kind == "unequal semantic units":
                spec = spec_for(cases[0])
                spec["assumptions"] = [
                    "Adversarial review case: cells have unequal physical units; do not interpret arithmetic as useful delivery."
                ]
                actual = engine.rounded_mean_model(spec)
                record.update(
                    actual=actual,
                    passed=actual["semantic_acceptance"] is False
                    and actual["source_truth_established"] is False
                    and actual["production_authority"] is False,
                    outcome="ARITHMETIC_ONLY_REQUIRES_SEMANTIC_REVIEW",
                    limitation="The engine does not understand or reject unequal declared physical units. A reviewer must refuse this mission; this check is not accepted delivery.",
                )
            else:
                spec = spec_for(cases[0])
                if kind in {"NaN", "infinity", "Boolean"}:
                    spec["cell_means"][0] = {"NaN": math.nan, "infinity": math.inf, "Boolean": True}[kind]
                if kind == "unknown top-level field":
                    spec["unrecognized_schema"] = "future/v99"
                if kind == "overlap contrast":
                    spec["contrast_negative_cells"] = [1, 2]
                if kind == "unknown aggregate field":
                    spec["aggregates"][0]["covariance"] = 0.4
                try:
                    if kind == "unknown dispersion":
                        actual = engine.pool(
                            [{"n": 10, "mean": 5, "dispersion": 1, "dispersion_kind": "CI"}],
                            mutually_exclusive=True,
                            same_endpoint=True,
                        )
                    elif kind == "digest mismatch":
                        actual = engine.read_jats(fixture, "0" * 64)
                    elif kind == "XML entity declaration":
                        actual = engine.read_jats(entity)
                    else:
                        actual = engine.rounded_mean_model(spec)
                    record.update(actual=actual, passed=False, expected="ValueError rejection")
                except ValueError as exc:
                    record.update(passed=True, outcome="REJECT", exception=str(exc))
        except Exception as exc:
            record.update(passed=False, unexpected_exception=repr(exc))
        results.append(record)
    output = {
        "schema": "independent-confirmation-results/v1",
        "executed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "duration_seconds": time.perf_counter() - start,
        "plan_sha256": digest(ROOT / "plan.json"),
        "generated_cases_sha256": digest(ROOT / "generated-cases.json"),
        "capsule_sha256": digest(capsule),
        "received_engine_sha256": digest(runtime / "evidence_engine.py"),
        "oracle_sha256": digest(ROOT.parent / "development-review/check_development.py"),
        "case_count": len(results),
        "passed": sum(r["passed"] for r in results),
        "failed": sum(not r["passed"] for r in results),
        "labels": [
            "synthetic",
            "executed",
            "no customer acceptance",
            "no source-truth validation",
            "no live authority",
        ],
        "results": results,
    }
    (ROOT / "results.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
