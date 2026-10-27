# Reproduce the connected study

The supplied package contains the public source arrays, their original compressed
chunks, source identities, protected-at-freeze task commitments, retained executable,
inherited lifecycle code, raw numerical results, and complete modeled economic
histories. The main replay needs no account, credential, model API, identity service,
network request, or customer access.

For compact distribution, the three large public NPY arrays may be supplied as
deterministic `.npy.gz` files. Their **decompressed bytes retain exactly the original
NPY hashes**. The driver checks those hashes in memory, then materializes the
arrays only in the new replay workspace. The original scientific runner and data
manifests are unchanged. Directly invoking a lower-level runner against a gzip-only
distribution requires that materialization first; the one-command replay handles it.

## One-command offline replay

With the study dependencies and Node.js installed, run from this directory:

```bash
python reproduce.py --output /tmp/microscopy-replay-01
```

Choose a **new or empty directory outside the original study tree**. The driver
refuses occupied destinations and paths that contain, or are contained by, the
original study. It verifies original evidence before and after the replay, creates
a separate executable copy, and writes all new outputs there. It never reruns a
writer against the original result directories.

To reconstruct all three NPY arrays from the preserved compressed chunks as well:

```bash
python reproduce.py --output /tmp/microscopy-replay-02 --rebuild-source-arrays
```

This optional stage requires `numcodecs==0.16.3`. Decoding and numerical replay
remain entirely offline. Rebuilt arrays must match the original NPY hashes exactly.
The recorded complete replay included this stage and passed.

## Environment

The observed numerical environment was Python **3.12.14**, NumPy **2.3.2**, SciPy
**1.17.0**, Pydantic **2.11.7**, cryptography **50.0.2**, and Numcodecs **0.16.3**.
The local inherited JavaScript lifecycle ran with Node.js **24.22.1**. The parent
repository requests Node.js **22.17.1**; no exact-environment qualification of that
version is claimed by this study replay.

Direct Python dependency pins are in `requirements-study.txt`. For a separate
environment, installing them normally requires package access or a prepared
wheelhouse before going offline:

```bash
python3.12 -m venv /tmp/microscopy-venv
/tmp/microscopy-venv/bin/python -m pip install -r requirements-study.txt
/tmp/microscopy-venv/bin/python reproduce.py --output /tmp/microscopy-replay-03
```

These direct pins are **not a complete transitive, wheel-hashed lock**. An offline
`pip-tools` lock attempt was made and preserved in `verification/`: the default
cache was unwritable, and a repeat using a writable cache found no offline NumPy
distribution. No lock file was fabricated. The successful replay used the
available, version-recorded environment. Full repository setup, pre-commit, hosted
CI, production-runtime qualification, and release/site acceptance remain separate.

## What the command actually does

1. Verifies the frozen instrument, conventional reference, mission protocol,
   held-task commitment, upstream source closure, maintained lifecycle callers,
   raw public chunks and arrays, initial scientific evidence, hosted-trial inputs
   and answers, and economic source/configuration/policy commitments.
2. Copies the executable closure into `OUTPUT/workspace/`, preserving source bytes
   and excluding caches. Earlier integration and economic outputs are not copied
   into their writable locations.
3. If requested, decodes the original public chunks into that copy and checks all
   three rebuilt array identities.
4. Runs the unchanged lifecycle caller, which executes 32 local conformance
   controls and writes a newly recovered `received-artifact.py`.
5. Runs the unchanged confirmation runner against those newly recovered bytes.
   The recovered recipient, conventional analytical baseline, and same-content
   ordinary-library control each attempt the same 48 affine missions; the
   recipient also attempts 12 semantic refusal cases.
6. Runs the eight existing accounting tests, repeats economic development on the
   same 24 development worlds, freezes the same policy, and regenerates the
   13,824 confirmation histories from the same disjoint 96-seed schedules.
7. Re-scores the **recorded** U/E/E+ worker answers with the common numerical
   evaluator. This does not launch new hosted model workers.
8. Audits the archived original scientific outputs with the stricter finite-value
   comparator, including its four NaN refusal probes.
9. Compares scientific acceptance, refusal status/reason, exact deterministic
   economic files, recorded hosted scores, and the original before/after hashes.

The copied confirmation runner retains its original path convention,
`integration/results/frozen-v1/received-artifact.py`. Within the isolated copy,
that path contains the artifact **newly recovered during this replay**, rather
than a copied original integration result. No runner code is rewritten to create
the connection.

## Inspect the result

`OUTPUT/REPRODUCTION.json` is the machine-readable receipt. `OUTPUT/logs/`
contains every executed command, its elapsed time, return code, stdout, and stderr.
`original-identities.json` and `copied-identities.json` document the checked bytes.
The full repeated outputs remain in `OUTPUT/workspace/` for inspection.

The completed study replay is preserved compactly in
`verification/reproduction-20261027/`. A second complete replay from a gzip-only
distribution is preserved in `verification/reproduction-gzip-20261027/`. The
plain-array replay's reported results are:

| Check | Repeated result |
|---|---:|
| Original committed logical file identities verified before and after | 703 |
| Local interface controls | 32/32 |
| Recovered recipient / conventional / identical library | 48/48 each |
| Appropriate semantic refusals | 12/12 |
| Recipient and library scientific JSON equal to originals, excluding numerical timing | 96/96 |
| Accounting tests | 8/8 |
| Economic policy, results, history CSV, and example ledger | Byte-identical |
| Simulated economic histories | 13,824 |
| Recorded hosted U / E / E+ answers re-scored | 12/12 each |
| Original source-array exports reconstructed from archived chunks | 3/3 exact |

The final distribution's gzip archives differ from the second replay's archives
only in byte 9, the gzip operating-system header. All three decompressed NPY
byte sequences are identical. This representation comparison and a fresh source
identity check are recorded in `verification/gzip-distribution-parity.json` and
`verification/reproduction-static-validation.json`; scientific outputs were not
rerun to resolve a header-only difference.

Scientific JSON equality is a diagnostic; acceptance uses the original finite
measurement tolerances. Numerical clocks, process paths, generated local signing
keys, journal identities, and randomized ciphertext are not deterministic result
targets. The receipt separately records semantic agreement and byte identity of
the recovered source.

## What reproduction does not establish

The 48 missions are authored maps over two supplied label groups from **one**
public image/timepoint. They were held out at the original freeze; they are now
disclosed, so replaying them is not another protected fresh trial. Source-label
geometry is not independent validation of segmentation, registration, complete
cell coverage, or biological interpretation.

Local identity and admission inputs are labeled fixtures. Real cryptographic
operations execute locally; no live ENS authentication or production microscopy
admission follows. The actual research ledger retains zero collections and unknown
complete research cost/profit.

The economic histories repeat conditional scenarios and supplied participant
rules. They do not become observed customer behavior or revenue through
reproduction. Hosted worker token use, billing, complete customer effort, and
comparable full-run latency were not available in the original task trials.
Re-scoring their answers cannot recover those missing measurements or prove a
quality/cost advantage for E over U or E+ over E.

Paper compilation, figure regeneration, and browser rendering are presentation
steps outside the numerical replay. The package preserves their source and final
artifacts separately. This replay is scoped evidence for the study, not a substitute
for the repository's required hosted merge and publication checks.
