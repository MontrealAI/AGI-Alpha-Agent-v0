import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

import numpy as np
import scipy

from confirmation_reference import compare, conventional_map, conventional_prepare, coordinate_prepare, coordinate_reference


ROOT = Path(__file__).resolve().parent
EXPECTED_SOURCE = "a04326ce0504bfe3ac290b6cb65ee6f089cc66a607f70b7cc7869099250c77db"
EXPECTED_TASKS = "a340f72f6efe4ec41f0d0b51de14f9131989318f6fe89818c680fcf46509fbd5"
SPACING = np.array([0.75, 0.2516, 0.2516])


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def mission(task, source_hash):
    affine = np.eye(4)
    affine[:3, :3] = task["linear_zyx"]
    affine[:3, 3] = task["translation_zyx_um"]
    return {"schema": "microscopy-moments/v1", "mission_id": task["task_id"],
            "source_sha256": source_hash, "source_axes": ["z", "y", "x"],
            "spacing": SPACING.tolist(), "units": ["micrometer"] * 3,
            "origin": [0.0] * 3, "object_definition": "label_id",
            "coverage": "provided_label_support", "map_semantics": "geometric_pushforward",
            "affine": affine.tolist(), "target_axes": ["z", "y", "x"],
            "metrics": ["label_count", "native_measure", "mapped_measure", "native_centroid", "mapped_centroid"]}


def invoke(module, labels, contract, output, cwd):
    started = time.perf_counter()
    process = subprocess.run([sys.executable, str(module), "--labels", str(labels),
                              "--contract", str(contract), "--output", str(output)],
                             cwd=cwd, capture_output=True, text=True, timeout=90, env=os.environ.copy())
    elapsed = time.perf_counter() - started
    output.with_suffix(".stdout.txt").write_text(process.stdout)
    output.with_suffix(".stderr.txt").write_text(process.stderr)
    result = json.loads(output.read_text()) if output.exists() else {"status": "PROCESS_FAILURE"}
    return result, {"returncode": process.returncode, "external_process_seconds": elapsed,
                    "module_sha256": sha(module), "output_sha256": sha(output) if output.exists() else None,
                    "stdout": process.stdout, "stderr": process.stderr}


def semantic_mutation(case, original, labels, out):
    contract = copy.deepcopy(original)
    contract["mission_id"] = "semantic-" + case["id"]
    name = case["id"]
    array = labels
    if name == "negative_spacing": contract["spacing"][1] = -0.25
    elif name == "zero_spacing": contract["spacing"][0] = 0
    elif name == "nonfinite_spacing": contract["spacing"][0] = float("nan")
    elif name == "singular_affine": contract["affine"][0][:3] = [0, 0, 0]
    elif name == "nonfinite_affine": contract["affine"][0][0] = float("inf")
    elif name == "source_hash_mismatch": contract["source_sha256"] = "0" * 64
    elif name == "nonlinear_request": contract["nonlinear_deformation_field"] = "missing-jacobian-model"
    elif name == "intensity_request": contract["metrics"] = ["mean_fluorescence_intensity"]
    elif name == "topology_request": contract["object_definition"] = "connected_component"
    elif name == "physical_native_claim_for_deformation":
        contract["affine"][0][0] = 2
        contract["map_semantics"] = "native_physical_volume_equals_deformed_geometric_volume"
    elif name == "wrong_transform_direction": contract["transform_direction"] = "target_to_source"
    elif name == "non_3d_labels":
        array = out / "unresolved_time_axis.npy"
        np.save(array, np.load(labels, allow_pickle=False)[None, ...], allow_pickle=False)
        contract["source_sha256"] = sha(array)
    else: raise ValueError(name)
    return contract, array


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "confirmation/results/frozen-v1")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tasks_path = ROOT / "protocols/held_tasks.json"
    recovered = ROOT / "integration/results/frozen-v1/received-artifact.py"
    if sha(tasks_path) != EXPECTED_TASKS or sha(recovered) != EXPECTED_SOURCE:
        raise RuntimeError("Precommitted task or recovered artifact bytes differ")
    if sha(ROOT / "src/microscopy_transfer.py") != EXPECTED_SOURCE:
        raise RuntimeError("Frozen source identity changed")
    tasks = json.loads(tasks_path.read_text())
    library = out / "ordinary-library/microscopy_transfer.py"
    library.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(recovered, library)
    manifest = json.loads((ROOT / "data/confirmation/idr0052/manifest.json").read_text())
    data = {}
    for group in ["Cell", "Chromosomes"]:
        file = ROOT / "data/confirmation/idr0052" / (group.lower() + "_t7_native.npy")
        entry = next(a for a in manifest["arrays"] if a["file"] == file.name)
        if sha(file) != entry["sha256"]:
            raise RuntimeError("Held data bytes differ")
        array = np.load(file, allow_pickle=False)
        prepared = conventional_prepare(array, SPACING)
        points = coordinate_prepare(array, SPACING)
        data[group] = {"file": file, "sha256": sha(file), "array": array,
                       "prepared": prepared, "points": points}
    records = []
    for task in tasks["tasks"]:
        item = data[task["group"]]
        current = out / "compatible" / task["task_id"]
        current.mkdir(parents=True)
        contract = mission(task, item["sha256"])
        write_json(current / "contract.json", contract)
        linear = np.asarray(task["linear_zyx"])
        translation = np.asarray(task["translation_zyx_um"])
        reference = coordinate_reference(item["points"], SPACING, linear, translation)
        ordinary = conventional_map(item["prepared"], linear, translation)
        write_json(current / "coordinate-reference.json", reference)
        write_json(current / "conventional-analytical.json", ordinary)
        received, receipt = invoke(recovered, item["file"], current / "contract.json",
                                    current / "received-result.json", ROOT)
        equal, equal_receipt = invoke(library, item["file"], current / "contract.json",
                                      current / "ordinary-library-result.json", library.parent)
        received_comparison = compare(received, reference)
        ordinary_comparison = compare(ordinary, reference)
        library_comparison = compare(equal, reference)
        received_scientific = {k: v for k, v in received.items() if k != "elapsed_seconds"}
        equal_scientific = {k: v for k, v in equal.items() if k != "elapsed_seconds"}
        record = {"task_id": task["task_id"], "group": task["group"], "kind": task["kind"],
                  "recovered": received_comparison, "conventional": ordinary_comparison,
                  "ordinary_library": library_comparison,
                  "identical_content_output_parity": received_scientific == equal_scientific,
                  "recovered_process": receipt, "ordinary_library_process": equal_receipt,
                  "recovered_numerical_seconds": received.get("elapsed_seconds"),
                  "conventional_map_seconds": ordinary["elapsed_seconds"],
                  "ordinary_library_numerical_seconds": equal.get("elapsed_seconds")}
        records.append(record)
        write_json(current / "evaluation.json", record)
    refusals = []
    template = mission(tasks["tasks"][0], data["Cell"]["sha256"])
    for case in tasks["refusal_tasks"]:
        current = out / "semantic" / case["id"]
        current.mkdir(parents=True)
        contract, labels = semantic_mutation(case, template, data["Cell"]["file"], current)
        contract_file = current / "contract.json"
        contract_file.write_text(json.dumps(contract, indent=2, allow_nan=True) + "\n")
        result, receipt = invoke(recovered, labels, contract_file, current / "received-result.json", ROOT)
        record = {"case_id": case["id"], "expected": case["expected"], "reason": case["reason"],
                  "observed_status": result.get("status"), "observed_reason": result.get("reason"),
                  "passed": result.get("status") in ("HOLD", "REJECT") and receipt["returncode"] == 0,
                  "process": receipt}
        refusals.append(record)
        write_json(current / "evaluation.json", record)
    summary = {
        "edition": "microscopy-transfer/confirmation-1.0",
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_sha256": EXPECTED_SOURCE, "task_sha256": EXPECTED_TASKS,
        "source_freeze": "2026-10-27T17:40:14.874015+00:00",
        "n_compatible_missions": len(records), "n_semantic_cases": len(refusals),
        "recovered_passed": sum(r["recovered"]["passed"] for r in records),
        "conventional_passed": sum(r["conventional"]["passed"] for r in records),
        "ordinary_library_passed": sum(r["ordinary_library"]["passed"] for r in records),
        "identical_content_output_parity": sum(r["identical_content_output_parity"] for r in records),
        "semantic_passed": sum(r["passed"] for r in refusals),
        "source_array_summaries": {g: {"source_sha256": d["sha256"], "shape": list(d["array"].shape),
            "supplied_label_ids": [int(v) for v in d["prepared"]["ids"]],
            "source_nonzero_voxels": int(d["prepared"]["counts"].sum()),
            "conventional_summary_preparation_seconds": d["prepared"]["elapsed_seconds"]}
            for g, d in data.items()},
        "maximum_recovered_relative_measure_error": max(r["recovered"].get("maximum_relative_measure_error", 0) for r in records),
        "maximum_recovered_absolute_centroid_error_um": max(r["recovered"].get("maximum_absolute_centroid_error_um", 0) for r in records),
        "recovered_process_seconds_total": sum(r["recovered_process"]["external_process_seconds"] for r in records),
        "recovered_numerical_seconds_total": sum(r["recovered_numerical_seconds"] or 0 for r in records),
        "conventional_preparation_seconds_total": sum(d["prepared"]["elapsed_seconds"] for d in data.values()),
        "conventional_mapping_seconds_total": sum(r["conventional_map_seconds"] for r in records),
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "scope": ["Two supplied label groups from one fixed public image/timepoint; 48 authored affine missions, not 48 biological samples.",
                  "Artifact bytes recovered through existing lifecycle fixture, then executed in genuinely separate Python processes.",
                  "Same-content ordinary-library control has exactly the same source and rights; timings may differ, numerical/contract output must match.",
                  "Conventional analytical baseline prepares each source summary once and reuses it, with equal permission to cache.",
                  "Numerical elapsed time excludes Python startup, file hashing and serialization; external process clocks are recorded separately.",
                  "No observed frontier-model U/E/E+ advantage, customer acceptance, actual revenue, biological validation or live ENS authentication."],
        "compatible_results": records, "semantic_results": refusals,
    }
    write_json(out / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("compatible_results", "semantic_results")}, indent=2))


if __name__ == "__main__":
    main()
