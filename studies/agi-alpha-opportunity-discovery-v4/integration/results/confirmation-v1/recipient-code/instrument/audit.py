# SPDX-License-Identifier: Apache-2.0
"""Construct a bounded mission-preserving inspection evidence dossier."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import importlib.metadata
import json
import platform
import re
import time

import jsonschema
from lxml import etree

from .geometry import bridge, traces
from .proofs import GUARDS, candidate_families, prove_family
from .qif_reader import EvidenceError, QIF, decimal, digest

HERE = Path(__file__).resolve().parent
RUNTIME_FILES = [
    "__init__.py",
    "audit.py",
    "cli.py",
    "qif_reader.py",
    "geometry.py",
    "proofs.py",
    "policy.json",
    "request.schema.json",
    "report.schema.json",
    "dependencies.json",
    "QIF_2_1_Units.xsd",
]


def canonical_hash(value: Any) -> str:
    """Hash a canonical JSON identity without time or local path dependence."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def runtime_identity() -> dict[str, Any]:
    """Bind the relevant executable, schema, policy and installed dependency versions."""
    expected = json.loads((HERE / "dependencies.json").read_text())
    actual = {name: importlib.metadata.version(name) for name in expected["packages"]}
    if actual != expected["packages"] or platform.python_version() != expected["python"]:
        raise EvidenceError("Runtime dependency versions differ from the qualified dependency identity")
    files = {name: digest(HERE / name) for name in RUNTIME_FILES}
    return {
        "files": files,
        "dependencies": actual,
        "python": platform.python_version(),
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "schema_id": "urn:agi-alpha:inspection-audit:report:0.1",
        "policy_id": "urn:agi-alpha:inspection-audit:policy:0.1",
    }


def audit(request: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Return a source-grounded audit, preserving the exact requested mission purpose."""
    started = time.perf_counter()
    try:
        jsonschema.Draft202012Validator(json.loads((HERE / "request.schema.json").read_text())).validate(request)
    except jsonschema.ValidationError as error:
        raise EvidenceError(f"Invalid request: {error.message}") from error
    policy = json.loads((HERE / "policy.json").read_text())
    if digest(HERE / "QIF_2_1_Units.xsd") != policy["unit_schema_sha256"]:
        raise EvidenceError("Exact source unit schema identity changed")
    identity = runtime_identity()
    identity["generic_identity_sha256"] = canonical_hash(identity)
    paths: dict[str, Path] = {}
    assets: dict[str, Any] = {}
    for role, asset in request["assets"].items():
        path = (base_dir / asset["path"]).resolve()
        if not path.is_file() or digest(path) != asset["sha256"]:
            raise EvidenceError(f"Missing or digest-mismatched asset {role}")
        paths[role] = path
        assets[role] = {"sha256": asset["sha256"], "bytes": path.stat().st_size}
    identity["assets"] = assets
    identity["mission_hash"] = canonical_hash(request["mission"])
    semantic_request = dict(request)
    semantic_request["assets"] = assets
    identity["request_hash"] = canonical_hash(semantic_request)
    identity["complete_identity_sha256"] = canonical_hash(identity)
    source = QIF(paths["source_qif"], "source_qif")
    incoming = QIF(paths["incoming_qif"], "incoming_qif")
    source_cf = None
    if "counterfactual" in request:
        source_cf = QIF(paths["source_qif"], "source_qif", request["counterfactual"]["source_linear_unit"])
    findings: list[dict[str, Any]] = []

    def finding(
        kind: str,
        status: str,
        conclusion: str,
        refs: list[Any],
        details: Any = None,
        basis: str = "derived",
        limits: list[str] | None = None,
    ) -> None:
        findings.append(
            {
                "id": f"F{len(findings) + 1:03d}",
                "kind": kind,
                "status": status,
                "evidence_basis": basis,
                "conclusion": conclusion,
                "refs": refs,
                "details": details,
                "limitations": limits or [],
            }
        )

    for document in [source, incoming]:
        if document.primary["basis"] == "QIF_2.1_SI_default":
            finding(
                "formal_unit_default",
                "supported",
                "Absent primary linear declaration formally defaults to meters",
                [],
                {
                    "asset": document.role,
                    "sha256": document.sha256,
                    "primary_linear_unit": document.primary,
                    "per_value_units": [
                        dict(e.attrib)
                        for e in document.tree.iter()
                        if isinstance(e.tag, str) and e.get("linearUnit") is not None
                    ],
                    "schema_sha256": policy["unit_schema_sha256"],
                },
                "observed_source",
            )
        for characteristic in document.characteristics.values():
            value = characteristic["tolerance_value_literal"]
            if value is not None and decimal(value) < 0:
                finding(
                    "negative_tolerance_literal",
                    "unsupported",
                    "Negative tolerance is retained; no sign repair applied",
                    characteristic["refs"],
                    {"literal": value, "characteristic_id": characteristic["id"]},
                    "observed_source",
                    ["No GD&T acceptance relation inferred"],
                )

    def normalize(value: Any) -> str:
        return re.sub(r"\s+", "", value or "").upper()

    pairs = []
    for a in source.characteristics.values():
        for b in incoming.characteristics.values():
            if normalize(a["name"]) != normalize(b["name"]):
                continue
            if a["target"] and b["target"] and decimal(a["target"]["raw"]) != 0:
                ratio = decimal(b["target"]["raw"]) / decimal(a["target"]["raw"])
                pair = {
                    "source_id": a["id"],
                    "incoming_id": b["id"],
                    "label": normalize(a["name"]),
                    "source_nominal": a["target"],
                    "incoming_nominal": b["target"],
                    "required_uniform_scale": str(ratio),
                }
                pairs.append(pair)
                if decimal(a["target"]["si"]) != decimal(b["target"]["si"]) or a["kind"] != b["kind"]:
                    finding(
                        "label_join_conflict",
                        "refuted",
                        "Matching labels do not encode equivalent nominal requirements",
                        a["refs"] + b["refs"],
                        pair,
                        limits=[
                            "Does not identify the intended physical correspondence or prove a manufactured defect"
                        ],
                    )
            for field in ["material_condition_literal", "tolerance_value_literal", "analysis_mode_literal"]:
                if a[field] != b[field]:
                    finding(
                        "literal_semantic_conflict",
                        "conditional",
                        "Source literals differ; semantic requalification required",
                        a["refs"] + b["refs"],
                        {"field": field, "source": a[field], "incoming": b[field]},
                        "observed_source",
                        ["No meaning inferred from NONE, MAXIMUM or a tolerance sign alone"],
                    )
    if len({decimal(x["required_uniform_scale"]) for x in pairs}) > 1:
        refs = [
            r
            for x in pairs
            for c in [source.characteristics[x["source_id"]], incoming.characteristics[x["incoming_id"]]]
            for r in c["refs"]
        ]
        finding(
            "incompatible_uniform_label_scale",
            "refuted",
            "No single unit scale reconciles all same-label nominal pairs",
            refs,
            {"pairs": pairs},
            limits=["Applies to the proposed whole label-join rule, not arbitrary alternative mappings"],
        )
    if [x["literals"] for x in source.public()["formal_standard_literals"]] != [
        x["literals"] for x in incoming.public()["formal_standard_literals"]
    ]:
        finding(
            "standard_identity_requires_requalification",
            "conditional",
            "Standard declarations must be reconciled explicitly",
            [],
            {
                "source": source.public()["formal_standard_literals"],
                "incoming": incoming.public()["formal_standard_literals"],
            },
            "observed_source",
        )

    # Countermodels are conditional candidate comparisons, not new measured observations.
    numeric_source = source_cf or source
    for a in numeric_source.characteristics.values():
        for b in incoming.characteristics.values():
            if a["kind"] != b["kind"] or not a["interval"] or not b["interval"]:
                continue
            low, high = decimal(a["interval"]["low_si"]), decimal(a["interval"]["high_si"])
            dlow, dhigh = decimal(b["interval"]["low_si"]), decimal(b["interval"]["high_si"])
            if max(low, dlow) <= min(high, dhigh) and not dlow <= low <= high <= dhigh:
                witness = low if low < dlow else high
                finding(
                    "numeric_interval_counterexample",
                    "refuted",
                    "This candidate source PASS need not imply receiving PASS",
                    a["refs"] + b["refs"],
                    {
                        "source_id": a["id"],
                        "incoming_id": b["id"],
                        "source_interval_si": [str(low), str(high)],
                        "incoming_interval_si": [str(dlow), str(dhigh)],
                        "constructed_value_si": str(witness),
                        "source_pass": low <= witness <= high,
                        "incoming_pass": dlow <= witness <= dhigh,
                        "observed_measurement": False,
                    },
                    "researcher_counterfactual" if source_cf else "derived",
                    ["Conditional on same-property identity; interval overlap alone does not establish that identity"],
                )
    geometry: dict[str, Any] = {"status": "not_supplied", "correspondences": []}
    if "cad_step" in paths:
        try:
            geometry = bridge(paths["cad_step"], incoming, policy)
        except Exception as error:
            geometry = {
                "status": "unsupported_or_failed",
                "error": f"{type(error).__name__}: {error}",
                "sha256": assets["cad_step"]["sha256"],
                "correspondences": [],
            }
            finding(
                "geometry_not_established",
                "unsupported",
                "No geometric claim admitted after failed/unsupported import",
                [],
                geometry,
            )
    trace_records = traces(incoming, geometry, policy)
    reference = {"status": "not_supplied"}
    if "reference_owl" in paths:
        tree = etree.parse(str(paths["reference_owl"]), etree.XMLParser(resolve_entities=False, no_network=True))
        namespace = "{http://www.nist.gov/QIF_ontology#}"
        identifiers = [x.text for x in tree.findall(".//" + namespace + "_id")]
        reference = {
            "status": "existing_E_reference_loaded",
            "sha256": assets["reference_owl"]["sha256"],
            "qif_id_assertions": len(identifiers),
            "covered_incoming_characteristic_ids": sorted(set(identifiers) & set(incoming.characteristics), key=int),
            "scope": "Existing representation supplied to E; no inference that all cross-file identities are verified",
        }
    families: list[tuple[list[str], str]] = []
    if "family" in request:
        family = request["family"]
        families = [(family["source_characteristic_ids"], family["incoming_characteristic_id"])]
    else:
        families = candidate_families(source_cf or source, incoming)
    proofs = []
    for source_ids, target_id in families:
        proofs.append(prove_family(source, incoming, source_ids, target_id, request.get("guards", {}), policy))
        if source_cf:
            proofs.append(prove_family(source_cf, incoming, source_ids, target_id, request.get("guards", {}), policy))
    repairs = []

    def repair(key: str, evidence: str, reason: str, affected: Any) -> None:
        repairs.append(
            {
                "id": key,
                "required_evidence": evidence,
                "reason": reason,
                "affected": affected,
                "status": "not_established",
                "mission_id": request["mission"]["id"],
            }
        )

    if source.primary != incoming.primary or source_cf:
        repair(
            "source_unit_intent",
            "Authorized unit declaration or corrected, separately hashed export if source units are wrong",
            "Formal defaults cannot be replaced by plausible numeric scale; researcher override is not evidence",
            {"source_sha256": source.sha256, "formal_unit": source.primary, "incoming_unit": incoming.primary},
        )
    repair(
        "feature_set_identity",
        "Source feature geometry or authenticated mapping establishing family identity and completeness",
        "Numerical candidate similarity and a supplied incoming graph do not establish source-family identity",
        families,
    )
    repair(
        "specimen_scope",
        "Traceable source-to-recipient specimen or lot identification and result coverage",
        "Row order or similar serial strings are not sufficient identity",
        [source.sha256, incoming.sha256],
    )
    repair(
        "requirement_requalification",
        "Applicable standard, datum/modifier semantics and approved revision/requirement relation",
        "A different tolerance or literal must not be silently normalized",
        [x["id"] for x in findings if "semantic" in x["kind"]],
    )
    repair(
        "measurement_adequacy",
        "Measurement method, uncertainty and acceptance-rule evidence for the claimed decision",
        "Encoded numeric PASS and nominal geometry do not qualify measurement adequacy",
        [x["incoming_id"] for x in proofs],
    )
    repair(
        "current_authority",
        "Current mission-specific authority and separate acceptance decision from the authorized process",
        "The computational instrument does not authenticate live authority or release parts",
        request["mission"],
    )
    purpose = request["mission"]["purpose"]
    if purpose == "feature_localization":
        repair(
            "individual_feature_identity",
            "Unique source-to-physical-feature correspondence sufficient for the requested localization",
            "A family-wide invariant conclusion cannot locate a particular hole",
            [x.get("assignment_counterexample") for x in proofs],
        )
    if purpose == "evidence_audit":
        material = {
            "label_join_conflict",
            "negative_tolerance_literal",
            "numeric_interval_counterexample",
            "formal_unit_default",
        }
        useful = bool(source.characteristics and incoming.characteristics) and (
            any(x["kind"] in material for x in findings)
            or any(x["geometry"].get("candidates") for x in trace_records)
            or any(x.get("all_observed_values_satisfy_destination") for x in proofs)
        )
        status = "supported_audit" if useful else "blocked"
        reasons = (
            ["Source-grounded audit produced; no physical substitution admitted"]
            if useful
            else ["No concrete supported audit witness; generic missing-evidence statements are insufficient"]
        )
    elif purpose == "physical_release":
        status, reasons = (
            "unsupported",
            ["Physical release is outside this instrument; audit cannot satisfy that different purpose"],
        )
    elif purpose == "feature_localization":
        status, reasons = (
            "blocked",
            ["Individual cross-provider feature identity is not established; family proof is insufficient"],
        )
    elif "family" not in request:
        status, reasons = (
            "blocked",
            [
                "A requested quantified proof needs explicit source IDs and receiving criterion; enumerated candidates are exploratory"
            ],
        )
    elif not proofs:
        status, reasons = "blocked", ["No supported candidate family under the requested interpretation"]
    elif purpose == "recorded_values_all":
        repairs = [r for r in repairs if r["id"] == "source_unit_intent" and source_cf is not None]
        if any(
            p["basis"] == "formal_source_interpretation" and p.get("all_observed_values_satisfy_destination")
            for p in proofs
        ):
            status, reasons = (
                "supported_audit",
                [
                    "All selected recorded numeric values satisfy the explicit receiving interval; no physical identity claim made"
                ],
            )
        elif any(p.get("all_observed_values_satisfy_destination") for p in proofs):
            status, reasons = (
                "conditional",
                [
                    "All selected recorded values satisfy the interval only under the explicit unit-repair counterfactual"
                ],
            )
        else:
            status, reasons = (
                "refuted",
                ["Selected recorded values do not establish the requested common-interval claim"],
            )
    elif any(x.get("family_all_recorded_values_pass") for x in proofs):
        status, reasons = (
            "conditional",
            ["Numeric family result is conditional; identity, units, measurement and authority guards remain"],
        )
    elif any(
        x.get("all_observed_values_satisfy_destination") and not x.get("family_cardinality_consistent") for x in proofs
    ):
        status, reasons = (
            "blocked",
            ["Selected records pass numerically but do not establish complete receiving-feature family coverage"],
        )
    else:
        status, reasons = (
            "refuted",
            ["Supported numeric implication not established or is refuted under supplied formal interpretation"],
        )
    report = {
        "schema_version": "0.1",
        "instrument_version": policy["instrument_version"],
        "identity": identity,
        "mission": request["mission"],
        "mission_result": {"status": status, "reasons": reasons, "physical_reuse_admitted": False},
        "facts": {"source_qif": source.public(), "incoming_qif": incoming.public()},
        "findings": findings,
        "geometry": geometry,
        "traces": trace_records,
        "existing_reference": reference,
        "family_proofs": proofs,
        "repair_requests": repairs,
        "limitations": [
            "No complete QIF schema or GD&T conformance validation",
            "Only Diameter family predicates supported",
            "No new physical observations or customer acceptance",
            "No authenticated authority",
            "No complete-dollar advantage measured",
            "Numeric/geometry evidence is not full feature, specimen or revision identity",
        ],
        "execution": {
            "elapsed_seconds": time.perf_counter() - started,
            "network_calls": 0,
            "input_mutations": 0,
            "development_and_evaluation_cost_included": False,
        },
    }
    jsonschema.Draft202012Validator(json.loads((HERE / "report.schema.json").read_text())).validate(report)
    return report
