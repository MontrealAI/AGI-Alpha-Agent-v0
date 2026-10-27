# SPDX-License-Identifier: Apache-2.0
"""Probe input binding and refusal with tiny synthetic inputs; no fresh specimen."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import io
import json
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, cast

import numpy as np


def load_source(path: Path) -> ModuleType:
    """Load exactly the separately retained reviewed source."""
    spec = importlib.util.spec_from_file_location("microscopy_input_review", path)
    if spec is None or spec.loader is None:
        raise ValueError("source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(source_hash: str) -> dict[str, Any]:
    """Create only a synthetic two-dimensional unit-grid contract."""
    return {
        "schema": "microscopy-moments/v1",
        "mission_id": "independent-input-boundary-probe",
        "source_sha256": source_hash,
        "source_axes": ["y", "x"],
        "spacing": [1, 1],
        "units": ["um", "um"],
        "origin": [0, 0],
        "object_definition": "label_id",
        "coverage": "provided_label_support",
        "map_semantics": "geometric_pushforward",
        "affine": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "target_axes": ["y", "x"],
        "metrics": ["label_count", "native_measure", "mapped_measure", "native_centroid", "mapped_centroid"],
    }


def run(source: Path, out: Path) -> dict[str, Any]:
    """Retain exact reviewed bytes and both observed boundary results."""
    out.mkdir(parents=True, exist_ok=False)
    source_bytes = source.read_bytes()
    frozen = out / "microscopy_transfer.py"
    frozen.write_bytes(source_bytes)
    module = load_source(frozen)
    report: dict[str, Any] = {
        "schema": "microscopy-independent-input-boundary-review/v1",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "input_basis": "Two tiny synthetic arrays; no confirmation specimen accessed.",
        "probes": {},
    }
    with tempfile.TemporaryDirectory(prefix="microscopy-input-review-") as temporary:
        root = Path(temporary)
        labels: np.ndarray[Any, Any] = np.zeros((3, 3), dtype=np.uint16)
        labels[1, 1] = 1
        labels_path, mission_path = root / "labels.npy", root / "mission.json"
        np.save(labels_path, labels)
        source_hash = hashlib.sha256(labels_path.read_bytes()).hexdigest()
        mission_path.write_text(json.dumps(contract(source_hash)))
        original_load = module.np.load
        injection: dict[str, Any] = {"called": False, "input_type": None}

        def mutate_before_numpy_load(*args: Any, **kwargs: Any) -> Any:
            injection["called"] = True
            injection["input_type"] = type(args[0]).__name__
            replacement: np.ndarray[Any, Any] = np.ones((3, 3), dtype=np.uint16)
            np.save(labels_path, replacement)
            return original_load(*args, **kwargs)

        module.np.load = mutate_before_numpy_load
        try:
            outcome = module.run(labels_path, mission_path)
        finally:
            module.np.load = original_load
        report["probes"]["hash_then_mutable_load"] = {
            "injection": "Replace the local path immediately before np.load reads its argument.",
            "injection_observed": injection,
            "original_sha256": source_hash,
            "final_path_sha256": hashlib.sha256(labels_path.read_bytes()).hexdigest(),
            "expected_original_measure": 1,
            "outcome": outcome,
            "passed": injection["called"]
            and outcome.get("status") == "ACCEPT"
            and outcome["objects"][0]["native_measure"] == 1,
        }
        archive = root / "labels.npz"
        np.savez(archive, labels=labels)
        archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
        mission_path.write_text(json.dumps(contract(archive_hash)))
        try:
            outcome = module.run(archive, mission_path)
            report["probes"]["numpy_archive_input"] = {
                "uncaught_exception": False,
                "outcome": outcome,
                "passed": outcome.get("status") in {"REJECT", "HOLD"},
            }
        except Exception as exc:
            report["probes"]["numpy_archive_input"] = {
                "uncaught_exception": True,
                "type": type(exc).__name__,
                "message": str(exc),
                "passed": False,
            }
        empty = root / "empty.npy"
        empty.write_bytes(b"")
        mission_path.write_text(json.dumps(contract(hashlib.sha256(b"").hexdigest())))
        try:
            outcome = module.run(empty, mission_path)
            report["probes"]["empty_input"] = {
                "outcome": outcome, "passed": outcome.get("status") in {"REJECT", "HOLD"}
            }
        except Exception as exc:
            report["probes"]["empty_input"] = {"passed": False, "uncaught_exception": type(exc).__name__}
        np.save(labels_path, labels)
        source_hash = hashlib.sha256(labels_path.read_bytes()).hexdigest()
        changes: dict[str, dict[str, Any]] = {
            "negative_spacing": {"spacing": [1, -1]},
            "zero_spacing": {"spacing": [1, 0]},
            "unknown_units": {"units": ["pixel", "um"]},
            "nan_spacing": {"spacing": [float("nan"), 1]},
            "biological_volume_meaning": {"map_semantics": "true_biological_volume"},
            "complete_cell_claim": {"coverage": "complete_cell"},
            "nonlinear_map": {"affine": [[1, 0, 0], [0, 1, 0], [0.1, 0, 1]]},
            "singular_affine": {"affine": [[1, 0, 0], [0, 0, 0], [0, 0, 1]]},
            "changed_axis_set": {"target_axes": ["z", "x"]},
            "unsupported_topology_metric": {"metrics": ["euler_number"]},
        }
        for name, change in changes.items():
            mission = {**copy.deepcopy(contract(source_hash)), **change}
            mission_path.write_text(json.dumps(mission))
            outcome = module.run(labels_path, mission_path)
            report["probes"][name] = {"outcome": outcome, "passed": outcome.get("status") in {"REJECT", "HOLD"}}
        signed: np.ndarray[Any, Any] = np.zeros((3, 3), dtype=np.int16)
        signed[1, 1] = -7
        np.save(labels_path, signed)
        source_hash = hashlib.sha256(labels_path.read_bytes()).hexdigest()
        mission_path.write_text(json.dumps(contract(source_hash)))
        outcome = module.run(labels_path, mission_path)
        report["probes"]["signed_nonzero_label"] = {
            "outcome": outcome,
            "passed": outcome.get("status") == "ACCEPT" and str(outcome["objects"][0]["label_id"]) == "-7",
        }
        large_ids: np.ndarray[Any, Any] = np.zeros((3, 3), dtype=np.uint64)
        large_ids[1, 1] = 2**53
        np.save(labels_path, large_ids)
        mission_path.write_text(json.dumps(contract(hashlib.sha256(labels_path.read_bytes()).hexdigest())))
        outcome = module.run(labels_path, mission_path)
        report["probes"]["json_unsafe_label_id"] = {"outcome": outcome, "passed": outcome.get("status") == "HOLD"}
        buffer = io.BytesIO()
        write_header = cast(Callable[[io.BytesIO, dict[str, Any]], None], np.lib.format.write_array_header_1_0)
        write_header(buffer, {"shape": (2, 2**30), "fortran_order": False, "descr": "<u2"})
        header = buffer.getvalue()
        labels_path.write_bytes(header)
        mission_path.write_text(json.dumps(contract(hashlib.sha256(header).hexdigest())))
        allocation = {"reached_numpy_load": False}

        def forbidden_allocation(*args: Any, **kwargs: Any) -> Any:
            allocation["reached_numpy_load"] = True
            raise AssertionError("oversized shape reached array allocation")

        module.np.load = forbidden_allocation
        try:
            outcome = module.run(labels_path, mission_path)
            report["probes"]["oversized_header_before_allocation"] = {
                "outcome": outcome,
                "header_bytes": len(header),
                "allocation_attempted": allocation["reached_numpy_load"],
                "passed": outcome.get("status") == "REJECT" and not allocation["reached_numpy_load"],
            }
        except Exception as exc:
            report["probes"]["oversized_header_before_allocation"] = {
                "passed": False, "uncaught_exception": type(exc).__name__
            }
        finally:
            module.np.load = original_load
    report["passed"] = sum(bool(row.get("passed")) for row in report["probes"].values())
    report["total"] = len(report["probes"])
    (out / "review.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.out), indent=2))
