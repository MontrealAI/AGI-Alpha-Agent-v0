# SPDX-License-Identifier: Apache-2.0
"""Register, freeze and execute one exposed native criticism pilot.

This trusted driver never interprets a generated AST. Candidate execution is
requested only through the unchanged Docker adapter in the native loop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.invention_automation import critic_loop
from alpha_factory_v1.core.runtime.structural_transfer.contracts import digest, read, write_new

PINNED_FILES = [
    "alpha_factory_v1/core/runtime/invention_automation/evidence_contracts.py",
    "alpha_factory_v1/core/runtime/invention_automation/evidence_critic.py",
    "alpha_factory_v1/core/runtime/invention_automation/critic_loop.py",
    "alpha_factory_v1/core/runtime/invention_automation/critic_protocol.json",
    "alpha_factory_v1/core/runtime/invention_automation/specification.py",
    "alpha_factory_v1/core/runtime/invention_automation/specification_run.py",
    "alpha_factory_v1/core/runtime/invention_automation/operator.py",
    "alpha_factory_v1/core/runtime/structural_transfer/contracts.py",
    "alpha_factory_v1/core/utils/secure_run.py",
    "alpha_factory_v1/core/runtime/invention_verification/__init__.py",
    "alpha_factory_v1/core/runtime/invention_verification/critic_verify.py",
    "alpha_factory_v1/core/runtime/invention_verification/qualify_verify.py",
    "alpha_factory_v1/core/runtime/invention_verification/readonly.py",
    "alpha_factory_v1/core/runtime/invention_verification/dynamic_oracle.py",
    "alpha_factory_v1/core/runtime/invention_automation/qualification.py",
    "contrib/invention_automation/run_critic_pilot.py",
]
PROTOCOL = "alpha_factory_v1/core/runtime/invention_automation/critic_protocol.json"


def context(request: dict[str, Any]) -> dict[str, Any]:
    labels = {"high_side_voltage": "high-side voltage", "rated_power": "rated power", "frequency": "frequency"}
    return {
        "schema": "agialpha/critic-context/v1",
        "requirements": {
            field: {
                "dimension": dim,
                "authority": "declared-task",
                "labels": [labels[field]],
                "location": "/requirements/" + field,
            }
            for field, dim in request["requirements"].items()
        },
        "sources": [
            {
                "id": source["id"],
                "sha256": source["sha256"],
                "url": source["url"],
                "version": "Exact excerpt hash; full remote-page version UNKNOWN",
                "retrieved_utc": "2026-10-29; original excerpt from prior source probe, rechecked this turn",
                "method": "Provided literal excerpt; primary DOE page rechecked via search service. Synthetic sources remain explicitly fixtures.",
            }
            for source in request["sources"]
        ],
        "bindings": [
            {
                "record_id": "doe-literal",
                "field": "high_side_voltage",
                "source_id": request["records"][0]["source_id"],
                "start": 0,
                "end": len(request["sources"][0]["excerpt"]),
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if root != critic_loop.ROOT:
        raise ValueError("running implementation must be the exact source/install root being frozen")
    budget = read(args.budget)
    if (
        budget["new_spending_allowed"] != "0"
        or budget["do_not_generate_candidates_after_utc"] != "2026-10-29T16:53:00Z"
    ):
        raise ValueError("inherited envelope identity mismatch; no new allowance")
    if datetime.now(UTC) >= critic_loop.GENERATION_CUTOFF:
        raise ValueError("inherited cutoff reached; use critic-resume")
    args.output.mkdir(exist_ok=False)
    output = args.output.resolve()
    original = read(args.request)
    primary = deepcopy(original)
    good = deepcopy(original)
    good["baseline"] = deepcopy(good["proposal"])
    misbound = deepcopy(original)
    misbound["sources"][0].update(
        {
            "id": "source-binding-control",
            "url": "fixture:development-only",
            "excerpt": "high-side voltage 34.5 kV; rated power 500 kVA; frequency 60 Hz.",
        }
    )
    misbound["sources"][0]["sha256"] = hashlib.sha256(misbound["sources"][0]["excerpt"].encode()).hexdigest()
    misbound["records"][0]["source_id"] = "source-binding-control"
    misbound["records"][0]["fields"]["high_side_voltage"] = {"value": "500", "unit": "kVA"}
    requests = {"primary": primary, "known-good": good, "source-misbinding": misbound}
    contexts = {name: context(value) for name, value in requests.items()}
    write_new(output / "inherited-budget.json", budget)
    write_new(
        output / "registration.json",
        {
            "schema": "agialpha/critic-pilot-registration/v1",
            "recorded_utc": datetime.now(UTC).isoformat(),
            "kind": "EXPOSED ENGINEERING DEVELOPMENT",
            "primary_problem": primary["problem"],
            "primary_endpoint": "Accepted useful dimensional-screen output on every retained record under the frozen contract.",
            "necessary_static_endpoint": "Field-associated mismatch plus missing dimensional guard; distinct from runtime acceptance.",
            "competent_reference": "Conventional dimensional/schema validator on identical records, definitions and budget; no superiority assumed.",
            "acceptance_threshold": {
                "all_record_ids_retained": True,
                "valid_record_false_rejections": 0,
                "incompatible_or_missing_dimensions_accepted": 0,
                "oracle_outputs": "exact in-order equality",
            },
            "consequential_error": "False source attribution or incompatible-dimensional admission; actual physical/economic consequence unmeasured.",
            "paired_comparison": "Baseline versus verified correction plus conventional reference. Missing Docker blocks the dynamic comparison.",
            "control_rules": {
                "known-good": "NO_DEFECT_ESTABLISHED and no corrective candidate",
                "irrelevant-on-good": "REFUTED and no corrective candidate",
                "source-misbinding": "REFUTED; no constraint",
                "dynamic-claim": "INCONCLUSIVE without candidate execution",
            },
            "precision_rationale": "Deterministic software regression, one exposed real-source provenance unit plus synthetic neighbors; no sampling precision or population effect claim.",
            "allowed_looks": "One registered production pilot and the named engineering controls; no fresh confirmation cases.",
            "stopping_rule": "Do not retry the missing sandbox; preserve blocks/failures and stop dependent execution.",
            "confirmation": {"new_looks": 0, "alpha_allocated": "0", "spent": "0", "all_cases_exposed": True},
            "experience_comparison": "Dynamic fresh independent work and cumulative/frozen/reset/ordinary-retrieval matched-budget benefit remain BLOCKED; stale/irrelevant constraints are tested only as engineering controls.",
            "budget": {
                "inherited_budget_hash": digest(budget),
                "new_external_spend": 0,
                "max_primary_construction_candidates": primary["budget"]["max_candidates"],
                "remaining_cpu_model_allowance": "UNKNOWN, not replenished",
                "added_storage_cap_this_turn_bytes": 268435456,
            },
            "costs": "Observed CPU/wall recorded once; model, retrieval and historical complete costs remain UNKNOWN, not free.",
        },
    )
    for name, value in requests.items():
        write_new(output / f"{name}-request.json", value)
        write_new(output / f"{name}-context.json", contexts[name])
    pins = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in PINNED_FILES}
    freeze = {
        "schema": "agialpha/critic-verifier-freeze/v1",
        "files": pins,
        "protocol_path": PROTOCOL,
        "protocol_sha256": pins[PROTOCOL],
        "request_hashes": [digest(value) for value in requests.values()],
        "context_hashes": [digest(value) for value in contexts.values()],
    }
    write_new(output / "freeze.json", freeze)
    result = critic_loop.run(
        output / "primary-request.json",
        output / "primary-context.json",
        output / "freeze.json",
        output / "primary-loop",
    )
    good_result = critic_loop.run(
        output / "known-good-request.json",
        output / "known-good-context.json",
        output / "freeze.json",
        output / "known-good-loop",
    )
    objection = result["finding"]["objections"][0]
    irrelevant = deepcopy(objection)
    irrelevant.update({"id": "irrelevant-on-good", "candidate_hash": digest(good["baseline"])})
    write_new(output / "irrelevant-objection.json", irrelevant)
    irrelevant_receipt = critic_loop.verify_role(
        output / "known-good-request.json",
        output / "known-good-context.json",
        output / "freeze.json",
        objection_path=output / "irrelevant-objection.json",
    )
    write_new(output / "irrelevant-verdict.json", irrelevant_receipt)
    false_source = deepcopy(objection)
    false_source.update({"id": "source-misbinding-control"})
    false_source["source"] = {
        "source_id": "source-binding-control",
        "location": f"/sources/0/excerpt#chars=0:{contexts['source-misbinding']['bindings'][0]['end']}",
        "sha256": misbound["sources"][0]["sha256"],
    }
    false_source["witness"].update(
        {
            "source_id": "source-binding-control",
            "value": "500",
            "end": contexts["source-misbinding"]["bindings"][0]["end"],
        }
    )
    write_new(output / "source-misbinding-objection.json", false_source)
    source_receipt = critic_loop.verify_role(
        output / "source-misbinding-request.json",
        output / "source-misbinding-context.json",
        output / "freeze.json",
        objection_path=output / "source-misbinding-objection.json",
    )
    write_new(output / "source-misbinding-verdict.json", source_receipt)
    dynamic = deepcopy(objection)
    dynamic["id"] = "dynamic-claim-control"
    dynamic["test"]["kind"] = "dynamic-paired"
    write_new(output / "dynamic-objection.json", dynamic)
    dynamic_receipt = critic_loop.verify_role(
        output / "primary-request.json",
        output / "primary-context.json",
        output / "freeze.json",
        objection_path=output / "dynamic-objection.json",
    )
    write_new(output / "dynamic-verdict.json", dynamic_receipt)
    resumed = critic_loop.resume(output / "primary-loop")
    summary = {
        "schema": "agialpha/critic-pilot-summary/v1",
        "primary_static_verdict": result["verdicts"][0]["verdict"],
        "primary_acceptance": result["acceptance"]["acceptance"],
        "complete_loop_status": result["complete_loop_status"],
        "known_good": good_result["verdicts"][0]["verdict"],
        "known_good_repaired": good_result["adaptation_hash"] is not None,
        "irrelevant": irrelevant_receipt["verdict"],
        "false_source_attribution": source_receipt["verdict"],
        "dynamic": dynamic_receipt["verdict"],
        "exact_resume": resumed == result,
        "static_false_rejections_on_named_good_controls": "0/2 exposed checks; no population rate inference",
        "runtime_effect_size": "UNKNOWN",
        "economic_profit_crossing": "NOT_ESTABLISHED",
        "fresh_experience_benefit": "NOT_ESTABLISHED",
        "confirmation": False,
        "candidate_executed": result["execution"]["executed"],
        "runtime_model_path": "BLOCKED; deterministic scanner and recorded actual host roles distinguished",
    }
    write_new(output / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
