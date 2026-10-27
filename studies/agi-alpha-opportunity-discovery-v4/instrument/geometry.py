# SPDX-License-Identifier: Apache-2.0
"""Actual CAD geometry candidates, with a deliberately narrow unit/frame profile."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import re

import cadquery as cq
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.Interface import Interface_Static

from .qif_reader import EvidenceError, QIF, decimal, digest


def bridge(path: Path, incoming: QIF, policy: dict[str, Any]) -> dict[str, Any]:
    """Import an actual solid and generate source-bound cylinder candidates."""
    raw = path.read_text(encoding="utf-8", errors="strict")
    statements = dict(re.findall(r"#(\d+)\s*=\s*(.*?);", raw, re.S))
    context_unit_ids = []
    for statement in statements.values():
        for context in re.findall(r"GLOBAL_UNIT_ASSIGNED_CONTEXT\s*\(\s*\((.*?)\)\s*\)", statement, re.S):
            context_unit_ids.extend(re.findall(r"#(\d+)", context))
    length_statements = [
        statements[i]
        for i in context_unit_ids
        if i in statements and "LENGTH_UNIT()" in re.sub(r"\s+", "", statements[i])
    ]
    # This check identifies supported units only. It does not parse CAD geometry.
    if not length_statements or any("SI_UNIT(.MILLI.,.METRE.)" not in re.sub(r"\s+", "", x) for x in length_statements):
        raise EvidenceError("CAD bridge supports only explicit millimeter STEP length contexts")
    shape = cq.importers.importStep(str(path)).val()
    kernel_unit = Interface_Static.CVal_s("xstep.cascade.unit")
    if kernel_unit != policy["geometry_kernel_length_unit"]:
        raise EvidenceError(f"Unexpected geometry-kernel length unit {kernel_unit!r}")
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise EvidenceError("CAD bridge currently requires one valid solid")
    faces = shape.Faces()
    cylinders = []
    for index, face in enumerate(faces):
        surface = BRepAdaptor_Surface(face.wrapped)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis()
        bounds = face.BoundingBox()
        cylinders.append(
            {
                "face_index": index,
                "radius_mm": cylinder.Radius(),
                "axis_location_mm": list(axis.Location().Coord()),
                "axis_direction": list(axis.Direction().Coord()),
                "area_mm2": face.Area(),
                "bounds_mm": [bounds.xmin, bounds.xmax, bounds.ymin, bounds.ymax, bounds.zmin, bounds.zmax],
            }
        )
    correspondences = []
    for feature in incoming.features.values():
        if not feature["supported_geometry"]:
            continue
        if not feature["axis_point"] or not feature["direction"] or not feature["diameter"]:
            continue
        point = np.asarray([float(decimal(v) * 1000) for v in feature["axis_point"]["si"]])
        direction = np.asarray([float(decimal(v)) for v in feature["direction"]])
        if direction.shape != (3,) or np.linalg.norm(direction) == 0:
            raise EvidenceError("Cylinder has invalid direction")
        direction = direction / np.linalg.norm(direction)
        radius = float(decimal(feature["diameter"]["si"]) * 500)
        candidates = []
        for cylinder in cylinders:
            axis = np.asarray(cylinder["axis_direction"])
            distance = float(np.linalg.norm(np.cross(point - np.asarray(cylinder["axis_location_mm"]), axis)))
            orientation = max(0.0, float(1 - abs(direction @ axis)))
            radius_error = abs(radius - cylinder["radius_mm"])
            if (
                distance <= policy["axis_distance_tolerance_mm"]
                and orientation <= policy["direction_residual_tolerance"]
                and radius_error <= policy["radius_tolerance_mm"]
            ):
                candidates.append(
                    {
                        "face_index": cylinder["face_index"],
                        "axis_distance_mm": distance,
                        "direction_residual": orientation,
                        "radius_residual_mm": radius_error,
                    }
                )
        correspondences.append(
            {
                "feature_item_id": feature["id"],
                "feature_nominal_id": feature["nominal_id"],
                "status": "geometric_candidates" if candidates else "no_candidate_in_declared_frame",
                "candidates": candidates,
                "refs": feature["refs"],
            }
        )
    box = shape.BoundingBox()
    return {
        "status": "executed",
        "asset": "cad_step",
        "sha256": digest(path),
        "kernel_unit": kernel_unit,
        "valid": True,
        "solids": 1,
        "faces": len(faces),
        "edges": len(shape.Edges()),
        "bounds_mm": [box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax],
        "surface_counts": dict(Counter(x.geomType() for x in faces)),
        "cylinders": cylinders,
        "correspondences": correspondences,
        "tolerances": {k: v for k, v in policy.items() if "tolerance" in k},
        "assumptions": [
            "QIF nominal points and STEP refer to the same declared coordinate frame",
            "Matching axis/radius is a candidate correspondence, not complete feature or revision identity",
        ],
        "not_established": ["CAD revision authority", "cross-provider specimen identity", "physical part conformity"],
    }


def traces(incoming: QIF, geometry: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate one reproducible observed trace per characteristic/feature pair."""
    mapping = {x["feature_item_id"]: x for x in geometry.get("correspondences", [])}
    output = []
    seen = set()
    for characteristic in incoming.characteristics.values():
        if not characteristic["supported_predicate"]:
            continue
        for actual in characteristic["actuals"]:
            for feature_actual_id in actual["feature_actual_ids"]:
                feature_actual = incoming.feature_actuals.get(feature_actual_id)
                if not feature_actual:
                    continue
                feature_id = feature_actual["item_id"]
                pair = (characteristic["id"], feature_id)
                if pair in seen:
                    continue
                seen.add(pair)
                feature = incoming.features[feature_id]
                value = actual["value"]
                interval = characteristic["interval"]
                within = (
                    None
                    if value is None
                    else decimal(interval["low_si"]) <= decimal(value["si"]) <= decimal(interval["high_si"])
                )
                output.append(
                    {
                        "characteristic_id": characteristic["id"],
                        "nominal_id": characteristic["nominal_id"],
                        "definition_id": characteristic["definition_id"],
                        "requirement_interval": interval,
                        "actual_id": actual["id"],
                        "actual_value": value,
                        "recorded_status": actual["status"],
                        "numeric_interval_satisfied": within,
                        "feature_actual_id": feature_actual_id,
                        "feature_actual_diameter": feature_actual["diameter"],
                        "feature_item_id": feature_id,
                        "feature_nominal_id": feature["nominal_id"],
                        "feature_definition_id": feature["definition_id"],
                        "geometry": mapping.get(feature_id, {"status": "not_available", "candidates": []}),
                        "measurement_result": incoming.results[actual["result_id"]],
                        "refs": characteristic["refs"] + [actual["ref"], feature_actual["ref"]] + feature["refs"],
                        "physical_release": False,
                    }
                )
                if len(output) >= policy["max_geometry_traces"]:
                    return output
    return output
