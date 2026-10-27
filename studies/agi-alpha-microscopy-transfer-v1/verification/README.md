# Executed reproduction checks

This directory retains the evidence for the standalone replay driver. It is
separate from the original scientific confirmation and should not be counted as
new protected evaluation.

| Record | What was executed or checked |
|---|---|
| `reproduction-20261027/REPRODUCTION.json` | Complete offline replay using the original plain NPY distribution, including exact reconstruction from preserved chunks |
| `reproduction-gzip-20261027/REPRODUCTION.json` | Complete offline replay from a separate package containing only gzip representations of the three public NPY arrays |
| `reproduction-static-validation.json` | Ruff, strict mypy for the maintained driver, and 703 declared logical identities rechecked against the final distribution |
| `output-preservation-controls.json` | Refusal of the original study tree and of an occupied external output directory; existing receipt remained unchanged |
| `gzip-distribution-parity.json` | Final gzip files differ from the executed package only in the gzip OS header; all three decompressed NPY sequences are exactly equal |
| `dependency-lock-*.txt` | Preserved failed offline dependency-lock attempts; direct dependency pins remain available |

Both complete replay directories include the exact driver executed, commands,
stdout/stderr, file-identity receipts, and the stricter archived-output audit.
The first driver predates gzip-distribution support; its source is preserved
instead of replacing its recorded identity with the later one.

The current driver is SHA-256
`705e98f4e42c43ee02e21e65d83d40e0160ca3b2669965361ad301f8b5985125`.
It passed Ruff and strict mypy with `--follow-imports=skip`. These checks cover
that maintained driver, not a retroactive reformat or retyping of frozen upstream
implementations. Full repository setup, pre-commit, hosted CI, deployment and
canonical publication acceptance were not run by this reproduction subtask.

The unit tests invoked here are the existing eight accounting tests. Repeated
economic files matched the originals byte for byte; all 13,824 histories retained
cash conservation and the identical-library parity condition. Hosted model
answers were only rescored; no new live model calls or billing observations were
created. Numerical timings and randomized cryptographic receipts are recorded,
but are not deterministic equality targets or a demonstrated speed advantage.
