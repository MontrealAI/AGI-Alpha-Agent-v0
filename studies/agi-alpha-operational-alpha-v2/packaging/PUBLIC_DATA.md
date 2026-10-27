# Compact public source and exact recorded-data restoration

The complete downloadable research archive contains all original data. The separate compact public source package
may omit **only the seven generated files listed below**, totaling **156,004,562 bytes (148.78 MiB)**. Their original
byte counts and SHA-256 hashes remain in [public_data_manifest.json](public_data_manifest.json). Frozen source,
inputs, policies, seeds, summaries, exact participant prompts, submissions, corrections and historical evidence stay
in the public source package.

This is a packaging mechanism for previously recorded experiments. It does not create a new prospective study,
choose new policies, reveal new demand information, change an outcome or book new revenue.

## Restore before running the complete reproduction

From `studies/agi-alpha-operational-alpha-v2/`:

```sh
python packaging/materialize_recorded_data.py
python reproduce_all.py --report validation/my_complete_replay.json
```

The first command needs only Python's standard library, the local frozen files and sufficient local disk space.
It makes no network requests or model calls and needs no API keys. The second command uses the numerical and native
fixture dependencies documented in [../REPRODUCTION_ALL.md](../REPRODUCTION_ALL.md).

If using the complete downloadable archive, all seven files already exist. The bootstrap checks their hashes and
returns successfully without regenerating or writing them. Repeated execution after successful restoration behaves
the same way.

To check completeness without reconstructing anything:

```sh
python packaging/materialize_recorded_data.py --check
```

Missing data or a mismatch returns a nonzero exit status. Do not use Python optimization (`-O` or `PYTHONOPTIMIZE`),
which the bootstrap refuses. Do not remove files from the complete archive: omission belongs only to the separately
prepared compact public copy.

## Exact omitted paths

Paths are relative to the study directory.

| Recorded file | Original bytes | Frozen reconstruction |
|---|---:|---|
| `economics/results/development.json` | 5,187,330 | Original development search with recorded pilot input, seeds and objective |
| `economics/results/confirmation.json` | 8,867,397 | Original frozen selected policies and confirmation seeds |
| `economics/results/events.jsonl.gz` | 27,763,040 | Same original confirmation, including every emitted event |
| `economics/value_results/confirmation.json` | 19,128,346 | Frozen value-controller selections and original controls on their recorded worlds |
| `economics/value_results/events.jsonl.gz` | 62,832,933 | Same value-controller confirmation, including every emitted event |
| `economics/prescreen_results/prescreen_confirmation.json` | 1,937,991 | Frozen artificial candidate process and seed range |
| `opportunity/arrangement/results/conditional_frontier.json` | 30,287,525 | Frozen finite arrangement grid, assumptions and exact selection logic |

No other file is declared omittable by this manifest. In particular, the small value-controller development gzip,
all freezes, result summaries, completion records, original failure/correction histories, accepted code and packet
outputs remain present. This rule does not authorize removing historical studies or their unfavorable evidence.
The complete archive remains the canonical full-data distribution.

## What the bootstrap guarantees

The implementation has a fixed seven-path allowlist and a fixed reconstruction-source list. It rejects absolute,
traversal, ambiguous and symlinked paths. Before doing expensive work, it verifies all reconstruction sources and
inputs and verifies every declared data file already present. An existing file with different bytes stops the
operation; it is never silently replaced.

Missing outputs are reconstructed in new temporary directories on the study filesystem. The script invokes the
unchanged frozen implementations rather than a substitute generator. It compares generated companion freezes,
selected policies, summaries and completion records against their originals. It then verifies **every missing
output's exact length and SHA-256 before installing the first file**.

Installation uses atomic hard links that can create an absent destination but cannot overwrite an existing one.
The full destination set is rechecked before installation. A concurrent matching file is accepted; a conflicting file
is refused. This provides per-file atomic installation, not a multi-file filesystem transaction. An operating-system
failure during installation may leave a subset of correctly verified files installed; rerunning safely restores the
remaining absent files. Existing evidence is preserved throughout.

Temporary reconstruction outputs are removed after completion or failure. The script prints a structured report
with the original missing-file list, generation timings, installed paths and any error. Brief stage progress appears
on standard error. It never calls the hosted frontier participants or updates the original reproducibility programs.

## Byte identity and runtime limits

The recorded environment is Python **3.12.14** with zlib **1.3.2**. Both event streams were written with gzip
`mtime=0` and an empty filename. The original stream uses compression level **9**; the value-controller stream uses
level **6**. These settings are preserved by the original source programs.

Different Python, floating-point math or zlib builds can change generated or compressed bytes even when some decoded
values agree. The bootstrap does not accept approximate replacements: **any recorded hash mismatch stops installation**.
Use the matching recorded environment or the complete data archive if exact regeneration fails. Neither an altered
compression header nor a new serialization becomes a replacement original result.

Staging plus installed data requires local disk headroom. The restored seven files occupy approximately 149 MiB;
allow at least several hundred MiB for temporary generated outputs, retained sources and normal operating overhead.
This is local storage guidance, not a measured complete economic cost.

In the reviewed environment, restoring all seven files took **102.17 seconds**. The subsequent default
`reproduce_all.py` check took **22.90 seconds**; no second full economic re-execution was requested. Rechecking
an already complete copy took approximately **0.12 seconds**. These are local observations, not portable
performance guarantees.

The clean compact-copy test and negative controls are recorded in
[../validation/public_bootstrap_review.json](../validation/public_bootstrap_review.json). That review includes exact
restored hashes, preserved retained files, a default complete-edition replay, idempotent execution, refusal of unsafe
manifest paths and refusal to overwrite mismatched existing evidence. It does not rerun hosted models, grant
production admission or claim full repository CI.
