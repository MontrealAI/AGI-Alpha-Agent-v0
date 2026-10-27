# SPDX-License-Identifier: Apache-2.0
"""Build the self-contained bilingual research demonstration from recorded evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent


def load(relative: str, required: bool = False) -> Any:
    path = STUDY / relative
    if not path.exists():
        if required:
            raise FileNotFoundError(relative)
        return None
    return json.loads(path.read_text())


def file_sha(relative: str) -> str | None:
    path = STUDY / relative
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def build(require_complete: bool = False) -> dict[str, Any]:
    pilot = load("results/pilot_summary.json", require_complete)
    composition = load("results/composition_summary.json", require_complete)
    economics = load("economics/results/summary.json", require_complete)
    if require_complete:
        if not economics.get("groups", {}).get("reference/ordinary_U"):
            raise ValueError("Missing final economic reference result")
        if not isinstance(composition, dict):
            raise ValueError("Missing final composition results")
    opportunity_paths = {
        "selection": "opportunity/SELECTION.json",
        "confirmation": "opportunity/results/confirmation_summary.json",
        "packet": "opportunity/conventional/packet.json",
        "conventional": "opportunity/conventional/acceptance.json",
        "requests": "opportunity/protocol/public_case/requests.json",
        "sources": "opportunity/protocol/public_case/SOURCE_FILES.json",
        "instrument_freeze": "opportunity/development/INSTRUMENT_FREEZE.json",
        "integration": "opportunity/integration/results/summary.json",
        "timing": "opportunity/arrangement/results/timing_examples.json",
        "selection_result": "opportunity/arrangement/results/reference_selection.json",
        "stress": "opportunity/arrangement/results/fresh_stress.json",
        "stress_complete": "opportunity/arrangement/results/FRESH_COMPLETE.json",
        "value": "economics/value_results/summary.json",
    }
    opportunity = {key: load(path, require_complete) for key, path in opportunity_paths.items()}
    if require_complete:
        confirmation = opportunity["confirmation"]
        for arm in ("U", "E", "E_plus"):
            row = confirmation.get("arms", {}).get(arm)
            if not row or "passed_missions" not in row or "accepted_output_cost_usd" not in row:
                raise ValueError("Missing final scientific confirmation for " + arm)
        if len(opportunity["packet"].get("missions", [])) != 4:
            raise ValueError("Four source-bound scientific missions are required")
        if len(opportunity["timing"].get("cases", [])) != 6:
            raise ValueError("Six exact cash-timing diagnostics are required")
    records: dict[str, Any] = {}
    for arm in ("U", "E", "E_plus"):
        info = (pilot or {}).get("arms", {}).get(arm, {})
        state = load(f"results/trials/{arm}/state.json") or {}
        cases = []
        for case in ("c1", "c2", "c3", "c4"):
            result = load(f"results/trials/{arm}/{case}_acceptance.json")
            if result:
                cases.append(
                    {
                        "case": case,
                        "accepted": result.get("accepted"),
                        "passed": result.get("passed"),
                        "total": result.get("total"),
                        "checks": result.get("checks", []),
                    }
                )
        records[arm] = {
            "accepted": info.get("accepted", sum(bool(r["accepted"]) for r in cases) if len(cases) == 4 else None),
            "attempted": info.get("attempted", 4),
            "elapsed_seconds": info.get("elapsed_seconds", state.get("elapsed_seconds")),
            "operations": info.get("operations", state.get("operations")),
            "test_executions": info.get("test_executions", state.get("test_executions")),
            "within_envelope": info.get("within_envelope", state.get("within_envelope")),
            "cases": cases,
        }
        if require_complete and (records[arm]["accepted"] is None or len(cases) != 4):
            raise ValueError("Missing final primary evidence for " + arm)
    source_paths = [
        "protocol/study_design.json",
        "protocol/CONFIRMATION_FREEZE.json",
        "protocol/COMPOSITION_FREEZE.json",
        "workflows/expert_v1.json",
        "workflows/learned_v2.json",
        "workflows/contract_probes.py",
        "results/pilot_summary.json",
        "results/composition_summary.json",
        "economics/results/summary.json",
        "economics/results/FREEZE.json",
        "economics/results/CONFIRMATION_COMPLETE.json",
        "integration/results/workflow-v2/summary.json",
    ]
    source_paths.extend(opportunity_paths.values())
    data = {
        "edition": "2.1.0",
        "opportunity": opportunity,
        "design": load("protocol/study_design.json", True),
        "primary": records,
        "pilot_raw": pilot,
        "composition_raw": composition,
        "composition_protocol": load("protocol/COMPOSITION_FREEZE.json", True),
        "economics": economics,
        "economic_protocol": load("economics/protocol.json", True),
        "economic_freeze": load("economics/results/FREEZE.json"),
        "economic_completion": load("economics/results/CONFIRMATION_COMPLETE.json"),
        "integration": load("integration/results/workflow-v2/summary.json", True),
        "expert": load("workflows/expert_v1.json", True),
        "learned": load("workflows/learned_v2.json", True),
        "helper": (STUDY / "workflows/contract_probes.py").read_text(),
        "source_hashes": {path: file_sha(path) for path in source_paths},
        "final_data_required": require_complete,
    }
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace("</", "<\\/")
    template = (HERE / "template.html").read_text()
    for marker, filename in {
        "__OPPORTUNITY_STYLE__": "opportunity_styles.css",
        "__OPPORTUNITY_HTML__": "opportunity_sections.html",
        "__OPPORTUNITY_JS__": "opportunity_demo.js",
    }.items():
        if template.count(marker) != 1:
            raise ValueError("Template source marker must occur exactly once: " + marker)
        template = template.replace(marker, (HERE / filename).read_text())
    if template.count("__EVIDENCE_JSON__") != 1:
        raise ValueError("Template data marker must occur exactly once")
    output = template.replace("__EVIDENCE_JSON__", encoded)
    (HERE / "index.html").write_text(output)
    receipt = {
        "schema": "operational-alpha-browser-build/v1",
        "final_data_required": require_complete,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "template_sha256": hashlib.sha256((HERE / "template.html").read_bytes()).hexdigest(),
        "component_sha256": {
            name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
            for name in ("opportunity_styles.css", "opportunity_sections.html", "opportunity_demo.js")
        },
        "html_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "bytes": len(output.encode()),
        "source_hashes": data["source_hashes"],
        "data_status": "complete" if require_complete else "development",
    }
    (HERE / "build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.require_complete), indent=2))
