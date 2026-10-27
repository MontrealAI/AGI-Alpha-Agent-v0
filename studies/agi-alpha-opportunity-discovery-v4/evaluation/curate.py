# SPDX-License-Identifier: Apache-2.0
"""Construct and freeze source-derived held-out jobs before candidate execution."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any

from source_oracle import canonical_hash, family_oracle, inspect_brep, inspect_step, read_qif, sha256

ROOT = Path(__file__).resolve().parent
GUARDS = [
    "feature_set_identity",
    "specimen_scope",
    "requirement_requalification",
    "measurement_adequacy",
    "current_authority",
]


def write_json(path: Path, value: Any) -> None:
    """Write one immutable curation output, refusing accidental replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def create(root: Path = ROOT) -> dict[str, Any]:
    """Prepare nine original-source jobs with no calls to the instrument."""
    started = time.perf_counter()
    protected = root / "protected"
    inputs = protected / "inputs"
    source_oracles: dict[str, dict[str, Any]] = {}
    source_manifest = json.loads((protected / "input_manifest.json").read_text())
    for entry in source_manifest:
        path = inputs / entry["file"]
        if sha256(path) != entry["sha256"]:
            raise ValueError("curator source changed")
    for part in ["Box", "Cover"]:
        for provider in ["FAIR", "incoming"]:
            name = f"{part}_{provider}"
            source_oracles[name] = read_qif(inputs / f"{name}.qif")
            write_json(protected / "oracles" / f"{name}.json", source_oracles[name])
        step_path = inputs / f"{part}_AP242.STP"
        write_json(protected / "oracles" / f"{part}_step.json", inspect_step(step_path))
        write_json(protected / "oracles" / f"{part}_brep.json", inspect_brep(step_path))

    def assets(part: str, geometry: bool = True) -> dict[str, Any]:
        names = {"source_qif": f"{part}_FAIR.qif", "incoming_qif": f"{part}_incoming.qif"}
        if geometry:
            names.update({"cad_step": f"{part}_AP242.STP", "reference_owl": f"{part}_integrated.owl"})
        return {key: {"path": f"../inputs/{name}", "sha256": sha256(inputs / name)} for key, name in names.items()}

    def family(part: str, nominal: str, incoming_id: str) -> dict[str, Any]:
        # The curator supplies requested membership, not a verified physical mapping.
        rows = source_oracles[f"{part}_FAIR"]["characteristics"]
        selected = [
            key
            for key, row in rows.items()
            if row["tag"] == "DiameterCharacteristicItem"
            and row["target"] is not None
            and row["target"]["raw"] == nominal
        ]
        return {"source_characteristic_ids": selected, "incoming_characteristic_id": incoming_id}

    specs = [
        (
            "box-report-comparability-v1",
            "Box",
            "evidence_audit",
            None,
            False,
            True,
            "Audit which cross-provider inspection claims the complete packet supports, contradicts or leaves unresolved.",
        ),
        (
            "cover-report-comparability-v1",
            "Cover",
            "evidence_audit",
            None,
            False,
            True,
            "Audit cross-provider requirement and measurement comparability without assuming label, graph or specimen identity.",
        ),
        (
            "box-formal-family-v1",
            "Box",
            "family_all",
            family("Box", "3.3", "33"),
            False,
            True,
            "Under the actual QIF formal units, test whether all selected recorded diameter values satisfy the requested interval.",
        ),
        (
            "box-counterfactual-family-v1",
            "Box",
            "family_all",
            family("Box", "3.3", "33"),
            True,
            True,
            "Separately evaluate the declared millimetre unit-repair hypothesis; preserve the formal result and every physical guard.",
        ),
        (
            "cover-counterfactual-family-v1",
            "Cover",
            "family_all",
            family("Cover", "4.5", "23"),
            True,
            True,
            "Test the entire selected recorded family under the stated unit hypothesis, without inferring feature-set coverage.",
        ),
        (
            "box-feature-localization-v1",
            "Box",
            "feature_localization",
            family("Box", "3.3", "33"),
            True,
            True,
            "Identify the particular physical feature for an investigation; a family-wide conjunction is insufficient.",
        ),
        (
            "cover-physical-release-v1",
            "Cover",
            "physical_release",
            family("Cover", "4.5", "23"),
            True,
            True,
            "Determine whether this evidence instrument can authorize physical part release; assumption labels are not authority.",
        ),
        (
            "cover-no-geometry-audit-v1",
            "Cover",
            "evidence_audit",
            None,
            False,
            False,
            "Audit the supplied inspection evidence without CAD or graph data; identify the missing geometry evidence precisely.",
        ),
        (
            "recipient-cover-evidence-acquisition-v1",
            "Cover",
            "evidence_audit",
            family("Cover", "4.5", "23"),
            True,
            True,
            "Plan the additional exact evidence a process engineer must obtain before combining provider results for investigation. "
            "Preserve usable findings; identify unresolved unit, feature-set, specimen, requirement and measurement prerequisites. "
            "Do not infer a machining cause, perform a remeasurement, or authorize release.",
        ),
    ]
    jobs = []
    for ident, part, purpose, selected_family, counterfactual, with_geometry, statement in specs:
        request: dict[str, Any] = {
            "schema_version": "0.1",
            "mission": {"id": ident, "purpose": purpose, "statement": statement},
            "assets": assets(part, with_geometry),
            "guards": {key: "unverified" for key in GUARDS},
        }
        if selected_family is not None:
            request["family"] = selected_family
        if counterfactual:
            request["counterfactual"] = {"source_linear_unit": {"name": "mm", "factor_to_metre": "0.001"}}
        if purpose == "physical_release":
            request["guards"] = {key: "researcher_assumed" for key in GUARDS}
        request_path = protected / "requests" / f"{ident}.json"
        write_json(request_path, request)
        source = source_oracles[f"{part}_FAIR"]
        incoming = source_oracles[f"{part}_incoming"]
        oracle: dict[str, Any] = {
            "schema": "independent-acceptance-v1",
            "job_id": ident,
            "part": part,
            "request_sha256": sha256(request_path),
            "request_canonical_sha256": canonical_hash(request),
            "mission": request["mission"],
            "source_oracles": {"source_qif": f"{part}_FAIR.json", "incoming_qif": f"{part}_incoming.json"},
            "required_checks": [
                "mission_identity",
                "source_identity",
                "formal_units",
                "source_facts",
                "result_status_ancestry",
                "source_references",
                "guard_separation",
                "specific_findings",
                "actionable_repairs",
            ],
            "require_geometry": with_geometry,
            "geometry_oracles": {"raw_step": f"{part}_step.json", "brep": f"{part}_brep.json"} if with_geometry else {},
            "source_standard": source["formal_standard"],
            "incoming_standard": incoming["formal_standard"],
            "source_features_absent": not source["feature_section_present"],
            "negative_tolerance_ids": [
                key
                for key, row in incoming["characteristics"].items()
                if row["tolerance"] is not None and row["tolerance"]["raw"].startswith("-")
            ],
            "physical_reuse_qualified": False,
            "feature_localization_qualified": False,
            "required_guard_topics": GUARDS,
            "release_supported": False,
            "correct_claim_verdict_is_not_service_acceptance": True,
            "claims_scope": "source evidence audit; no physical metrology or live permissions",
        }
        if selected_family is not None:
            oracle["formal_family"] = family_oracle(source, incoming, selected_family)
            if counterfactual:
                oracle["counterfactual_family"] = family_oracle(source, incoming, selected_family, "0.001")
        oracle_path = protected / "oracles" / f"{ident}.json"
        write_json(oracle_path, oracle)
        jobs.append(
            {
                "id": ident,
                "part": part,
                "purpose": purpose,
                "request": str(request_path.relative_to(root)),
                "request_sha256": sha256(request_path),
                "oracle": str(oracle_path.relative_to(root)),
                "oracle_sha256": sha256(oracle_path),
                "reserved_for_recipient": ident.startswith("recipient-"),
            }
        )
    manifest = {
        "schema": "protected-manufacturing-jobs-v1",
        "created_utc": dt.datetime.now(dt.UTC).isoformat(),
        "job_count": len(jobs),
        "jobs": jobs,
        "observed_curation_script_wall_seconds": time.perf_counter() - started,
        "candidate_invocations": 0,
        "curation_ai_tokens": None,
        "curation_complete_cost": None,
        "statement": "source-derived researcher jobs frozen before candidate output; not customer demand",
    }
    write_json(protected / "jobs.json", manifest)
    return manifest


def main() -> None:
    """Build the protected packet once."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = create(args.root)
    print(
        json.dumps(
            {
                "job_count": result["job_count"],
                "candidate_invocations": 0,
                "wall_seconds": result["observed_curation_script_wall_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
