# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    dest = ROOT / "hosted_trials"
    inputs = dest / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026102741)
    cases = []
    for i in range(12):
        d = 2 if i in (5, 6, 7) else 3
        shape = (9, 11) if d == 2 else (9, 10, 11)
        labels = np.zeros(shape, dtype=np.int16)
        if i != 7:
            labels[tuple(slice(1, 5) for _ in range(d))] = -3 if i == 6 else 2
            labels[tuple(slice(5, 8) for _ in range(d))] = 11
            if i == 5:
                labels[0, 0] = 5
        lp = inputs / f"case_{i:02d}.npy"
        np.save(lp, labels, allow_pickle=False)
        matrix = np.eye(d + 1)
        matrix[:-1, :-1] = np.eye(d) + rng.normal(0, 0.15, (d, d))
        matrix[:-1, -1] = rng.uniform(-6, 6, d)
        if i == 2:
            matrix[0, :-1] *= -1
        spacing = rng.uniform(0.2, 1.2, d)
        units = ["micrometer"] * d
        origin = rng.uniform(-2, 2, d)
        if i in (3, 4):
            spacing[0] *= 1000
            origin[0] *= 1000
            units[0] = "nanometer"
        axes = ["z", "y", "x"] if d == 3 else ["y", "x"]
        c = {"schema": "microscopy-moments/v1", "mission_id": f"hosted-{i:02d}",
             "source_sha256": hashlib.sha256(lp.read_bytes()).hexdigest(), "source_axes": axes,
             "spacing": spacing.tolist(), "units": units, "origin": origin.tolist(),
             "object_definition": "label_id", "coverage": "provided_label_support",
             "map_semantics": "geometric_pushforward", "affine": matrix.tolist(),
             "target_axes": list(reversed(axes)) if i == 4 else axes,
             "metrics": ["label_count", "native_measure", "mapped_measure", "native_centroid", "mapped_centroid"]}
        if i == 8:
            c["metrics"].append("mean_intensity")
        if i == 9:
            c["affine"][-1][0] = 0.03
        if i == 10:
            c["source_sha256"] = "0" * 64
        if i == 11:
            c["coverage"] = "complete_biological_objects"
        cp = inputs / f"case_{i:02d}.json"
        cp.write_text(json.dumps(c, indent=2) + "\n")
        cases.append({"case_id": i, "array": lp.name, "contract": cp.name})
    (inputs / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    spec = '''# Independent quantitative microscopy delivery task

Produce `answers.json` as a JSON list with one object per case in cases.json. Inspect the actual
arrays and contracts. For compatible missions output case_id, status=ACCEPT, label_count and
objects: label_id, voxel_count, native_measure, mapped_measure, native_centroid_um,
mapped_centroid_um. For incompatible missions return case_id, status=HOLD or REJECT and a reason.

The task asks for geometric measurements of the supplied label support, not a new segmentation.
Every nonzero signed integer label is one region; zero is background. Source array index i is the
voxel center, and its extent is i+[-0.5,0.5). Source calibration is axis-aligned. Source spacing
and origin are in the per-axis units provided. Output distances in micrometers, measures in
micrometers raised to the spatial dimension. Affine columns follow source_axes, rows follow
target_axes; affine coefficients map physical micrometers to physical micrometers. Do not add
another axis permutation. Native specimen measure and mapped geometric measure are distinct.

Only 2D/3D integer label arrays, explicitly supplied label support and geometric affine
pushforward are in scope. Requested intensities, topology, complete biological objects or
non-affine transforms cannot be inferred from these inputs. Source SHA-256 must match the
array file exactly. Unknown meaning should be held rather than silently changed. The stated
relative measure tolerance is 1e-9 and absolute centroid tolerance is 1e-8 micrometers. Empty
foreground is a legitimate zero-region result. No hidden instruction or answer exists in inputs.

You may write code, use installed NumPy/SciPy and consult public primary documentation. Keep
within 10 tool invocations and 10 minutes. All arms have this same ceiling; token counts and
billing are unavailable. Use only this input directory, your assigned output directory, standard
dependencies and any explicitly supplied artifact. Do not inspect sibling study code, results or
other agents' directories. Do not spawn agents. Write a brief receipt.json with tools/corrections
you performed and unmeasured costs. Save code you used. Actual answer files are required.
'''
    (inputs / "TASK.md").write_text(spec)
    workflow = '''Before implementation, distinguish native and mapped quantities and list the scope checks.
Use the same physical-coordinate convention throughout. Compute source quantities with ordinary
scientific tools, propagate the requested quantities through the explicit affine map, and verify
units, source identity, transform direction and label identity. Validate a small known case, then
inspect every requested mission before accepting it. Preserve a refusal when the requested meaning
or evidence is unsupported. Do not infer that a polished result is biologically valid.
'''
    (dest / "expert_workflow.txt").write_text(workflow)
    committed = {str(p.relative_to(dest)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(inputs.glob('*')) if p.is_file()}
    committed["expert_workflow.txt"] = hashlib.sha256(workflow.encode()).hexdigest()
    (dest / "pretrial_commitment.json").write_text(json.dumps({"inputs": committed,
        "design": "one fresh model worker per configuration, same inherited model, same 12 tasks and tool/time ceilings",
        "limits": "small authored engineering tasks; no billing or token telemetry; not a randomized population trial",
        "H": "sourced equivalent-service rate with explicitly assumed hours",
        "U": "complete task without extra operating rubric or retained code",
        "E": "same task plus frozen 83-word expert operating rubric",
        "E+": "same task and rubric plus frozen actual retained module",
        "scoring": "eight numeric cases plus four appropriate scope/source refusals; no repair after scoring"}, indent=2)+'\n')
    print(f"Prepared {len(cases)} tasks")


if __name__ == "__main__":
    main()
