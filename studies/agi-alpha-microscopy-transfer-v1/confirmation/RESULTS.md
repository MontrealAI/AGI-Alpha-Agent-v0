# Fresh mission confirmation and executable transfer

**The frozen instrument successfully executed all 48 compatible held missions after being recovered through the existing lifecycle fixture. Its mathematical answers tied a strong conventional analytical baseline. An ordinary directory containing identical artifact bytes produced identical scientific results in all 48 cases.** These are observed software and numerical results; customer acceptance, model performance and sales are not measured by this test.

## What was held fresh

Development used IDR0062A image 6001240. Confirmation used a separate public study, IDR0052A image 5514375, fixed zero-based time index 7 and channel 0. The `Cell` and `Chromosomes` label groups were selected and extracted before their statistics or measurement outcomes were inspected. Each has native z/y/x shape 31 × 256 × 256 and metadata spacing 0.75 / 0.2516 / 0.2516 micrometers. Each group contains one supplied nonzero label identity, 8. The data therefore provide two distinct partitions of one image/timepoint, not 48 independent biological specimens.

The task file contains 24 affine missions per group: identity, translation, reflection, anisotropic scaling, shear and seeded combinations of rotations, scales, shears and translations. Task bytes were committed at 17:37:23 UTC on 27 October 2026, before the instrument source freeze at 17:40:14 UTC. The first evaluation completed at 17:42:57 UTC. The held source arrays were not used to revise the instrument. The source hash remains `a04326ce0504bfe3ac290b6cb65ee6f089cc66a607f70b7cc7869099250c77db`.

The recipient executes the exact recovered artifact in a new Python interpreter for each mission. This demonstrates executable artifact transfer between local configurations. The surrounding identity/lifecycle evidence is a labeled fixture; no live ENS authentication or production authorization is implied. The ordinary-library arm copies the same recovered bytes into an ordinary directory and executes them with the same inputs, rights and permissions.

## Independent comparison

The conventional method uses SciPy `ndimage.sum_labels` and `ndimage.center_of_mass`, the declared source spacing and ordinary affine algebra. It prepares each source summary once and reuses it across maps. This is a competent comparator with permission to use the same mathematical formulation and caching.

The numerical reference separately enumerates every occupied source voxel center, converts the coordinates into source micrometers, transforms all points, and averages them. Mapped voxel measure is calculated using a scalar triple product of transformed voxel basis vectors. This provides an independent implementation path for the same declared affine geometric quantity. It does not create an independent physical calibration or biological ground truth.

Acceptance was fixed before evaluation: exact label identities and voxel counts; native and mapped measure relative error at most 10⁻⁹; native and mapped centroid maximum absolute error at most 10⁻⁸ micrometers. Every compatible mission must explicitly request geometric pushforward of the supplied label support.

| Configuration | Compatible missions accepted | Error checks passed | Scientific parity with recovered artifact |
|---|---:|---:|---:|
| Recovered artifact, separate recipient process | 48/48 | 48/48 | — |
| Strong conventional analytical workflow | 48/48 | 48/48 | Same accepted quantities within tolerance |
| Ordinary directory, identical artifact contents | 48/48 | 48/48 | 48/48 exact, excluding measured elapsed time |

The maximum recovered relative measure discrepancy was **4.3964 × 10⁻¹⁶**; the maximum centroid discrepancy was **1.0737 × 10⁻¹¹ micrometers**. These numerical tolerances should not be interpreted as experimental precision of the microscope or biological labels.

At identity, the supplied Cell partition contained 115,632 foreground voxels and native measure 5,489.85121344 µm³. The Chromosomes partition contained 18,238 foreground voxels and native measure 865.88406696 µm³. These are geometric properties of the published partitions. No claim about true cell count, chromosome count, labeling completeness or segmentation accuracy follows.

## Meaning and refusal

All 12 precommitted incompatible or malformed cases returned a reasoned `HOLD` or `REJECT`, with no process crash. Cases covered negative/zero/nonfinite spacing, singular/nonfinite affine maps, source-byte mismatch, nonlinear mapping, fluorescence intensity, connected-component topology, treating mapped geometric volume as native physical volume, an unsupported reverse-direction declaration and an unresolved extra time axis.

The direction test checks an explicit unsupported contract field; it does not establish that software can detect a mathematically valid matrix whose caller secretly intended the reverse direction. The nonlinear/intensity/topology cases check contract boundaries, not performance on those new scientific tasks.

Reflection is compatible and uses the absolute determinant. Native physical measure remains tied to the source metric; mapped geometric measure changes under geometric deformation. A label can have disconnected support, so supplied label count and connected-component count remain distinct.

## Time and fair interpretation

| Recorded quantity, all 48 compatible missions | Seconds |
|---|---:|
| Recipient external process wall time, including startup and CLI work | 11.542 |
| Recipient reported numerical work | 2.200 |
| Identical ordinary-library external process wall time | 11.521 |
| Identical ordinary-library reported numerical work | 2.151 |
| Conventional source-summary preparation, two groups | 0.328 |
| Conventional affine mapping after preparation | 0.005 |

The recipient numerical timer excludes Python startup, file hashing and serialization. The conventional timings measure numerical preparation and mapping in the evaluator process. These are engineering diagnostics with different deployment overheads, not a matched latency superiority claim. The first run favors the conventional cached workflow; no timing advantage is attributed to the transferred instrument. If future production work needs caching, its implementation, validity and costs require their own version and evaluation.

This test establishes reusable executable behavior and fresh mission validation. It establishes **zero accepted-quality advantage over the competent conventional analytical workflow** and **zero numerical advantage attributable to graph storage over an equal-content ordinary library**. It does not measure U versus E or E+ versus E frontier-model outcomes, human labor savings, customer effort or the economics of live service delivery. Those quantities remain separate assumptions or future measurements.

## Audit and preservation

Every contract, numerical reference, baseline output, recipient output, process receipt, stdout and stderr is preserved in `results/frozen-v1/`. The initial evaluator source is preserved there as well. A post-run audit tightened the comparator to reject nonfinite values and duplicate identities explicitly; Python's `max` can otherwise mask NaNs. All preserved outputs are finite, and stricter re-scoring leaves every acceptance count unchanged. Four targeted NaN probes verify the new guard. No instrument code, task, source array or primary result was changed, and no favorable rerun replaced the first evaluation.

The original compressed data chunks, their metadata, source URLs, SHA-256 manifests and CC BY 4.0 attribution are retained in `data/confirmation/`. A disposable offline replay deleted both exported NumPy arrays, decoded the original compressed chunks again and reproduced both exact export hashes. Source image and label acquisition is observed; transforms are authored test inputs.

The next useful experiment is a bounded service trial with unfamiliar customer data and a strong existing expert workflow. Measure the time and residual obligations required to establish meaning, bind source bytes, validate the mission, correct defects and produce an accepted report. Equal-quality delivery alone is already demonstrated here; commercial advantage depends on savings or useful scope that the recipient does not already possess.
