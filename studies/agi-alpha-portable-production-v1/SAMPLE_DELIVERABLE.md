<!-- SPDX-License-Identifier: Apache-2.0 -->
# Portable nominal feature package

This supporting deliverable contains editable nominal geometry for three
upstream CadQuery educational examples. It is conventional CAD construction,
not an admitted transformational enterprise milestone or a customer delivery.

## Files and use

The source-controlled feature program is `src/feature_program.json`.
`src/produce.py` constructs the parts from stock, outer corner radius and typed
holes. Each current output folder in `results/construction_v1_2/` contains:

- `part.step`: boundary-representation geometry for import into CAD tools.
- `part.stl`: a mesh approximation for visualization; it is not manufacturing approval.
- `part.svg`: a nominal geometric preview.
- `feature_program.json`: the editable per-part feature recipe.
- `features.csv`: nominal hole locations, sizes and feature types.

Run from this extracted study directory using the supported replay entry point:

```sh
python reproduce.py /absolute/new/replay-directory
```

The destination must not exist. The runner uses the packaged `data/public/`
sources, verifies frozen identities, reproduces the known cases, and invokes
the strict supplementary evidence check. It needs Python 3.12, CadQuery 2.7.0
and its OpenCascade dependencies. See `requirements.txt` and `README.md`.
Replaying disclosed cases does not create additional fresh confirmation.

The frozen historical script remains available for inspecting earlier behavior;
it should not be used as the standalone evidence gate or with untrusted inputs.
Missing and duplicate feature IDs remain unhandled. The recipe stores explicit
coordinates and does not preserve all source parameter dependencies.

## What each example contains

| Case | Nominal stock | Features |
|---|---|---|
| block_002 |80 x60 x10| One centered22-diameter through hole |
| pillow_003 |80 x100 x10| Center22 hole; four2.4 through holes at(+/-34,+/-44), top4.4 counterbores2.1 deep; outer vertical corner radius2 |
| countersink_019 |4 x2 x0.5| Four0.125 through holes at(+/-1.75,+/-0.75), top0.25 countersinks of82 degrees included angle |

These values reproduce executable source semantics. In Ex003, the source's
comment describes an edge inset12, but its construction rectangle places the
holes6 units from each edge. The package preserves the executable interpretation
and records the discrepancy. Ex002 and Ex003 have millimeter comments; Ex019
does not specify physical units. Its STEP file has millimeter-tagged coordinates
as an export convention only. A legitimate specification must resolve units
before any production use.

## Acceptance and limits

The native reference is the exact upstream example executed using CadQuery2.7.0;
only the display function is replaced by a no-op. The new constructor builds
holes using primitive Boolean operations. Comparisons include valid single
solids, nominal dimensions, analytic volume, exact Boolean difference, and
STEP export/reimport. Both geometry paths use the same OpenCascade kernel;
these are not independent kernels or physical measurements.

Original v1 accepted0/3 because triangulation-cached bounding boxes failed the
frozen dimension checks. That source and result remain preserved. Measurement
amendment1.1 switched only to exact-geometry bounding boxes and accepted3/3
on the same examples. Version1.2 further narrows admitted input geometry before
separate fresh confirmation. The amendment documents explain both changes.
Replaying these examples is historical reproduction, not fresh confirmation.

No material, manufacturing tolerance, datum system, surface finish, feed/speed,
machine program, machine release, physical inspection or customer acceptance
is supplied. A numeric software comparison threshold is not a physical
manufacturing tolerance. The feature interpretation was manually authored from
the upstream programs; this package is not an automatic drawing interpreter.
No training, live ENS authentication, paid sale or incremental Alpha is claimed.

## Permissions and provenance

Sources are CadQuery contributors' Apache-2.0 examples at commit
`8178185a24a035c9af7f4679033be14267f6a6ef`. Exact files, source URLs, Git blob
identities, SHA256 values and license are in `data/public/`. No private
designs were used. New source code is Apache-2.0. This artifact neither
modifies nor supersedes AGI ALPHA PR#4980's manufacturing-evidence audit.
