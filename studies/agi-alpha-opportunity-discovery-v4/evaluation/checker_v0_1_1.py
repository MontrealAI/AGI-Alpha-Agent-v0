# SPDX-License-Identifier: Apache-2.0
"""Independent report checker for the frozen manufacturing experiment.

Does not import any instrument implementation. A passing receipt accepts only
the scoped evidence-audit service, never physical reuse or part release.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import xml.etree.ElementTree as ET
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.parsers import expat

from source_oracle import canonical_hash, family_oracle, path_text, read_qif, sha256

VERSION = "independent-manufacturing-checker-0.1.1-prospective"
UNIT_SCHEMA_SHA = "2d46993e49300841e66fc05c35dafbcb63ac8085e9c9c8cbc8670e97c13a5fbd"


def walk(value: Any) -> Any:
    """Visit every nested object; no candidate helper code is used."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def reference_locations(path: Path) -> set[tuple[str | None, int, str]]:
    """Resolve exact tag/line/nearest-ID triples independently with Expat."""
    parser = expat.ParserCreate()
    stack: list[str | None] = []
    result: set[tuple[str | None, int, str]] = set()

    def start(name: str, attrs: dict[str, str]) -> None:
        ident = attrs.get("id", stack[-1] if stack else None)
        stack.append(ident)
        result.add((ident, parser.CurrentLineNumber, name.rsplit(":", 1)[-1]))

    def end(name: str) -> None:
        del name
        stack.pop()

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(path.read_bytes(), True)
    return result


def same_number(left: Any, right: Any) -> bool:
    """Compare finite exact numeric values without float rounding."""
    if left is None or right is None:
        return left is right
    try:
        a, b = Decimal(str(left)), Decimal(str(right))
        return a.is_finite() and b.is_finite() and a == b
    except Exception:
        return False


class AuditCheck:
    """Collect substantive checks with compact failure evidence."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.failed_counts: Counter[str] = Counter()
        self.failures: list[dict[str, str]] = []

    def check(self, category: str, condition: bool, detail: str) -> None:
        self.counts[category] += 1
        if not condition:
            self.failed_counts[category] += 1
            if len(self.failures) < 100:
                self.failures.append({"category": category, "detail": detail})

    def quantity(self, actual: Any, expected: Any, detail: str, required: bool) -> None:
        if actual is None:
            self.check("quantities", not required, detail + ": required quantity missing")
            return
        self.check(
            "quantities", expected is not None and actual.get("raw") == expected.get("raw"), detail + ": raw literal"
        )
        self.check(
            "quantities", expected is not None and same_number(actual.get("si"), expected.get("si")), detail + ": SI"
        )
        if expected is not None and isinstance(expected.get("unit"), dict):
            self.check(
                "quantities",
                same_number(actual.get("factor_to_metre"), expected["unit"]["factor_to_metre"]),
                detail + ": unit factor",
            )


def _check_facts(check: AuditCheck, report: dict[str, Any], sources: dict[str, dict[str, Any]]) -> None:
    for asset, source in sources.items():
        doc = report["facts"][asset]
        check.check("source_identity", doc.get("sha256") == source["source_sha256"], asset + ": fact digest")
        check.check("formal_units", doc.get("counterfactual") is False, asset + ": raw facts replaced by hypothesis")
        unit = doc["primary_linear_unit"]
        check.check(
            "formal_units", same_number(unit["factor_to_metre"], source["primary_unit"]["factor_to_metre"]), asset
        )
        standards = [x for row in doc["formal_standard_literals"] for x in row["literals"]]
        check.check("semantics", source["formal_standard"] in standards, asset + ": standard declaration")
        rows = {x["id"]: x for x in doc["characteristics"]}
        check.check(
            "completeness",
            len(rows) == len(doc["characteristics"]) and set(rows) == set(source["characteristics"]),
            asset + ": characteristic coverage",
        )
        actual_seen: list[str] = []
        for cid, expected in source["characteristics"].items():
            if cid not in rows:
                continue
            row = rows[cid]
            prefix = asset + "/" + cid
            for key in ["name", "nominal_id", "definition_id"]:
                check.check("source_facts", row.get(key) == expected[key], prefix + ": " + key)
            check.check(
                "source_facts", row.get("kind") == expected["tag"].removesuffix("CharacteristicItem"), prefix + ": type"
            )
            diameter = expected["tag"] == "DiameterCharacteristicItem"
            check.check("semantics", row.get("supported_predicate") is diameter, prefix + ": supported type")
            check.quantity(row.get("target"), expected["target"], prefix + ": target", diameter)
            check.check(
                "source_facts",
                row.get("raw_target_literal") == (expected["target"] or {}).get("raw"),
                prefix + ": preserved raw nominal",
            )
            for reported, oracle_key in [
                ("material_condition_literal", "material_condition"),
                ("datum_reference_frame_id", "datum_reference_frame_id"),
            ]:
                check.check("semantics", row.get(reported) == expected[oracle_key], prefix + ": " + reported)
            raw_tol = None if expected["tolerance"] is None else expected["tolerance"]["raw"]
            check.check("semantics", row.get("tolerance_value_literal") == raw_tol, prefix + ": signed tolerance")
            if diameter and expected["interval_si"] is not None:
                interval = row.get("interval") or {}
                check.check(
                    "quantities",
                    same_number(interval.get("low_si"), expected["interval_si"][0])
                    and same_number(interval.get("high_si"), expected["interval_si"][1]),
                    prefix + ": interval",
                )
            for actual in row["actuals"]:
                aid = actual["id"]
                actual_seen.append(aid)
                exp = source["actuals"].get(aid)
                check.check(
                    "source_facts", exp is not None and exp["item_id"] == cid, prefix + ": actual linkage " + aid
                )
                if exp is None:
                    continue
                check.check(
                    "source_facts",
                    actual.get("raw_value_literal") == (exp["value"] or {}).get("raw"),
                    aid + ": raw actual",
                )
                check.quantity(actual.get("value"), exp["value"], asset + "/" + aid, diameter)
                for key in ["status", "result_id", "feature_actual_ids"]:
                    check.check("status_ancestry", actual.get(key) == exp[key], asset + "/" + aid + ": " + key)
        check.check(
            "completeness",
            len(actual_seen) == len(set(actual_seen)) and set(actual_seen) == set(source["actuals"]),
            asset + ": complete nonduplicated actual records",
        )
        results = {x["id"]: x for x in doc["measurement_results"]}
        check.check("completeness", set(results) == set(source["result_sets"]), asset + ": result-set coverage")
        for rid, expected in source["result_sets"].items():
            row = results.get(rid, {})
            for key, exp_key in [
                ("overall_status", "overall_status"),
                ("component_ids", "components"),
                ("serials", "serials"),
            ]:
                check.check("status_ancestry", row.get(key) == expected[exp_key], asset + "/" + rid + ": " + key)
        if not source["feature_section_present"]:
            check.check("no_fabrication", doc.get("features") == [], asset + ": invented source geometry")


def _check_proofs(check: AuditCheck, request: dict[str, Any], report: dict[str, Any], sources: dict[str, Any]) -> None:
    proofs = report["family_proofs"]
    if "family" in request:
        selected = request["family"]
        matches = [
            p
            for p in proofs
            if p["source_ids"] == selected["source_characteristic_ids"]
            and p["incoming_id"] == selected["incoming_characteristic_id"]
        ]
        bases = {p["basis"] for p in matches}
        needed = {"formal_source_interpretation"}
        if "counterfactual" in request:
            needed.add("researcher_counterfactual")
        check.check("proof_completeness", needed <= bases, "requested formal/counterfactual proof missing")
    for proof in proofs:
        family = {"source_characteristic_ids": proof["source_ids"], "incoming_characteristic_id": proof["incoming_id"]}
        override = None
        if proof["basis"] == "researcher_counterfactual":
            override = proof["counterfactual_primary_unit"]["factor_to_metre"]
            check.check("counterfactual", bool(proof.get("not_proved")), "unit hypothesis missing limitations")
        expected = family_oracle(sources["source_qif"], sources["incoming_qif"], family, override)
        check.check(
            "guard_separation",
            proof.get("physical_reuse_admitted") is False and proof.get("guard_evidence_authenticated") is False,
            "proof admits unauthenticated physical reuse",
        )
        check.check("guard_separation", proof.get("guard_status") == request.get("guards", {}), "guard terms changed")
        if not expected["supported"]:
            check.check(
                "proof_soundness",
                not str(proof.get("status", "")).startswith("proved"),
                "unsupported predicate admitted",
            )
            continue
        interval = proof["destination_interval"]
        check.check(
            "proof_soundness",
            same_number(interval["low_si"], expected["interval_si"][0])
            and same_number(interval["high_si"], expected["interval_si"][1]),
            "destination interval changed",
        )
        check.check(
            "proof_soundness",
            proof["all_observed_values_satisfy_destination"] == expected["all_values_within"],
            "incorrect universal assertion over observed source values",
        )
        seen = {v["actual_id"]: v for v in proof["observed_values"]}
        check.check(
            "proof_completeness",
            len(seen) == len(proof["observed_values"]) == expected["source_value_count"],
            "proof omitted/duplicated observed values",
        )
        for val in expected["values"]:
            observed = seen.get(val["actual_id"], {})
            check.check(
                "proof_soundness",
                observed.get("source_id") == val["item_id"]
                and observed.get("result_id") == val["result_id"]
                and same_number(observed.get("value_si"), val["value_si"]),
                "wrong proof value " + val["actual_id"],
            )
        if not expected["all_values_within"]:
            counter = proof.get("observed_numeric_counterexample") or {}
            exp_counter = next((v for v in expected["values"] if v["actual_id"] == counter.get("actual_id")), None)
            check.check(
                "proof_soundness",
                exp_counter is not None
                and not exp_counter["within"]
                and same_number(counter.get("value_si"), exp_counter["value_si"]),
                "missing/false observed counterexample",
            )
        source_intervals = []
        for sid in proof["source_ids"]:
            source = sources["source_qif"]["characteristics"][sid]
            interval_si = [Decimal(x) for x in source["interval_si"]]
            if override is not None:
                old_factor = Decimal(sources["source_qif"]["primary_unit"]["factor_to_metre"])
                interval_si = [x / old_factor * Decimal(override) for x in interval_si]
            source_intervals.append((sid, *interval_si))
        lo, hi = (Decimal(x) for x in expected["interval_si"])
        subset = all(lo <= a <= b <= hi for _, a, b in source_intervals)
        check.check("proof_soundness", proof.get("all_source_intervals_subset") is subset, "wrong interval implication")
        if not subset:
            counter = proof.get("interval_counterexample") or {}
            source_range = next(((a, b) for sid, a, b in source_intervals if sid == counter.get("source_id")), None)
            value = Decimal(counter.get("constructed_value_si", "NaN"))
            valid = value.is_finite() and source_range is not None and source_range[0] <= value <= source_range[1]
            valid = valid and not lo <= value <= hi
            check.check(
                "proof_soundness",
                valid and counter.get("observed_measurement") is False,
                "constructed interval counterexample invalid or relabeled observed",
            )
        incoming = sources["incoming_qif"]
        target_ids = set(incoming["characteristics"][proof["incoming_id"]]["feature_item_ids"])
        for actual in incoming["actuals"].values():
            if actual["item_id"] == proof["incoming_id"]:
                for actual_feature_id in actual["feature_actual_ids"]:
                    feature_item = incoming["objects"][actual_feature_id]["leaves"].get("FeatureItemId")
                    if feature_item is not None:
                        target_ids.add(feature_item)
        check.check(
            "proof_soundness",
            set(proof.get("target_feature_ids", [])) == target_ids,
            "incorrect target feature set from source associations",
        )
        cardinality = len(target_ids) == len(proof["source_ids"]) and bool(target_ids)
        check.check(
            "proof_soundness", proof.get("family_cardinality_consistent") is cardinality, "family cardinality incorrect"
        )
        if proof.get("permutation_invariance_proved") is True:
            check.check("proof_soundness", cardinality, "bijection certificate despite mismatched cardinality")
        if proof.get("family_all_recorded_values_pass") is True:
            check.check(
                "proof_soundness",
                cardinality and expected["all_values_within"],
                "physical-family record claim overpromoted",
            )
        permutations = proof.get("enumerated_source_permutations", [])
        for permutation in permutations:
            check.check(
                "proof_soundness", sorted(permutation) == sorted(proof["source_ids"]), "invalid enumerated permutation"
            )
        if permutations:
            check.check(
                "proof_soundness", len({tuple(x) for x in permutations}) == len(permutations), "duplicate permutations"
            )
        assignment = proof.get("assignment_counterexample")
        if assignment:
            maps = [assignment.get("mapping_A", {}), assignment.get("mapping_B", {})]
            valid = cardinality and all(
                set(m) == set(target_ids) and sorted(m.values()) == sorted(proof["source_ids"]) for m in maps
            )
            check.check("proof_soundness", valid and maps[0] != maps[1], "invalid assignment counterexample")


def _vector(values: Any) -> list[float]:
    return [float(x) for x in values]


def _axis_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    radius = abs(float(left["radius_mm"]) - float(right["radius"]))
    a, b = _vector(left["axis_direction"]), _vector(right["axis_direction"])
    dot = abs(sum(x * y for x, y in zip(a, b)))
    displacement = [float(x) - float(y) for x, y in zip(left["axis_location_mm"], right["axis_origin"])]
    projection = sum(x * y for x, y in zip(displacement, b))
    distance = math.sqrt(sum((x - projection * y) ** 2 for x, y in zip(displacement, b)))
    return radius <= 1e-8 and 1 - dot <= 1e-10 and distance <= 1e-7


def _check_geometry(
    check: AuditCheck, request: dict[str, Any], report: dict[str, Any], base: Path, oracle: dict[str, Any], odir: Path
) -> None:
    geometry = report["geometry"]
    if "cad_step" not in request["assets"]:
        check.check(
            "geometry",
            geometry.get("correspondences", []) == [] and not geometry.get("cylinders"),
            "invented absent geometry",
        )
        return
    expected = json.loads((odir / oracle["geometry_oracles"]["brep"]).read_text())
    check.check("geometry", geometry.get("status") == "executed", "available CAD was not successfully inspected")
    if geometry.get("status") != "executed":
        return
    for key in ["valid", "faces", "solids"]:
        check.check("geometry", geometry.get(key) == expected[key], "CAD " + key)
    reported = geometry.get("cylinders", [])
    check.check("geometry", len(reported) == len(expected["cylinders"]), "cylinder inventory count")
    for cylinder in reported:
        check.check(
            "geometry", any(_axis_match(cylinder, e) for e in expected["cylinders"]), "unreproduced CAD cylinder"
        )
    by_face = {c["face_index"]: c for c in reported}
    root = ET.parse(base / request["assets"]["incoming_qif"]["path"]).getroot()
    index = {e.attrib["id"]: e for e in root.iter() if "id" in e.attrib}
    matched = 0
    for correspondence in geometry["correspondences"]:
        item = index[correspondence["feature_item_id"]]
        nid = path_text(item, "q:FeatureNominalId")
        nominal = index[str(nid)]
        did = path_text(nominal, "q:FeatureDefinitionId")
        definition = index[str(did)]
        check.check("geometry", correspondence.get("feature_nominal_id") == nid, "wrong feature nominal geometry link")
        diameter = float(path_text(definition, "q:Diameter") or "nan")
        point = [float(x) for x in (path_text(nominal, "q:Axis/q:AxisPoint") or "").split()]
        direction = [float(x) for x in (path_text(nominal, "q:Axis/q:Direction") or "").split()]
        for candidate in correspondence.get("candidates", []):
            face = by_face.get(candidate["face_index"])
            check.check("geometry", face is not None, "unknown candidate face")
            if face is None:
                continue
            expected_axis = {"radius": diameter / 2, "axis_origin": point, "axis_direction": direction}
            check.check(
                "geometry", _axis_match(face, expected_axis), "candidate not consistent with QIF nominal cylinder"
            )
            matched += 1
    check.check("usefulness", matched > 0, "no source-to-CAD candidate trace established")


def _check_traces(check: AuditCheck, report: dict[str, Any], source: dict[str, Any]) -> None:
    seen: set[str] = set()
    for trace in report["traces"]:
        cid, aid = trace["characteristic_id"], trace["actual_id"]
        char = source["characteristics"].get(cid)
        actual = source["actuals"].get(aid)
        check.check(
            "traces",
            char is not None and actual is not None and actual["item_id"] == cid,
            "bad characteristic actual trace",
        )
        if char is None or actual is None:
            continue
        seen.add(cid)
        check.check(
            "traces",
            trace["nominal_id"] == char["nominal_id"] and trace["definition_id"] == char["definition_id"],
            "requirement chain",
        )
        check.quantity(trace["actual_value"], actual["value"], "trace " + aid, True)
        result = source["result_sets"][actual["result_id"]]
        check.check(
            "traces",
            trace["measurement_result"]["id"] == result["id"]
            and trace["measurement_result"]["overall_status"] == result["overall_status"],
            "parent status lost",
        )
        check.check("traces", trace.get("recorded_status") == actual["status"], "recorded local status changed")
        fa = trace["feature_actual_id"]
        check.check("traces", fa in actual["feature_actual_ids"], "wrong actual feature association")
        if fa in source["objects"]:
            item_id = source["objects"][fa]["leaves"].get("FeatureItemId")
            check.check("traces", trace["feature_item_id"] == item_id, "feature item chain")
            if item_id is not None:
                nominal_id = source["objects"][item_id]["leaves"].get("FeatureNominalId")
                definition_id = source["objects"].get(str(nominal_id), {}).get("leaves", {}).get("FeatureDefinitionId")
                check.check(
                    "traces",
                    trace.get("feature_nominal_id") == nominal_id
                    and trace.get("feature_definition_id") == definition_id,
                    "feature definition chain",
                )
        lo, hi = (Decimal(v) for v in char["interval_si"])
        value = Decimal(actual["value"]["si"])
        check.check("traces", trace["numeric_interval_satisfied"] == (lo <= value <= hi), "wrong local numeric status")
        check.check("guard_separation", trace.get("physical_release") is False, "trace promoted to release")
    diameter_ids = {
        key for key, value in source["characteristics"].items() if value["tag"] == "DiameterCharacteristicItem"
    }
    check.check("usefulness", diameter_ids <= seen, "no representative trace for an incoming diameter obligation")


def _check_repair_scope(
    check: AuditCheck, request: dict[str, Any], report: dict[str, Any], sources: dict[str, Any], oracle: dict[str, Any]
) -> None:
    """Resolve the prospectively required repair bindings without inferred correspondence."""
    requirements = oracle.get("prospective_requirements")
    if requirements is None:
        return
    repairs = {item["id"]: item for item in report["repair_requests"]}
    requested = {
        "source_qif": set(requirements["source_characteristic_ids"]),
        "incoming_qif": set(requirements["incoming_characteristic_ids"]),
    }
    for topic in requirements["required_binding_topics"]:
        repair = repairs.get(topic, {})
        affected = repair.get("affected", {})
        check.check(
            "prospective_bindings", isinstance(affected, dict) and bool(affected), topic + ": absent binding object"
        )
        if not isinstance(affected, dict):
            continue
        check.check(
            "prospective_bindings",
            affected.get("correspondence_established") is False,
            topic + ": obligation scope promoted to physical correspondence",
        )
        mission = affected.get("mission", {})
        check.check(
            "prospective_bindings",
            mission.get("id") == request["mission"]["id"]
            and mission.get("purpose") == request["mission"]["purpose"]
            and mission.get("sha256") == canonical_hash(request["mission"]),
            topic + ": stale mission binding",
        )
        documents = affected.get("documents", [])
        by_asset = {document.get("asset"): document for document in documents}
        check.check(
            "prospective_bindings",
            len(by_asset) == len(documents) and set(by_asset) == set(sources),
            topic + ": missing/duplicate source roles",
        )
        for asset, expected_ids in requested.items():
            document = by_asset.get(asset, {})
            source = sources[asset]
            check.check(
                "prospective_bindings",
                document.get("sha256") == source["source_sha256"],
                topic + "/" + asset + ": changed source identity",
            )
            obligations = document.get("characteristic_obligations", [])
            by_id = {obligation.get("characteristic_id"): obligation for obligation in obligations}
            check.check(
                "prospective_bindings",
                len(by_id) == len(obligations) and expected_ids <= set(by_id),
                topic + "/" + asset + ": requested obligations missing or duplicated",
            )
            for cid, obligation in by_id.items():
                expected = source["characteristics"].get(cid)
                check.check("prospective_bindings", expected is not None, topic + ": fabricated obligation " + str(cid))
                if expected is None:
                    continue
                check.check(
                    "prospective_bindings",
                    obligation.get("nominal_id") == expected["nominal_id"]
                    and obligation.get("definition_id") == expected["definition_id"],
                    topic + ": wrong nominal/definition binding",
                )
                actuals = {actual["id"]: actual for actual in source["actuals"].values() if actual["item_id"] == cid}
                records = obligation.get("actuals", [])
                check.check(
                    "prospective_bindings",
                    {row.get("actual_id") for row in records} == set(actuals) and len(records) == len(actuals),
                    topic + ": actual coverage lost",
                )
                for record in records:
                    expected_actual = actuals.get(record.get("actual_id"))
                    check.check(
                        "prospective_bindings",
                        expected_actual is not None
                        and record.get("measurement_result_id") == expected_actual["result_id"],
                        topic + ": wrong measurement-result scope",
                    )
                feature_ids = set(expected["feature_item_ids"])
                for actual in actuals.values():
                    for actual_feature in actual["feature_actual_ids"]:
                        feature_id = source["objects"][actual_feature]["leaves"].get("FeatureItemId")
                        if feature_id is not None:
                            feature_ids.add(feature_id)
                check.check(
                    "prospective_bindings",
                    set(obligation.get("feature_item_ids", [])) == feature_ids,
                    topic + ": unsupported feature linkage",
                )
        check.check(
            "prospective_bindings",
            affected.get("scope") == "all_declared_characteristics",
            topic + ": unspecialized mission incorrectly narrowed",
        )


def evaluate(request_path: Path, report_path: Path, oracle_path: Path) -> dict[str, Any]:
    """Return a full-audit acceptance receipt with reproducible failure details."""
    started = time.perf_counter()
    check = AuditCheck()
    request = json.loads(request_path.read_text())
    report = json.loads(report_path.read_text())
    oracle = json.loads(oracle_path.read_text())
    base, odir = request_path.parent, oracle_path.parent
    check.check("freeze", sha256(request_path) == oracle["request_sha256"], "request changed after curation")
    sources = {asset: read_qif(base / request["assets"][asset]["path"]) for asset in ["source_qif", "incoming_qif"]}
    for asset, entry in request["assets"].items():
        file_path = base / entry["path"]
        actual_hash = sha256(file_path)
        check.check("source_identity", actual_hash == entry["sha256"], asset + ": bytes changed")
        identity = report["identity"]["assets"].get(asset, {})
        check.check(
            "source_identity",
            identity.get("sha256") == actual_hash and identity.get("bytes") == file_path.stat().st_size,
            asset + ": report source binding",
        )
    check.check("mission_identity", report["mission"] == request["mission"], "mission replaced")
    check.check(
        "mission_identity", report["identity"]["mission_hash"] == canonical_hash(request["mission"]), "mission hash"
    )
    semantic_request = dict(request)
    semantic_request["assets"] = {
        role: {"sha256": item["sha256"], "bytes": (base / item["path"]).stat().st_size}
        for role, item in request["assets"].items()
    }
    check.check(
        "mission_identity",
        report["identity"]["request_hash"] == canonical_hash(semantic_request),
        "complete path-independent semantic request hash",
    )
    freeze_path = Path(__file__).resolve().parent.parent / "instrument_v0_1_1" / "freeze.json"
    freeze = json.loads(freeze_path.read_text())
    expected_files = {Path(name).name: value for name, value in freeze["files"].items()}
    check.check(
        "instrument_identity",
        report["identity"]["files"] == expected_files,
        "runtime source closure differs from freeze",
    )
    check.check(
        "instrument_identity",
        report["identity"]["dependencies"] == freeze["dependencies"],
        "dependency closure differs",
    )
    check.check(
        "instrument_identity",
        report["identity"]["generic_identity_sha256"] == freeze["generic_identity_sha256"],
        "generic evaluator/policy/runtime identity differs",
    )
    _check_facts(check, report, sources)
    locations = {asset: reference_locations(base / request["assets"][asset]["path"]) for asset in sources}
    for node in walk(report):
        if {"asset", "sha256", "element_id", "line", "field"} <= set(node):
            asset = node["asset"]
            check.check(
                "references",
                asset in request["assets"] and node["sha256"] == request["assets"].get(asset, {}).get("sha256"),
                "reference source digest",
            )
            if asset in locations:
                check.check(
                    "references",
                    (node["element_id"], node["line"], node["field"]) in locations[asset],
                    f"{asset}/{node['element_id']} line {node['line']} field {node['field']}",
                )
    _check_proofs(check, request, report, sources)
    _check_geometry(check, request, report, base, oracle, odir)
    _check_traces(check, report, sources["incoming_qif"])
    findings = report["findings"]
    kinds = {f["kind"] for f in findings}
    check.check(
        "usefulness",
        "formal_unit_default" in kinds and "standard_identity_requires_requalification" in kinds,
        "missing consequential unit/standard audit findings",
    )
    check.check(
        "usefulness", len(findings) >= 3 and any(f.get("refs") for f in findings), "blanket/non-evidential audit"
    )
    if oracle["negative_tolerance_ids"]:
        check.check("semantics", "negative_tolerance_literal" in kinds, "negative tolerance not flagged")
    for finding in findings:
        if finding["kind"] == "formal_unit_default":
            check.check(
                "formal_units",
                finding["details"].get("schema_sha256") == UNIT_SCHEMA_SHA,
                "wrong formal-unit rule identity",
            )
        if finding["kind"] == "numeric_interval_counterexample":
            details = finding["details"]
            value = Decimal(details["constructed_value_si"])
            left = [Decimal(x) for x in details["source_interval_si"]]
            right = [Decimal(x) for x in details["incoming_interval_si"]]
            check.check(
                "proof_soundness",
                left[0] <= value <= left[1]
                and not right[0] <= value <= right[1]
                and details.get("observed_measurement") is False,
                "incorrect constructed finding",
            )
    repairs = {r["id"]: r for r in report["repair_requests"]}
    required = set(oracle["required_guard_topics"]) | {"source_unit_intent"}
    check.check("usefulness", required <= set(repairs), "missing exact evidence-acquisition topics")
    for repair in repairs.values():
        check.check(
            "repairs",
            repair["mission_id"] == request["mission"]["id"]
            and bool(repair["required_evidence"])
            and bool(repair["reason"])
            and bool(repair["affected"]),
            "unbound/non-actionable repair request",
        )
    _check_repair_scope(check, request, report, sources, oracle)
    mission = report["mission_result"]
    check.check("guard_separation", mission["physical_reuse_admitted"] is False, "physical reuse admitted")
    purpose = request["mission"]["purpose"]
    if purpose == "physical_release":
        check.check("purpose", mission["status"] == "unsupported", "physical-release purpose falsely supported")
    elif purpose == "feature_localization":
        check.check(
            "purpose", mission["status"] in {"blocked", "unsupported"}, "family proof promoted to feature localization"
        )
    elif purpose == "evidence_audit":
        check.check("purpose", mission["status"] == "supported_audit", "requested audit not completed")
    check.check(
        "execution_scope",
        report["execution"].get("network_calls") == 0
        and report["execution"].get("input_mutations") == 0
        and report["execution"].get("development_and_evaluation_cost_included") is False,
        "unsupported execution/cost scope",
    )
    return {
        "schema": VERSION,
        "accepted": not check.failed_counts,
        "job_id": request["mission"]["id"],
        "mission_result": mission,
        "physical_release_accepted": False,
        "request_sha256": sha256(request_path),
        "report_sha256": sha256(report_path),
        "oracle_sha256": sha256(oracle_path),
        "checker_sha256": sha256(Path(__file__)),
        "checks_by_category": dict(check.counts),
        "failed_checks_by_category": dict(check.failed_counts),
        "failures": check.failures,
        "elapsed_seconds": time.perf_counter() - started,
        "complete_cost": None,
        "independence": "standard-library XML/Expat and Decimal; source-derived oracle; direct OCP shared kernel",
        "acceptance_scope": "useful, source-faithful computational evidence audit; no physical or live-authority acceptance",
    }


def main() -> None:
    """CLI expected by the separate recipient integration runner."""
    parser = argparse.ArgumentParser()
    for name in ["request", "report", "oracle", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.request, args.report, args.oracle)
    except Exception as exc:
        result = {
            "schema": VERSION,
            "accepted": False,
            "checker_error": type(exc).__name__ + ": " + str(exc),
            "checker_sha256": sha256(Path(__file__)),
            "physical_release_accepted": False,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "accepted": result["accepted"],
                "checker_error": result.get("checker_error"),
                "failed_checks": result.get("failed_checks_by_category", {}),
            }
        )
    )


if __name__ == "__main__":
    main()
