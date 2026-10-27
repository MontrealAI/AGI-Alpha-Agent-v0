"""Build the offline bilingual evidence explorer from immutable study receipts."""

from __future__ import annotations

import base64
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
SOURCES: dict[str, dict] = {}


def read(relative: str) -> dict | list:
    """Read a frozen receipt and retain its exact on-disk identity."""
    raw = (STUDY / relative).read_bytes()
    SOURCES[relative] = {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if relative.endswith(".gz"):
        raw = gzip.decompress(raw)
        SOURCES[relative]["decoded_sha256"] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def main() -> None:
    """Extract display evidence without running or modifying any evaluated method."""
    primary = read("evaluation/results/confirmation-v1/summary.json")
    prospective = read("evaluation/prospective-v1/results/confirmation-v1/summary.json")
    transfer = read("integration/results/confirmation-v1/summary.json")
    hosted = read("evaluation/hosted-grading-v1/summary.json")
    economic = read("economics/confirmation/summary.json")
    admission = read("economics/admission.json")
    solvency_source = read("economics/postconfirmation_solvency_v1/RESULTS.json")
    solvency = {k: v for k, v in solvency_source.items() if k not in ("rows", "by_scenario_arm")}
    solvency["exposed_originally_cancelled"] = sum(
        bool(row["exposed"] and row["original_realization_action"] == "cancel_after_withdrawal")
        for row in solvency_source["rows"]
    )
    assert solvency["aggregate"]["exposed_packages"] == 114
    assert solvency["aggregate"]["original_producing_plans"] == 1889
    assert solvency["exposed_originally_cancelled"] == 11
    read("economics/postconfirmation_solvency_v1/FREEZE.json")
    solvency_readme_path = "economics/postconfirmation_solvency_v1/README.md"
    solvency_readme = (STUDY / solvency_readme_path).read_bytes()
    SOURCES[solvency_readme_path] = {
        "path": solvency_readme_path, "bytes": len(solvency_readme),
        "sha256": hashlib.sha256(solvency_readme).hexdigest(),
    }
    cash_examples = read("economics/confirmation/cash_examples.json")
    example = next(x for x in cash_examples if x["plan"]["arm"] == "retained_arranged" and x["seed"] == 21001)
    cases = {}
    for part in ("box", "cover"):
        job = f"{part}-counterfactual-family-v1"
        path = f"evaluation/results/confirmation-v1/{job}.report.json.gz"
        report = read(path)
        expected = next(r for r in primary["rows"] if r["job_id"] == job)["report_sha256"]
        assert SOURCES[path]["decoded_sha256"] == expected
        formal, hypothesis = report["family_proofs"]
        assert formal["basis"] == "formal_source_interpretation"
        assert hypothesis["basis"] == "researcher_counterfactual"
        records = [
            {
                "source_id": v["source_id"],
                "actual_id": v["actual_id"],
                "result_id": v["result_id"],
                "raw": v["raw"],
                "line": v["ref"]["line"],
                "formal_mm": str(Decimal(v["value_si"]) * 1000),
                "hypothesis_mm": str(Decimal(hypothesis["observed_values"][i]["value_si"]) * 1000),
            }
            for i, v in enumerate(formal["observed_values"])
        ]
        keys = (
            "basis", "status", "source_ids", "incoming_id", "source_asset_sha256", "incoming_asset_sha256",
            "destination_interval", "source_intervals", "all_source_intervals_subset",
            "all_observed_values_satisfy_destination", "target_feature_ids", "family_cardinality_consistent",
            "family_all_recorded_values_pass", "permutation_invariance_proved", "observed_numeric_counterexample",
            "not_proved", "physical_reuse_admitted",
        )
        cases[part] = {
            "job": job,
            "report_source": path,
            "report_sha256": expected,
            "assets": report["identity"]["assets"],
            "records": records,
            "formal": {k: formal.get(k) for k in keys},
            "hypothesis": {k: hypothesis.get(k) for k in keys},
            "destination_mm": [str(Decimal(formal["destination_interval"][f"{k}_si"]) * 1000) for k in ("low", "high")],
            "record_count": len(records),
            "source_characteristics": len(formal["source_ids"]),
            "receiving_features": len(formal["target_feature_ids"]),
        }
    repairs = []
    selections = {
        "box-size-to-width-evidence-v1": (["38", "41", "44", "47", "50", "53"], ["193"]),
        "cover-labeled-distance-evidence-v1": (["77"], ["155"]),
        "box-position-modifier-evidence-v1": (["80"], ["68"]),
        "cover-signed-tolerance-export-evidence-v1": (["11"], ["29"]),
    }
    for job, identifiers in selections.items():
        request_path = f"evaluation/prospective-v1/requests/{job}.json"
        request = read(request_path)
        report_path = f"evaluation/prospective-v1/results/confirmation-v1/{job}.report.json.gz"
        report = read(report_path)
        expected = next(r for r in prospective["rows"] if r["job_id"] == job)["report_sha256"]
        assert SOURCES[report_path]["decoded_sha256"] == expected
        bindings = []
        for doc in report["repair_requests"][0]["affected"]["documents"]:
            selected = identifiers[0 if doc["asset"] == "source_qif" else 1]
            for obj in doc["characteristic_obligations"]:
                if obj["characteristic_id"] in selected:
                    bindings.append({
                        "asset": doc["asset"], "sha256": doc["sha256"],
                        "characteristic_id": obj["characteristic_id"], "nominal_id": obj["nominal_id"],
                        "definition_id": obj["definition_id"], "refs": obj["refs"],
                    })
        repairs.append({
            "job": job, "mission": request["mission"], "request_path": request_path,
            "request_sha256": SOURCES[request_path]["sha256"], "report_sha256": expected,
            "requested_source_ids": identifiers[0], "requested_incoming_ids": identifiers[1],
            "bindings": bindings,
            "requirements": [{k: r[k] for k in ("id", "required_evidence", "reason", "status")} for r in report["repair_requests"]],
        })
    read("instrument/freeze.json")
    read("instrument_v0_1_1/freeze.json")
    read("evaluation/EVALUATOR_FREEZE.json")
    read("evaluation/PROSPECTIVE_EVALUATOR_FREEZE.json")
    read("economics/freeze.json")
    image = (HERE / "figures/01_actual_geometry.png").read_bytes()
    SOURCES["publication/figures/01_actual_geometry.png"] = {
        "path": "publication/figures/01_actual_geometry.png", "bytes": len(image),
        "sha256": hashlib.sha256(image).hexdigest(),
    }
    data = {
        "schema": "bilingual-frozen-evidence-explorer-v1",
        "evidence_date": "2026-10-27",
        "boundary": "Offline view of saved computational evidence. No model, CAD kernel, evaluator or market simulation runs in the browser.",
        "cases": cases, "primary": primary, "prospective": prospective, "repairs": repairs,
        "transfer": {
            "artifact_bytes": transfer["artifact_bytes"], "artifact_sha256": transfer["artifact_sha256"] ,
            "checks_passed": sum(x["passed"] for x in transfer["checks"]), "checks_total": len(transfer["checks"]),
            "fresh_mission_rechecked": transfer["fresh_mission_rechecked"],
            "actual_collections": transfer["actual_customer_collections_usd"],
            "actual_complete_cost": transfer["actual_complete_research_cost_usd"],
            "checks": transfer["checks"],
        },
        "hosted": hosted, "economics": {
            "summary": economic, "admission": admission, "cash_example": example,
            "postconfirmation_solvency_audit": solvency,
        },
        "sources": list(SOURCES.values()),
    }
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    template = (HERE / "demo.template.html").read_text()
    html = template.replace("__FROZEN_DATA__", serialized).replace("__GEOMETRY_BASE64__", base64.b64encode(image).decode())
    assert "__FROZEN_DATA__" not in html and "__GEOMETRY_BASE64__" not in html
    (HERE / "demo.html").write_text(html)
    (HERE / "demo-evidence.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    build_receipt = {
        "schema": "bilingual-demo-build/v1",
        "source_count": len(SOURCES),
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "template_sha256": hashlib.sha256((HERE / "demo.template.html").read_bytes()).hexdigest(),
        "outputs": {
            name: {"sha256": hashlib.sha256((HERE / name).read_bytes()).hexdigest(),
                   "bytes": (HERE / name).stat().st_size}
            for name in ("demo.html", "demo-evidence.json")
        },
        "solvency_boundary": "Post-confirmation conditional full-refund exposure; original expected profits unchanged; no rejection probability inferred.",
        "scientific_or_financial_model_executed": False,
    }
    (HERE / "demo-build.json").write_text(json.dumps(build_receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(HERE / "demo.html"), "bytes": len(html.encode()), "sources": len(SOURCES),
                      "sha256": hashlib.sha256(html.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
