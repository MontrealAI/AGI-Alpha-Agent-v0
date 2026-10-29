# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import shutil
import time
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.invention_automation import engine, programs
from alpha_factory_v1.core.runtime.structural_transfer.contracts import digest, write_new

ROOT = Path(__file__).resolve().parents[2]


def fault_case(**changes: Any) -> dict[str, Any]:
    return {
        "id": "job1",
        "scope": "software-fault-fixture",
        "price": 1_000_000,
        "screening": 10_000,
        "measurement": 5_000,
        "production": 100_000,
        "required_value": 1_000_000,
        "buyer_cash": 2_000_000,
        "observed_value": 1_500_000,
        "measurement_valid": True,
        "settlement": "clear",
        "deadline": 100,
        **changes,
    }


def component_reference() -> dict[str, Any]:
    return {
        "schema": "agialpha/contingent-strategy/v1",
        "steps": [
            {"op": "screen"},
            {"op": "measure"},
            {"op": "guard", "test": programs.field("measurement_valid"), "constraint": "measurement-before-production"},
            {
                "op": "guard",
                "test": programs.sufficient(programs.field("measured_value"), programs.field("required_value")),
                "constraint": "measurement-before-production",
            },
            {
                "op": "guard",
                "test": programs.sufficient(
                    programs.field("available"),
                    {"op": "add", "left": programs.field("price"), "right": programs.field("production")},
                ),
                "constraint": "collateral-and-production",
            },
            {"op": "fund"},
            {
                "op": "guard",
                "test": programs.sufficient(programs.field("available"), programs.field("production")),
                "constraint": "paid-production",
            },
            {"op": "produce"},
            {"op": "inspect"},
            {"op": "settle"},
        ],
    }


def source_manifest() -> dict[str, str]:
    paths = list((ROOT / "alpha_factory_v1/core/runtime/invention_automation").glob("*.py"))
    paths += list((ROOT / "alpha_factory_v1/core/runtime/invention_verification").glob("*.py"))
    paths += list((ROOT / "contrib/invention_automation").glob("*.py"))
    paths += [
        ROOT / "alpha_factory_v1/core/runtime/claim_probe/protected_exchange.py",
        ROOT / "alpha_factory_v1/core/runtime/claim_probe/contracts.py",
        ROOT / "alpha_factory_v1/core/runtime/structural_transfer/contracts.py",
        ROOT / "alpha_factory_v1/core/runtime/cli.py",
        ROOT / "studies/invention-automation-20261029/REGISTRY.md",
    ]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    frozen = source_manifest()
    write_new(args.output / "source-freeze.json", frozen)
    for relative in frozen:
        destination = args.output / "source-snapshot" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    protocol = {
        "class": "exploratory software-fault tests",
        "confirmatory_looks": 0,
        "alpha_spent": "0",
        "meaningful_business_comparator": "NOT_ADMITTED",
        "units": "simulated-microUSD",
        "one_route": "local nonrecourse SIM only",
        "opening": "finite fixed per registered test, no injected cash",
        "primary": "no avoidable production before decisive measurement or funded collateral capacity",
        "control": "competent component policy only, not operating-business superiority",
        "no_reinvestment": "fixture margins are not earned business funds; research costs unmetered",
        "maximum_cases": 16,
        "maximum_operations_per_run": 256,
    }
    write_new(args.output / "protocol.json", protocol)
    index = []

    def run(name: str, program: dict[str, Any], cases: list[dict[str, Any]], opening: int) -> dict[str, Any]:
        request = {"program": program, "cases": cases, "opening": opening}
        write_new(args.output / f"{name}.request.json", request)
        result = engine.execute(program, cases, args.output / f"{name}.sqlite", opening=opening)
        write_new(args.output / f"{name}.result.json", result)
        index.append(name)
        return result

    p0 = programs.initial_program()
    technical_cases = [fault_case(observed_value=0)]
    first = run("technical-v0", p0, technical_cases, 5_000_000)
    technical = engine.failures(technical_cases, first)[0]
    write_new(args.output / "technical-witness.json", technical)
    tc = engine.validate_criticism(
        p0, technical_cases, technical, args.output / "technical-reproduction.sqlite", opening=5_000_000
    )
    p1 = programs.adapt(p0, tc)
    write_new(args.output / "technical-constraint.json", tc)
    revised = run("technical-v1", p1, technical_cases, 5_000_000)
    if engine.failures(technical_cases, revised):
        raise AssertionError("technical witness not corrected")
    economic_cases = [fault_case(production=500_000)]
    second = run("economic-v1", p1, economic_cases, 1_200_000)
    economic = next(x for x in engine.failures(economic_cases, second) if x["critic"] == "economic")
    write_new(args.output / "economic-witness.json", economic)
    ec = engine.validate_criticism(
        p1, economic_cases, economic, args.output / "economic-reproduction.sqlite", opening=1_200_000
    )
    p2 = programs.adapt(p1, ec)
    write_new(args.output / "economic-constraint.json", ec)
    repaired = run("economic-v2", p2, economic_cases, 1_200_000)
    if engine.failures(economic_cases, repaired):
        raise AssertionError("economic witness not corrected")
    invalid = {"critic": "irrelevant", "family": "raise-price", "reason": "assume richer buyers"}
    try:
        engine.validate_criticism(
            p2, economic_cases, invalid, args.output / "invalid-criticism.sqlite", opening=1_200_000
        )
    except ValueError as error:
        write_new(args.output / "irrelevant-criticism.json", {"promoted": False, "reason": str(error)})
    else:
        raise AssertionError("irrelevant criticism promoted")
    panel: list[dict[str, Any]] = []
    variants: list[tuple[str, dict[str, Any]]] = [
        ("valid", {}),
        ("lowValue", {"observed_value": 0}),
        ("invalidMeasurement", {"measurement_valid": False}),
        ("unfundedBuyer", {"buyer_cash": 0}),
        ("expensive", {"production": 500_000}),
        ("nonpayment", {"settlement": "withhold"}),
        ("interruption", {"settlement": "interrupt"}),
    ]
    for opening in [1_200_000, 5_000_000]:
        for variant, changes in variants:
            panel.append({"id": f"{variant}-{opening}", "cases": [fault_case(**changes)], "opening": opening})
    write_new(args.output / "panel-registry.json", panel)
    comparisons = []
    reference = component_reference()
    for item in panel:
        full = run(item["id"] + "-corrected", p2, item["cases"], item["opening"])
        control = run(item["id"] + "-reference", reference, item["cases"], item["opening"])
        comparisons.append(
            {
                "id": item["id"],
                "same_outcomes": full["outcomes"] == control["outcomes"],
                "same_economics": full["summary"] == control["summary"],
                "candidate_summary": full["summary"],
                "control_summary": control["summary"],
            }
        )
    write_new(args.output / "paired-comparison.json", comparisons)
    write_new(args.output / "index.json", index)
    write_new(args.output / "candidate-final.json", p2)
    now = resource.getrusage(resource.RUSAGE_SELF)
    write_new(
        args.output / "execution-resource.json",
        {
            "wall_seconds": format(time.monotonic() - start, ".9f"),
            "cpu_seconds": format(now.ru_utime + now.ru_stime - usage.ru_utime - usage.ru_stime, ".9f"),
            "process_peak_rss_kib": now.ru_maxrss,
            "new_cash_spend": "0",
            "model_calls_in_this_runner": 0,
            "development_model_usage": "UNMETERED",
            "tariff_equivalent_cost": "UNKNOWN",
            "research_funding": "authorized local research resources, not SIM earnings",
        },
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "cases": len(panel),
                "component_ties": sum(x["same_outcomes"] and x["same_economics"] for x in comparisons),
                "technical_waste_before": first["summary"]["expenses"],
                "technical_waste_after": revised["summary"]["expenses"],
                "economic_payables_before": second["summary"]["payables"],
                "economic_payables_after": repaired["summary"]["payables"],
                "business_go": False,
                "confirmed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
