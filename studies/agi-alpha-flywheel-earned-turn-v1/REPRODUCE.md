# Reproduce the Earn the Next Turn study

Run these commands from a **new extracted copy of the complete package**, with its directory as the current working directory. Keep the delivered archive and recorded results unchanged. This guide distinguishes verifying recorded evidence, reproducing the same inputs, and opening fresh browser computation.

## 1. Environment

The executed numerical environment is pinned to:

| Component | Version |
|---|---|
| Python | 3.12.14 |
| NumPy | 2.4.6 |
| SciPy | 1.17.0 |
| Node.js | 24.22.1 |
| Matplotlib, for publication figures | 3.10.8 |
| XeLaTeX/BibTeX, for the paper | TeX Live 2023 with Latin Modern fonts |
| Optional browser QA | Playwright 1.62.1 with Chromium |

`requirements.txt` pins the Python packages. The upstream Alpha source has its own Node requirements; its historical Node 22.17.1 floor is not the exact Node version used for this experiment. Preserve the complete environment record when comparing timing measurements across machines.

Use a Python 3.12.14 environment and put Node 24.22.1 on `PATH`. A separate environment is recommended:

```bash
python3.12 -m venv .venv-earned-turn
. .venv-earned-turn/bin/activate
python -m pip install -r requirements.txt
```

Before importing numerical libraries, restrict their worker counts:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
```

Inspect the actual versions:

```bash
python -c "import sys,numpy,scipy; print(sys.version); print('NumPy',numpy.__version__,'SciPy',scipy.__version__)"
node --version
```

Installing dependencies may use the package network on your machine. Once installed, the research run makes no provider, wallet, contract or external service calls. There is no API key or credential setup. The local bridge requires a Linux/POSIX environment for the executed process accounting and custody file lock.

## 2. Restore and verify the packaged evidence before doing new work

The complete companion stores the original development, confirmation and operational records losslessly in `evidence/AGI_ALPHA_Earned_Turn_Raw_Evidence.tar.xz`. This avoids packaging thousands of redundant text blocks uncompressed. The content is the actual recorded evidence, not a recipe for regenerating it. Restore its original paths before auditing or replaying:

```bash
python unpack_evidence.py
```

The helper verifies the archive SHA-256, every member against `publication/RAW_EVIDENCE_MANIFEST.json`, and safe relative paths. It refuses to overwrite different existing files. Use `--verify-only` to read and validate without extracting. The paper-only archive does not include this large raw companion. Allow approximately 2 GB of free space for restored evidence in addition to the compressed package. Extraction executes no missions.

The complete delivery contains an existing `protocol/FREEZE.json`. Require it to exist before verification:

```bash
python -c "from pathlib import Path; assert Path('protocol/FREEZE.json').is_file(), 'Use the final package with its existing freeze; do not invent a new identity.'"
python protocol/freeze.py
```

On a complete frozen package, the second command verifies the exact file identities and prints the freeze hash. The script is also the original freeze constructor: if `FREEZE.json` is absent, it creates a new one. **Do not use that creation behavior to legitimize a modified copy or a missing artifact.** A changed file should be investigated as a new version, not repaired by replacing the old freeze.

The confirmation runner independently checks every frozen file at launch and completion. The source manifest covers the fixed numerical implementation, task generation, driver, checker, independent aggregation, budget custody, exact workbench closure, protocol, calibration and browser executable closure. Presentation files and post-run derived records have their own final delivery hashes.

Verify the published archive hash and its payload manifest as described by the final verification record. The standalone displayed PDF may carry file-serving provenance metadata; the authoritative author PDF inside the complete source archive is the byte identity used for the clean rebuild.

## 3. Inspect and reaggregate recorded evidence

The original fresh campaign is stored under `results/confirmation-v1/`. Start with:

- `SEEDS.json`: the original 24 network seeds and the source freeze identity.
- `EXECUTION.json`: one recorded launch, order, environment, timing and status.
- `SUMMARIES.json` and `trials/*/summary.json`: participant outcomes, including failed or unattempted work.
- Each trial's `tasks.json`, `solutions.npz`, `rows.json`, `events.json`, workbench packs, capability files and custody journal.

To derive producer analysis from those existing records, write to a new path:

```bash
mkdir -p reproduction-audit
python companion/analyze.py results/confirmation-v1 --out reproduction-audit/ANALYSIS.json
```

This does not rerun a mission. It reads the recorded stream summaries.

For a separately implemented raw-data audit, obtain the exact freeze hash and pass it explicitly:

```bash
EARNED_TURN_FREEZE=$(python -c "import json; print(json.load(open('protocol/FREEZE.json'))['freeze_sha256'])")
python review/independent_results.py \
  --results results/confirmation-v1 \
  --expected-source "$EARNED_TURN_FREEZE" \
  --output reproduction-audit/INDEPENDENT_RESULTS.json
```

The auditor rechecks task/output validity and result bindings, examines the recorded custody and pair structure, and independently aggregates the comparisons. It does not import the producer's analysis function. The checker and reviewer were developed within the same commission and host; this is not independently governed external replication. CPU hardware observations cannot be reconstructed after the fact; the auditor checks internal consistency and artifact attribution rather than inventing a second measurement of historical CPU.

Additional audit CPU is new research overhead. Do not silently add it to already recorded participant CPU or omit it when discussing complete research investment.

## 4. Reproduce the original inputs in a new output directory

Use the delivered seed file. The output directory must not already exist:

```bash
python companion/confirm.py \
  --out reproduction-original-seeds \
  --seeds-file results/confirmation-v1/SEEDS.json
```

The runner labels this **`REPRODUCTION_NOT_ADDITIONAL_CONFIRMATION`**. It executes all seven arms on the same 24 streams, for 168 stream/arm trials, under the frozen source and deterministic arm-order rule. It writes its own inputs, outputs, failures, receipts, journals, timing and summaries into the new directory.

Do not omit `--seeds-file` for reproduction. Without that option the original driver generates new secret seeds and labels them a first frozen confirmation; the label alone does not grant the right to perform another confirmatory search. A new study needs a separately identified protocol and repeated-testing accounting. The delivered campaign does not authorize an unlimited sequence of reruns until a favorable interval appears.

To analyze the reproduction:

```bash
python companion/analyze.py reproduction-original-seeds --out reproduction-audit/REPRODUCED_ANALYSIS.json
python review/independent_results.py \
  --results reproduction-original-seeds \
  --expected-source "$EARNED_TURN_FREEZE" \
  --output reproduction-audit/REPRODUCED_INDEPENDENT_RESULTS.json
```

Expect matching task identities and appropriately close valid numerical outputs. CPU, elapsed time, ordering perturbations from the operating system, compressed-file metadata and resulting timing-based decisions need not be byte-identical across machines. Retain any failures rather than substituting original numbers. The independent unit remains the complete network stream, not each load or each node.

The foreground campaign runs automatically after one launch but is not an installed persistent service. A killed process is not automatically restarted. The raw recovery probes demonstrate narrower recovery guarantees; they do not supply a general background supervisor for an interrupted entire confirmation campaign. Do not restart a partially executed confirmation into the same path or relabel an ad hoc continuation as the original fresh run.

## 5. Operational and browser checks

Existing source-bound development records are in `runtime/`, `review/` and `browser/qa/`. Their exact scope is stated in each record. In particular, maintenance within the main stream is a matched memory eviction and real persisted-array reload; a separate two-process probe tests an actual process exit and lost acknowledgement. These are different tests.

To repeat component checks in your extracted working copy:

```bash
python runtime/test_bridge.py
python runtime/test_custody.py
python review/test_checker.py
python review/test_numerical.py
node browser/checker.test.mjs
```

These commands may update local test reports in the working copy. They are component tests, not a new efficacy campaign or automatic qualification of a changed source tree.

The packaged actual process-recovery evidence can be inspected with `runtime/verify_process_recovery.py`; that verifier writes a fresh `READ_ONLY_VERIFICATION.json` into the directory supplied to it. Copy the evidence directory first if preserving every original byte is required. It checks the original numerical outputs and journal bindings without executing the missions again. To execute a new two-process probe instead, use the script's documented `--out` and exact source identity in a new directory, and label its result as a new operational reproduction.

For the default browser experience, simply open `browser/index.html`. Rebuild it from source with:

```bash
python browser/build_demo.py
```

Its recorded-study panel and fresh JavaScript computation are separate. The browser has no authenticated approved-executor connection. Its operation-count budget is a different accounting model from native CPU, and it does not test earned-credit reinvestment. The browser's execution lock remains fixed when recorded research JSON is embedded.

Optional automated UI and recovery checks require the pinned Playwright dependency; see `browser/README.md`. These checks block outbound HTTP requests. Browser screenshot PNGs are inspection intermediates and are not required research payloads.

## 6. Rebuild and inspect the paper

In the fresh extracted copy:

```bash
bash paper/build.sh
```

The script generates editable vector figures, runs XeLaTeX/BibTeX with the fixed source date and PDF identity, and rejects overfull boxes, missing glyphs and unresolved references. Use the complete final source package; missing manuscript modules are an incomplete package, not permission to substitute a placeholder.

For page inspection:

```bash
mkdir -p reproduction-audit/pdf-pages
pdftoppm -png -r 115 paper/AGI_ALPHA_FLYWHEEL_Earn_the_Next_Turn.pdf reproduction-audit/pdf-pages/page
```

Inspect every final page. The package's own rebuild and visual-review records bind the authoritative PDF; a clean TeX log is not a substitute for rendering.

## 7. What the cost and publication records do not establish

Whole-participant CPU includes stream setup, matrix assembly, hashes, checking, Python/Node work, persistence, failures, maintenance and raw evidence writing within the measurement boundary. Source reading, development, independent audit, publication and unknown human/model costs remain separate research obligations. Do not add CPU to wall time, count one debit twice, convert operation units into cash, or call released allowance a profit.

A correctness-qualified asset can still fail product admission. A prospectively useful method can still leave research investment unrecovered. This finite one-successor experiment does not test an increasing long-run improvement rate.

The recovered historical Strategy Laboratory replay is part of the previous Strategy Succession archive, linked by the prior evidence audit and [PR #4896](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4896). It is not an additional participant in this study. Earlier PDFs and their historical URLs remain separate.

Prepared source, review approval, merged code, released assets and verified live URLs are different states. Follow the final additive publication handoff and existing owner restrictions. Nothing in this reproduction guide grants Harness/Fleet clearance, new credentials, production modification or financial authority.
