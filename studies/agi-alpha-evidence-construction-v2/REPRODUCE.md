# Portable reproduction — additive evidence-construction edition v2

The offline runner re-executes the study's numerical programs and modeled lifecycle in a separate output tree. It does not overwrite the frozen scripts, development failures, original recipient deliverables or published results. A completed isolated run passed all **13 stages**, reproduced the **32 numerical confirmation cases**, and verified that all **164 copied input files** were unchanged. The receipt is [validation/portable-replay.json](validation/portable-replay.json).

This is a replay of executable evidence. It is not another frontier-model trial, customer trial, sale, live ENS authentication or production admission. Complete actual research and delivery costs remain **unknown**. Commercial amounts are conditional modeled quantities.

## Run from a checkout or the standalone research archive

Use Python 3.12 and Node.js on `PATH`. The observed environment was Python 3.12.14, Node 24.22.1, NumPy 2.3.2, SciPy 1.17.0, Pydantic 2.11.7, cryptography 50.0.2 and HTTPX 0.28.1. No browser, R, API key, customer credentials or network connection is needed for the public replay. The native bridge uses HTTPX as an import dependency; it does not call a network service in these stages.

For a clean environment, install the Python packages before going offline:

```bash
python3.12 -m venv /tmp/evidence-replay-env
source /tmp/evidence-replay-env/bin/activate
python -m pip install numpy==2.3.2 scipy==1.17.0 pydantic==2.11.7 cryptography==50.0.2 httpx==0.28.1
```

Set the study path to its actual location. The output directory must be new and outside the original study directory:

```bash
STUDY=/path/to/checkout/studies/agi-alpha-evidence-construction-v2
python "$STUDY/reproduce.py" --out /tmp/evidence-replay
```

The runner locates the two preserved predecessor studies beside this study by default. When they are stored elsewhere, supply the directory containing their study directories:

```bash
python "$STUDY/reproduce.py" \
  --dependency-studies /path/to/preserved/studies \
  --out /tmp/evidence-replay-separate-dependencies
```

Do not run a frozen historical script directly against the original tree if you intend to preserve its saved outputs. Use the runner's isolated copies. Run time in the observed environment was approximately 33 seconds across subprocess stages; this is a replay measurement, not recipient turnaround or provider labor.

## Exact predecessor closure for a standalone archive

Preserve these paths relative to the common `studies/` directory, with their original bytes:

1. `agi-alpha-capability-opportunity-v1/integration/bridge.py`.
2. `agi-alpha-capability-opportunity-v1/integration/source_manifest.json`.
3. All **29 files** whose integration-relative names occur in that manifest's `files[].local_path`. This includes the runtime and research lifecycle modules, fixture authority, provenance and license files.
4. `agi-alpha-opportunity-discovery-v1/economics/economics.py`, the unchanged exact-cent ledger.

The complete list with size and SHA-256 is [validation/reproduction-predecessors.json](validation/reproduction-predecessors.json): **32 files, 520,458 bytes**. The bridge verifies the original 29-file manifest before imports. Prior study results, data, recipient programs and `replay.mjs` are not needed by this runner; its transfer stage calls this edition's `integration/modeled_transfer.mjs`. The unused historical `bridge.run_lifecycle()` method would need its own extra adapter if invoked for a different purpose.

This archive closure preserves existing implementations and provenance; it does not introduce another registry. A complete repository checkout already contains the required paths. Packaging the closure alongside this study is sufficient; copying or recommitting whole predecessor studies is unnecessary.

## What is reproduced

| Stage | Executed evidence and comparison | Boundary |
|---|---|---|
| Development pilot and construction | Publisher-source contradictions and the two conditional rounding-feasibility branches; exact saved-result comparisons | A repaired authoritative point remains on HOLD. Feasibility intervals are not confidence intervals. |
| Independent development check | Independent source extraction and arithmetic against the saved golden result | Source interpretation remains an explicit part of the scientific task. |
| Numerical confirmation | Same frozen 32 generated cases and exact rational oracle comparisons against the actual inherited engine | Replay of the existing confirmation, not 32 additional independent cases. |
| U, E and E+ recipient programs | All three saved deterministic calculation programs, with numerical JSON equality apart from recorded environment versions | Does not replay their model sessions, prompting, elapsed time, grading judgment or original full packet. Historical 20/20 scores remain the archived adjudication. |
| Public source verification | Publisher hashes, public numerical checks and a clearly labeled public-subset verifier derivative | The original OSF raw-row grouping check is omitted by default, not replaced with invented data. |
| Economics v1 | All saved reference paths, the frozen 72 worlds, and saved summary exactly reproduced | The original v1 capacity omission remains preserved as history. |
| Economics v1.1 | Eight prospective capacity cases, 17 reference monetary/acceptance regressions and the exact deposit-aware pricing diagnostic | Corrected capacity accounting is the preferred prospective result; this does not replace or reroll the original 72 worlds. |
| Residual obligations | Saved verification-effort sensitivity at 0, 10, 25 and 60 minutes using the same cost helper | Supplier capacity and labor inputs remain assumptions. |
| Artifact transfer | Actual capability ZIP bytes recovered through the existing modeled network; exact SHA-256 identity | Economic admission and member identity are fixtures, not production authorization. |
| Native accounting | Existing signed accounting, duplicate/idempotence/revocation/scope controls, and modeled report reconciliation | Actual unknown costs remain unknown; the native complete-cost seal refuses them. No simulated collection becomes revenue. |

The core capsule identity is `32a9c193200f43c94b922c9b7f5460a60a57f44031f1b2c88c8a50b15766a930`. Its transfer replay preserves exact bytes. The ordinary-library comparison has identical capability contents and permissions; this edition claims no graph-specific performance premium.

## Path adaptations and comparison rules

The frozen E+ calculation contains the historical absolute packet path. The runner changes exactly that one literal in a temporary copy to the copied public packet location. It records the old and new paths and both source hashes in `summary.json`. The original remains unchanged.

The frozen private verifier expects publisher files and an OSF CSV in its original local layout. The default replay assembles the public files in an isolated directory and makes an explicitly labeled derivative: only the raw-data group-count check is replaced with a check of the sample sizes reported by the publisher. This derivative writes `public_verification_replay.json`, never the original private verification filename. Its mapping and distinct evidential scope are recorded.

Numerical comparisons ignore execution timestamps, execution durations, timestamp-dependent generated-case file hashes and recipient environment-version fields. All substantive case results and generated case content are compared. Native reports are compared without claiming repeatable ephemeral signing keys or journal identities. No frozen original script is edited.

Each stage saves separate stdout/stderr. The output also contains `source-copy-receipt.json`, the isolated working tree, `public-source-verification.json` and `summary.json`. A subprocess failure stops the run and preserves its logs. Repeating the command requires a new destination so a failed attempt cannot silently become a successful historical run.

## Optional historical OSF cross-check

The publisher packet is a post-run public subset under the publisher's CC BY terms. The original recipient packet also included author-linked OSF raw files and codebooks. Their independent redistribution license was not verified. They are **not included** here, and the original full `source_packet.tar.gz` must not be published. See [assay/source_packet/PUBLICATION_NOTE.md](assay/source_packet/PUBLICATION_NOTE.md).

The default runner explicitly records `SKIPPED_OPTIONAL_EXTERNAL_DATA_NOT_REDISTRIBUTED` for the raw-row check. It performs no download. A reader who independently obtains the original Experiment 1 CSV from the stable source recorded in the receipt may provide it:

```bash
python "$STUDY/reproduce.py" \
  --out /tmp/evidence-replay-with-local-data \
  --external-osf-file /private/local/Error_correction_PI_Experiment_1.csv
```

The expected CSV SHA-256 is `76e88825fc4b3b08c44ccb0e2a14bfd38bd1f4efcdde0dc54311eb12cdb89dc7`. A mismatch stops the run. With a matching file, the runner invokes an unchanged copy of the original verifier in a temporary layout, then removes the temporary raw data. It retains only the verification result. This option is not permission to redistribute the data and was not required for the documented public replay. The requested numerical contrasts are reproducible from the public summary statistics alone.

## Publication scan and limits

Run the bounded local scan after preparing this edition's package:

```bash
python "$STUDY/publication_scan.py"
```

It scans only this new study, reports paths and match digests without secret values, and checks signed cloud query parameters, recognizable token/private-key patterns and the forbidden OSF filenames. It also inspects decompressed ZIP/DOCX members. The receipt is [validation/publication-scan.json](validation/publication-scan.json). The completed scan had no pattern findings. This is a bounded check, not proof that all possible credentials, encodings or restricted content are absent. PDF compressed streams are not decoded by this helper; the public research PDFs have mechanical text companions. Images and arbitrarily encoded secrets are outside its scope.

Historical scratch paths in frozen scripts and receipts remain as provenance. The runner relocates the path that affects execution. All actual costs remain unknown even when replayed modeled ledgers reconcile exactly. Further live trials, invoice-quality cost measurement, delivery contracts, customer acceptance and production authorization are separate next steps.
