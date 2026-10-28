# SPDX-License-Identifier: Apache-2.0
"""Prospective source-bound confirmation; requires an externally supplied freeze hash."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest, load_record, safe_json_loads

from .cases import case
from .discovery import Hypothesis, discover
from .economics import evaluate
from .engine import ConstructionPolicy, ProductionBrief, construct
from .manifest import freeze, verify_freeze
from .native import LiveAdapter, proposal
from .verify import exhaustive, verify

REPO = Path(__file__).resolve().parents[2]
HOME = Path(__file__).resolve().parent


def frozen_paths() -> list[str]:
    """Bind every new source/test/input plus the unchanged native runtime closure."""
    paths = [
        *HOME.glob("*.py"),
        *HOME.glob("tests/*.py"),
        *HOME.glob("inputs/*.json"),
        *REPO.glob("alpha_factory_v1/core/runtime/**/*.py"),
        REPO / "mypy-runtime.ini",
        REPO / "requirements.lock",
        REPO / "requirements-dev.lock",
        REPO / "pyproject.toml",
    ]
    return sorted(str(p.relative_to(REPO)) for p in paths if p.is_file())


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(manifest_path: Path, expected_sha256: str, output: Path) -> dict[str, Any]:
    """Verify the exact inventory before execution, and again before receipts."""
    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("freeze differs from the independently retained expected digest")
    manifest = safe_json_loads(raw)
    if sorted(manifest["files"]) != frozen_paths():
        raise ValueError("freeze omits or adds a scientific source, policy, input or acceptance path")
    verify_freeze(REPO, manifest)
    if output.exists():
        raise FileExistsError("keep original campaign; use a new output directory")
    output.mkdir(parents=True)
    acceptance = safe_json_loads((HOME / "inputs/ACCEPTANCE.json").read_bytes())
    policy = load_record(ConstructionPolicy, (HOME / "inputs/POLICY.json").read_bytes())
    cases, results, elapsed = [], [], []
    for domain in acceptance["domains"]:
        for seed in acceptance["confirmation_seeds"]:
            brief = case(domain, seed)
            started = time.perf_counter_ns()
            report = construct(brief, policy)
            elapsed.append(time.perf_counter_ns() - started)
            baseline = exhaustive(brief)
            if not report["search_complete"] or (report["best"] is None) != (baseline is None):
                raise ValueError("incomplete search or conventional feasibility mismatch")
            if baseline:
                if not verify(brief, policy, report) or report["best"]["rank"] != baseline["rank"]:
                    raise ValueError("witness or conventional rank mismatch")
            cases.append(brief.model_dump())
            results.append(
                {
                    "brief_id": brief.brief_id,
                    "binding": report["binding"],
                    "result": report,
                    "independent_conventional": baseline,
                    "comparison": "tie",
                    "oracle_scope": "independent exhaustive full grammar with the same recipes and information",
                }
            )
    save(output / "FRESH_CASES.json", cases)
    save(output / "FRESH_RESULTS.json", results)
    discoveries, rejection_archive, samples = [], [], {}
    for domain in ("transformer", "metrology"):
        brief = load_record(ProductionBrief, (HOME / f"inputs/{domain}.json").read_bytes())
        hypothesis = load_record(Hypothesis, (HOME / f"inputs/{domain}-hypothesis.json").read_bytes())
        decision = discover(hypothesis, brief, prior_rejections=[])
        if decision["decision"] != "HOLD-no-admitted-opportunity":
            raise ValueError("this authored study cannot admit a commercial opportunity")
        discoveries.append(decision)
        rejection = {
            "causal_core_digest": decision["causal_core_digest"],
            "hypothesis_id": hypothesis.hypothesis_id,
            "reasons": decision["reasons"],
            "hypothesis_digest": decision["hypothesis_digest"],
        }
        rejection["rejection_digest"] = digest("production-frontier-rejection/v1", rejection)
        rejection_archive.append(rejection)
        if not discover(hypothesis, brief, prior_rejections=rejection_archive)["decision"].startswith(
            "previously-rejected"
        ):
            raise ValueError("failed causal cores must remain rejected")
        result = construct(brief, policy)
        if not result["best"] or not verify(brief, policy, result):
            raise ValueError("sample lacks a valid independently replayed witness")
        samples[domain] = {
            "brief": brief.model_dump(),
            "result": result,
            "native_opportunity_proposal": proposal(brief).model_dump(),
            "registered_in_native_custody": False,
        }
    save(output / "DISCOVERY.json", discoveries)
    save(output / "REJECTIONS.json", rejection_archive)
    save(output / "SAMPLES.json", samples)
    commercial = evaluate(safe_json_loads((HOME / "inputs/ECONOMICS.json").read_bytes()))
    save(output / "COMMERCIAL.json", commercial)
    # Freeze the selection rule, not an answer: first feasible prospective
    # metrology case in the predeclared bank, with every other case retained.
    fresh = next(
        ProductionBrief.model_validate(c)
        for c, r in zip(cases, results)
        if c["brief_id"].startswith("metrology-") and r["result"]["best"] is not None
    )
    original = construct(fresh, policy)
    ordinary = construct(ProductionBrief.model_validate_json(canonical(fresh)), policy)
    conventional = exhaustive(fresh)
    if original != ordinary or not conventional or original["best"]["rank"] != conventional["rank"]:
        raise ValueError("ordinary-library or conventional replacement mismatch")
    save(
        output / "EXPANSION.json",
        {
            "new_brief": fresh.brief_id,
            "material_difference": "Joint metrology and destructive specimen conservation, after shared industrial batch construction",
            "same_machinery": True,
            "bespoke_solution_injected": False,
            "compiler_result": original,
            "ordinary_library_same_asset": ordinary,
            "instrument_disabled_conventional_replacement": conventional,
            "comparison": "All identical-information arms tie; conventional replacement still produces the outcome",
            "expanded_physical_productive_feasibility_established": False,
            "retained_alpha_established": False,
            "measured_transfer_to_authenticated_second_agent": False,
            "reason": "Only authored-model software conformance is measured. No newly feasible physical activity, real independent recipient or paid frontier trial is established",
        },
    )
    verify_freeze(REPO, manifest)
    summary = {
        "schema": "production-frontier-confirmation/v1",
        "freeze_sha256": expected_sha256,
        "frozen_files": len(manifest["files"]),
        "fresh_cases": len(results),
        "feasible": sum(r["result"]["best"] is not None for r in results),
        "no_plan": sum(r["result"]["best"] is None for r in results),
        "conventional_ties": len(results),
        "independent_witnesses_checked": sum(len(r["result"]["candidates"]) for r in results),
        "compiler_time_ns_median": sorted(elapsed)[len(elapsed) // 2],
        "compiler_time_ns_max": max(elapsed),
        "timing_scope": "One local process, declared-model compiler only; excludes oracle, source research, development and billing",
        "admitted_opportunities": 0,
        "commercial_decision": commercial["commercial_decision"],
        "actual_collections_micro_usd": 0,
        "actual_cost_micro_usd": None,
        "live_adapter": LiveAdapter().status(),
        "live_frontier_provider_trials": 0,
        "real_production_actions": 0,
        "authority_granted": False,
        "next_test": discoveries[0]["next_experiment"],
        "next_test_cap_micro_usd": discoveries[0]["next_experiment_cap_micro_usd"],
        "next_test_authorized": False,
    }
    save(output / "SUMMARY.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "run"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(REPO, frozen_paths(), args.manifest)
        print(hashlib.sha256(args.manifest.read_bytes()).hexdigest())
    else:
        if not args.expected_sha256 or not args.output:
            parser.error("run requires independently retained --expected-sha256 and a new --output")
        print(json.dumps(run(args.manifest, args.expected_sha256, args.output), indent=2))


if __name__ == "__main__":
    main()
