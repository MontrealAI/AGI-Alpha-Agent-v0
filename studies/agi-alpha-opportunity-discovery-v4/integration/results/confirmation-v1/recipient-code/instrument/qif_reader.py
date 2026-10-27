# SPDX-License-Identifier: Apache-2.0
"""Read a deliberately bounded QIF 2.1 evidence model without repairing source semantics."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
import hashlib

from lxml import etree

NS = {"q": "http://qifstandards.org/xsd/qif2"}
LINEAR_KINDS = {"Diameter", "Radius", "Length", "Width", "DistanceBetween"}


class EvidenceError(ValueError):
    """An input cannot be interpreted within the declared evidence contract."""


def decimal(value: Any) -> Decimal:
    """Require a finite decimal literal."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise EvidenceError(f"Invalid decimal literal: {value!r}") from error
    if not result.is_finite():
        raise EvidenceError("Non-finite numeric evidence is unsupported")
    return result


def text(node: Any, path: str, default: Any = None) -> Any:
    """Read exact text at a QIF-relative path."""
    return node.findtext(path, default=default, namespaces=NS)


def local(node: Any) -> str:
    """Return an XML local name."""
    return etree.QName(node).localname


def digest(path: Path) -> str:
    """Hash exact input bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class QIF:
    """Keep typed records and their raw XML identity together for one source."""

    def __init__(self, path: Path, role: str, override: dict[str, str] | None = None) -> None:
        self.path, self.role, self.sha256 = path, role, digest(path)
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
        self.tree = etree.parse(str(path), parser)
        root = self.tree.getroot()
        if self.tree.docinfo.doctype:
            raise EvidenceError("DOCTYPE is outside the supported QIF evidence profile")
        if root.tag != "{" + NS["q"] + "}QIFDocument" or root.get("versionQIF") != "2.1.0":
            raise EvidenceError("Only QIF namespace qif2 and exact versionQIF=2.1.0 are supported")
        self.ids: dict[str, Any] = {}
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            identifier = node.get("id")
            if identifier:
                if identifier in self.ids:
                    raise EvidenceError(f"Duplicate QIF id {identifier}")
                self.ids[identifier] = node
        self.override = override
        self.primary = {"name": "meter", "factor_to_metre": "1", "basis": "QIF_2.1_SI_default"}
        self.units: dict[str, dict[str, str]] = {"meter": self.primary}
        explicit = root.find("q:FileUnits/q:PrimaryUnits/q:LinearUnit", NS)
        for unit in root.findall(".//q:FileUnits//q:LinearUnit", NS):
            unit_name = text(unit, "q:UnitName")
            factor = text(unit, "q:UnitConversion/q:Factor")
            offset = text(unit, "q:UnitConversion/q:Offset", "0")
            if not unit_name or decimal(offset) != 0:
                raise EvidenceError("Unnamed or nonzero-offset linear unit is unsupported")
            if factor is None:
                if unit_name not in {"meter", "metre", "m"}:
                    raise EvidenceError("A non-SI linear unit requires an explicit conversion factor")
                factor = "1"
            if decimal(factor) <= 0:
                raise EvidenceError("Linear conversion factor must be positive")
            record = {"name": unit_name, "factor_to_metre": str(decimal(factor)), "basis": "explicit_file_unit"}
            if unit_name in self.units and self.units[unit_name]["factor_to_metre"] != record["factor_to_metre"]:
                raise EvidenceError("Ambiguous repeated unit name")
            self.units[unit_name] = record
            if unit is explicit:
                self.primary = record
        if override is not None:
            factor = decimal(override["factor_to_metre"])
            if factor <= 0:
                raise EvidenceError("Counterfactual conversion must be positive")
            self.primary = {
                "name": override["name"],
                "factor_to_metre": str(factor),
                "basis": "researcher_counterfactual_primary_unit",
            }
            # Explicit per-value units retain their original declarations.
        self.characteristics: dict[str, dict[str, Any]] = {}
        self.features: dict[str, dict[str, Any]] = {}
        self.feature_actuals: dict[str, dict[str, Any]] = {}
        self.results: dict[str, dict[str, Any]] = {}
        self._read_features()
        self._read_characteristics()

    def ref(self, node: Any, field: str | None = None) -> dict[str, Any]:
        """Produce a byte-bound, inspectable source reference."""
        parent = node
        while parent is not None and not parent.get("id"):
            parent = parent.getparent()
        return {
            "asset": self.role,
            "sha256": self.sha256,
            "element_id": None if parent is None else parent.get("id"),
            "line": node.sourceline,
            "field": field or local(node),
        }

    def resolve(self, identifier: str | None, expected: str | None = None) -> Any:
        """Resolve an actual typed reference; missing references fail closed."""
        if identifier not in self.ids:
            raise EvidenceError(f"Missing referenced QIF id {identifier}")
        node = self.ids[identifier]
        if expected and not local(node).endswith(expected):
            raise EvidenceError(f"QIF reference {identifier} has unexpected type {local(node)}")
        return node

    def quantity(self, node: Any | None) -> dict[str, Any] | None:
        """Read a linear scalar using exact source/default/per-value units."""
        if node is None:
            return None
        value = decimal(node.text)
        specific = node.get("linearUnit")
        unit = self.primary if specific is None else self.units.get(specific)
        if unit is None:
            raise EvidenceError(f"Undeclared per-value linear unit {specific!r}")
        return {
            "raw": node.text,
            "unit_name": unit["name"],
            "factor_to_metre": unit["factor_to_metre"],
            "si": str(value * decimal(unit["factor_to_metre"])),
            "basis": unit["basis"],
            "ref": self.ref(node),
        }

    def vector(self, node: Any | None) -> dict[str, Any] | None:
        """Read a linear three-vector; direction vectors are handled separately."""
        if node is None:
            return None
        values = (node.text or "").split()
        if len(values) != 3:
            raise EvidenceError("A supported feature point needs three coordinates")
        specific = node.get("linearUnit")
        unit = self.primary if specific is None else self.units.get(specific)
        if unit is None:
            raise EvidenceError("Undeclared point unit")
        return {
            "raw": node.text,
            "si": [str(decimal(v) * decimal(unit["factor_to_metre"])) for v in values],
            "basis": unit["basis"],
            "unit_name": unit["name"],
            "ref": self.ref(node),
        }

    def _read_features(self) -> None:
        for item in self.tree.findall("q:Features/q:FeatureItems/*", NS):
            nominal = self.resolve(text(item, "q:FeatureNominalId"), "FeatureNominal")
            definition = self.resolve(text(nominal, "q:FeatureDefinitionId"), "FeatureDefinition")
            kind = local(item).replace("FeatureItem", "")
            supported = kind == "Cylinder"
            direction = text(nominal, "q:Axis/q:Direction") if supported else None
            self.features[item.get("id")] = {
                "id": item.get("id"),
                "kind": kind,
                "name": text(item, "q:FeatureName"),
                "nominal_id": nominal.get("id"),
                "definition_id": definition.get("id"),
                "diameter": self.quantity(definition.find("q:Diameter", NS)) if supported else None,
                "axis_point": self.vector(nominal.find("q:Axis/q:AxisPoint", NS)) if supported else None,
                "direction": [str(decimal(v)) for v in direction.split()] if direction else None,
                "supported_geometry": supported,
                "refs": [self.ref(item), self.ref(nominal), self.ref(definition)],
            }
        for actual in self.tree.findall(".//q:FeatureActuals/*", NS):
            item_id = text(actual, "q:FeatureItemId")
            self.resolve(item_id, "FeatureItem")
            supported = local(actual) == "CylinderFeatureActual"
            self.feature_actuals[actual.get("id")] = {
                "id": actual.get("id"),
                "item_id": item_id,
                "diameter": self.quantity(actual.find("q:Diameter", NS)) if supported else None,
                "ref": self.ref(actual),
            }

    def _read_characteristics(self) -> None:
        for item in self.tree.findall("q:Characteristics/q:CharacteristicItems/*", NS):
            nominal = self.resolve(text(item, "q:CharacteristicNominalId"), "CharacteristicNominal")
            definition = self.resolve(text(nominal, "q:CharacteristicDefinitionId"), "CharacteristicDefinition")
            kind = local(item).replace("CharacteristicItem", "")
            # Do not treat an angular/form predicate as a length interval.
            target = self.quantity(nominal.find("q:TargetValue", NS)) if kind in LINEAR_KINDS else None
            low = self.quantity(definition.find("q:Tolerance/q:MinValue", NS)) if kind in LINEAR_KINDS else None
            high = self.quantity(definition.find("q:Tolerance/q:MaxValue", NS)) if kind in LINEAR_KINDS else None
            limit = text(definition, "q:Tolerance/q:DefinedAsLimit")
            interval = None
            if low and high and limit in {"true", "false", "1", "0"}:
                offset = Decimal(0) if limit in {"true", "1"} else None if target is None else decimal(target["si"])
                if offset is not None:
                    lower, upper = decimal(low["si"]) + offset, decimal(high["si"]) + offset
                    if lower > upper:
                        raise EvidenceError("Reversed encoded tolerance interval")
                    interval = {
                        "low_si": str(lower),
                        "high_si": str(upper),
                        "unit": "meter",
                        "lower_literal": low,
                        "upper_literal": high,
                        "defined_as_limit": limit,
                    }
            features = [node.text for node in item.findall("q:FeatureItemIds/q:Id", NS)]
            for identifier in features:
                self.resolve(identifier, "FeatureItem")
            self.characteristics[item.get("id")] = {
                "id": item.get("id"),
                "name": text(item, "q:Name"),
                "kind": kind,
                "nominal_id": nominal.get("id"),
                "definition_id": definition.get("id"),
                "target": target,
                "interval": interval,
                "features": features,
                "material_condition_literal": text(definition, "q:MaterialCondition"),
                "tolerance_value_literal": text(definition, "q:ToleranceValue"),
                "datum_reference_frame_id": text(definition, "q:DatumReferenceFrameId"),
                "analysis_mode_literal": text(nominal, "q:AnalysisMode"),
                "raw_target_literal": text(nominal, "q:TargetValue"),
                "raw_tolerance_literals": {
                    "min": text(definition, "q:Tolerance/q:MinValue"),
                    "max": text(definition, "q:Tolerance/q:MaxValue"),
                    "defined_as_limit": limit,
                },
                "supported_predicate": kind == "Diameter" and interval is not None,
                "refs": [self.ref(item), self.ref(nominal), self.ref(definition)],
                "actuals": [],
            }
        for result in self.tree.findall(".//q:MeasurementResults", NS):
            identifier = result.get("id")
            component_ids = [x.text for x in result.findall("q:ActualComponentIds/q:Id", NS)]
            serials = [text(self.resolve(c), "q:SerialNumber") for c in component_ids]
            self.results[identifier] = {
                "id": identifier,
                "component_ids": component_ids,
                "serials": serials,
                "overall_status": text(result, "q:InspectionStatus/q:InspectionStatusEnum"),
                "ref": self.ref(result),
            }
            for actual in result.findall("q:MeasuredCharacteristics/q:CharacteristicActuals/*", NS):
                item_id = text(actual, "q:CharacteristicItemId")
                self.resolve(item_id, "CharacteristicItem")
                if item_id not in self.characteristics:
                    raise EvidenceError("Actual references an unsupported characteristic location")
                char = self.characteristics[item_id]
                fa = [x.text for x in actual.findall("q:FeatureActualIds/q:Id", NS)]
                for feature_actual in fa:
                    self.resolve(feature_actual, "FeatureActual")
                value = self.quantity(actual.find("q:Value", NS)) if char["kind"] in LINEAR_KINDS else None
                char["actuals"].append(
                    {
                        "id": actual.get("id"),
                        "value": value,
                        "raw_value_literal": text(actual, "q:Value"),
                        "status": text(actual, "q:Status/q:CharacteristicStatusEnum"),
                        "feature_actual_ids": fa,
                        "result_id": identifier,
                        "ref": self.ref(actual),
                    }
                )

    def public(self) -> dict[str, Any]:
        """Return a serializable source-bound fact model."""
        standards = []
        for element in self.tree.findall(".//q:FormalStandard", NS):
            standards.append({"literals": [x.text for x in element if x.text], "ref": self.ref(element)})
        return {
            "asset": self.role,
            "sha256": self.sha256,
            "version": "2.1.0",
            "primary_linear_unit": self.primary,
            "unit_declarations": self.units,
            "counterfactual": self.override is not None,
            "formal_standard_literals": standards,
            "characteristics": list(self.characteristics.values()),
            "features": list(self.features.values()),
            "feature_actuals": list(self.feature_actuals.values()),
            "measurement_results": list(self.results.values()),
        }
