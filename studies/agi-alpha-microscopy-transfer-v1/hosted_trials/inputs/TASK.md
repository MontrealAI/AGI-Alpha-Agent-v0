# Independent quantitative microscopy delivery task

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
