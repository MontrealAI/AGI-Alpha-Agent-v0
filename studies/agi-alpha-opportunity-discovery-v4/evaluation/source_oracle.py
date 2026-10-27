# SPDX-License-Identifier: Apache-2.0
"""Independent QIF source oracle; never imports the candidate instrument.

Uses the Python standard-library XML parser and Decimal arithmetic. Source
expectations are derived before candidate execution and kept outside its bundle.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.parsers import expat

QIF = "http://qifstandards.org/xsd/qif2"
NS = {"q": QIF}


def sha256(path: Path) -> str:
    """Hash the exact source bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    """Hash canonical JSON using the declared evaluation representation."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def local(tag: str) -> str:
    """Return a namespace-local tag."""
    return tag.rsplit("}", 1)[-1]


def path_text(element: ET.Element, path: str) -> str | None:
    """Resolve an explicit QIF path without guessing a value."""
    found = element.find(path, NS)
    return None if found is None or found.text is None else found.text.strip()


def decimal_text(value: str | Decimal) -> str:
    """Serialize an exact decimal without exponential float coercion."""
    return format(Decimal(value), "f")


def _line_index(raw: bytes) -> dict[str, int]:
    parser = expat.ParserCreate()
    result: dict[str, int] = {}

    def start(name: str, attrs: dict[str, str]) -> None:
        del name
        if "id" in attrs:
            if attrs["id"] in result:
                raise ValueError("duplicate QIF object id")
            result[attrs["id"]] = parser.CurrentLineNumber

    parser.StartElementHandler = start
    parser.Parse(raw, True)
    return result


def read_qif(path: Path) -> dict[str, Any]:
    """Independently resolve raw objects, quantities and result ancestry."""
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("DTD/entity declarations outside evaluator support")
    root = ET.fromstring(raw)
    if root.tag != f"{{{QIF}}}QIFDocument" or root.get("versionQIF") != "2.1.0":
        raise ValueError("oracle supports only the frozen QIF 2.1 namespace/version")
    lines = _line_index(raw)
    index = {e.attrib["id"]: e for e in root.iter() if "id" in e.attrib}
    units: dict[str, dict[str, str]] = {}
    for unit in root.findall("./q:FileUnits//q:LinearUnit", NS):
        name = path_text(unit, "q:UnitName")
        si = path_text(unit, "q:SIUnitName")
        factor = path_text(unit, "q:UnitConversion/q:Factor") or "1"
        offset = path_text(unit, "q:UnitConversion/q:Offset") or "0"
        if name is None or si != "meter" or Decimal(offset) != 0 or Decimal(factor) <= 0:
            raise ValueError("unsupported linear-unit declaration")
        units[name] = {"name": name, "factor_to_metre": factor, "basis": "declared_file_unit"}
    primary = root.find("./q:FileUnits/q:PrimaryUnits/q:LinearUnit", NS)
    if primary is None:
        primary_unit = {"name": "meter", "factor_to_metre": "1", "basis": "QIF_2_1_default_metre"}
    else:
        primary_name = path_text(primary, "q:UnitName")
        if primary_name is None or primary_name not in units:
            raise ValueError("primary unit cannot be resolved")
        primary_unit = units[primary_name]

    def quantity(element: ET.Element | None) -> dict[str, Any] | None:
        if element is None or element.text is None:
            return None
        literal = element.text.strip()
        override = element.get("linearUnit")
        resolved = primary_unit if override is None else units.get(override)
        if resolved is None:
            return {"raw": literal, "si": None, "unit": override, "error": "unresolved_explicit_unit"}
        try:
            number = Decimal(literal)
            if not number.is_finite():
                raise ValueError("nonfinite source value")
            si_value = number * Decimal(resolved["factor_to_metre"])
        except InvalidOperation as exc:
            raise ValueError("invalid decimal") from exc
        return {"raw": literal, "si": decimal_text(si_value), "unit": dict(resolved), "override": override}

    characteristics: dict[str, dict[str, Any]] = {}
    for item in root.findall("./q:Characteristics/q:CharacteristicItems/*", NS):
        iid = item.attrib["id"]
        nid = path_text(item, "q:CharacteristicNominalId")
        if nid is None or nid not in index:
            raise ValueError("missing nominal reference")
        nominal = index[nid]
        did = path_text(nominal, "q:CharacteristicDefinitionId")
        if did is None or did not in index:
            raise ValueError("missing definition reference")
        definition = index[did]
        target = quantity(nominal.find("q:TargetValue", NS))
        minimum = quantity(definition.find("q:Tolerance/q:MinValue", NS))
        maximum = quantity(definition.find("q:Tolerance/q:MaxValue", NS))
        limit = path_text(definition, "q:Tolerance/q:DefinedAsLimit")
        interval: list[str] | None = None
        if minimum is not None and maximum is not None and minimum["si"] is not None and maximum["si"] is not None:
            if limit in {"true", "1"}:
                interval = [minimum["si"], maximum["si"]]
            elif limit in {"false", "0"} and target is not None and target["si"] is not None:
                interval = [decimal_text(Decimal(target["si"]) + Decimal(v["si"])) for v in [minimum, maximum]]
        characteristics[iid] = {
            "id": iid,
            "tag": local(item.tag),
            "name": path_text(item, "q:Name") or "",
            "nominal_id": nid,
            "definition_id": did,
            "target": target,
            "minimum": minimum,
            "maximum": maximum,
            "defined_as_limit": limit,
            "interval_si": interval,
            "tolerance": quantity(definition.find("q:ToleranceValue", NS)),
            "material_condition": path_text(definition, "q:MaterialCondition"),
            "datum_reference_frame_id": path_text(definition, "q:DatumReferenceFrameId"),
            "feature_item_ids": [x.text.strip() for x in item.findall("q:FeatureItemIds/q:Id", NS) if x.text],
            "line": lines[iid],
            "nominal_line": lines[nid],
            "definition_line": lines[did],
        }

    actuals: dict[str, dict[str, Any]] = {}
    result_sets: dict[str, dict[str, Any]] = {}
    for result in root.findall("./q:MeasurementsResults/q:MeasurementResultsSet/q:MeasurementResults", NS):
        rid = result.attrib["id"]
        components = [x.text.strip() for x in result.findall("q:ActualComponentIds/q:Id", NS) if x.text]
        overall = path_text(result, "q:InspectionStatus/q:InspectionStatusEnum")
        serials = [path_text(index[c], "q:SerialNumber") for c in components if c in index]
        result_sets[rid] = {"id": rid, "overall_status": overall, "components": components, "serials": serials}
        for actual in result.findall("./q:MeasuredCharacteristics/q:CharacteristicActuals/*", NS):
            aid = actual.attrib["id"]
            actuals[aid] = {
                "id": aid,
                "tag": local(actual.tag),
                "item_id": path_text(actual, "q:CharacteristicItemId"),
                "value": quantity(actual.find("q:Value", NS)),
                "status": path_text(actual, "q:Status/q:CharacteristicStatusEnum"),
                "result_id": rid,
                "overall_status": overall,
                "component_ids": components,
                "serials": serials,
                "feature_actual_ids": [x.text.strip() for x in actual.findall("q:FeatureActualIds/q:Id", NS) if x.text],
                "line": lines[aid],
            }

    objects: dict[str, dict[str, Any]] = {}
    for ident, element in index.items():
        objects[ident] = {
            "tag": local(element.tag),
            "line": lines[ident],
            "leaves": {local(child.tag): child.text.strip() for child in element if len(child) == 0 and child.text},
            "references": {
                local(child.tag): [x.text.strip() for x in child if x.text]
                for child in element
                if local(child.tag).endswith("Ids")
            },
        }
    return {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "qif_version": root.get("versionQIF"),
        "primary_unit": primary_unit,
        "formal_standard": path_text(root, "./q:Characteristics/q:FormalStandard/q:FormalStandardEnum"),
        "feature_section_present": root.find("./q:Features", NS) is not None,
        "characteristics": characteristics,
        "actuals": actuals,
        "result_sets": result_sets,
        "objects": objects,
        "overall_status_counts": dict(Counter(x["overall_status"] for x in result_sets.values())),
        "explicit_linear_unit_overrides": sum("linearUnit" in e.attrib for e in root.iter()),
    }


def family_oracle(
    source: dict[str, Any], incoming: dict[str, Any], family: dict[str, Any], override_factor: str | None = None
) -> dict[str, Any]:
    """Check a finite family claim independently of names/physical identity.

    A universal assertion that all selected recorded values satisfy one common
    interval is permutation invariant by conjunction commutativity. Small
    families are also exhaustively permuted as a separate numerical check.
    This proves neither feature-set coverage nor specimen correspondence.
    """
    selected = family["source_characteristic_ids"]
    if len(selected) != len(set(selected)) or not selected:
        raise ValueError("family must contain distinct source item ids")
    target_id = family["incoming_characteristic_id"]
    target = incoming["characteristics"][target_id]
    bounds = target["interval_si"]
    valid_kinds = target["tag"] == "DiameterCharacteristicItem" and all(
        source["characteristics"][s]["tag"] == "DiameterCharacteristicItem" for s in selected
    )
    if not valid_kinds or bounds is None:
        return {"supported": False, "reason": "unsupported_predicate_or_interval"}
    lo, hi = (Decimal(x) for x in bounds)
    if lo > hi:
        return {"supported": False, "reason": "reversed_interval"}
    records = [a for a in source["actuals"].values() if a["item_id"] in selected]
    values: list[dict[str, Any]] = []
    for actual in records:
        value = actual["value"]
        if value is None or value["si"] is None:
            return {"supported": False, "reason": "unresolved_actual_quantity"}
        val = Decimal(value["si"]) if override_factor is None else Decimal(value["raw"]) * Decimal(override_factor)
        values.append(
            {
                "actual_id": actual["id"],
                "item_id": actual["item_id"],
                "result_id": actual["result_id"],
                "value_si": decimal_text(val),
                "within": lo <= val <= hi,
                "overall_status": actual["overall_status"],
                "characteristic_status": actual["status"],
            }
        )
    if not values or any(not any(v["item_id"] == s for v in values) for s in selected):
        return {"supported": False, "reason": "missing_family_measurements"}
    all_within = all(v["within"] for v in values)
    permutations_checked = 0
    if len(selected) <= 8:
        for perm in itertools.permutations(selected):
            verdict = all(v["within"] for s in perm for v in values if v["item_id"] == s)
            if verdict != all_within:
                raise AssertionError("common-interval conjunction lost permutation invariance")
            permutations_checked += 1
    numbers = [Decimal(v["value_si"]) for v in values]
    return {
        "supported": True,
        "source_characteristic_ids": selected,
        "incoming_characteristic_id": target_id,
        "basis": "formal_QIF_units" if override_factor is None else "researcher_unit_counterfactual",
        "interval_si": bounds,
        "source_value_count": len(values),
        "minimum_si": decimal_text(min(numbers)),
        "maximum_si": decimal_text(max(numbers)),
        "all_values_within": all_within,
        "permutation_invariant": True,
        "permutations_checked": permutations_checked,
        "admissible_permutations_count": str(math.factorial(len(selected))),
        "invariance_proof": "universal conjunction under one common interval; finite family only",
        "counterexample": next((v for v in values if not v["within"]), None),
        "values": values,
        "physical_reuse_qualified": False,
        "feature_localization_qualified": False,
    }


def inspect_step(path: Path) -> dict[str, Any]:
    """Resolve raw STEP cylinder placements without using the candidate reader."""
    text = path.read_text(errors="strict")
    statements = {m.group(1): m.group(2).strip() for m in re.finditer(r"#(\d+)\s*=\s*(.*?);", text, re.S)}
    cylinders: list[dict[str, Any]] = []
    for ident, statement in statements.items():
        match = re.fullmatch(r"CYLINDRICAL_SURFACE\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*,\s*([^,)]+)\s*\)", statement)
        if match:
            placement_id, radius = match.groups()
            cylinders.append(
                {
                    "entity_id": ident,
                    "radius_raw": radius.strip(),
                    "placement_id": placement_id,
                    "placement_statement": statements[placement_id],
                }
            )
    return {
        "source_sha256": sha256(path),
        "entity_count": len(statements),
        "cylinder_surface_count": len(cylinders),
        "cylinders": cylinders,
    }


def inspect_brep(path: Path) -> dict[str, Any]:
    """Reimport via direct OCP, separately from the instrument's CAD wrapper.

    The underlying geometry kernel is shared infrastructure, not independent
    physical ground truth. Raw STEP inspection supplies a second source check.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise ValueError("independent STEP import failed")
    reader.TransferRoots()
    shape = reader.OneShape()
    surface_counts: Counter[str] = Counter()
    cylinders: list[dict[str, Any]] = []
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    face_count = 0
    while faces.More():
        face_count += 1
        surface = BRepAdaptor_Surface(TopoDS.Face_s(faces.Current()), True)
        surface_counts[str(surface.GetType())] += 1
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            origin = cylinder.Axis().Location()
            direction = cylinder.Axis().Direction()
            cylinders.append(
                {
                    "face_ordinal": face_count,
                    "radius": cylinder.Radius(),
                    "axis_origin": [origin.X(), origin.Y(), origin.Z()],
                    "axis_direction": [direction.X(), direction.Y(), direction.Z()],
                }
            )
        faces.Next()

    def count(kind: Any) -> int:
        explorer = TopExp_Explorer(shape, kind)
        total = 0
        while explorer.More():
            total += 1
            explorer.Next()
        return total

    return {
        "source_sha256": sha256(path),
        "valid": BRepCheck_Analyzer(shape).IsValid(),
        "faces": face_count,
        "edges_with_topological_occurrence_duplicates": count(TopAbs_EDGE),
        "solids": count(TopAbs_SOLID),
        "surface_counts": dict(surface_counts),
        "cylinders": cylinders,
        "independence_limit": "direct OCP reimport; same OpenCascade kernel as candidate infrastructure",
    }
