# Reproduction and evidence verification

The delivered directory contains the evidence used for the paper. Preserve it as received. Some research scripts write their outputs relative to their own location, and several secondary analyses deliberately reject changed input hashes. Use a disposable complete copy for a new numerical run; use new output directories for frozen economic replay.

All commands below start from the **study root**, the directory containing this file, `src/`, `paper/`, `web/` and `evidence/`.

## 1. Verify and inspect the delivered package

The manifest verifier uses only Python's standard library and does not change files:

```bash
python verify_evidence.py
```

It checks every listed relative path, byte count and SHA-256 digest. It rejects missing files, duplicate entries, symbolic links, out-of-tree paths and changed bytes. The manifest itself and explicitly excluded generated caches/build logs are not self-authenticated. Compare the package/manifest identity through a trusted publication record when independent origin verification is required. A successful byte check does not establish a scientific result or deployment qualification.

Open `web/index.html` directly in a browser. Its data, controls and English/French text are embedded; there are no required remote data requests. Keep the complete tree so its paper and evidence links remain valid. If the browser prefers local HTTP, serve the study root:

```bash
python -m http.server 8080 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8080/web/index.html`. This local server does not publish the site externally.

The three largest complete simulation traces are delivered as `.jsonl.gz` files to keep the package compact. This is lossless packaging, not filtering: `provenance/compressed_evidence.json` records each original byte count, row count and SHA-256 along with its gzip identity. Python's `gzip.open(path, "rt")` reads them directly. New experiment runs write the original uncompressed `.jsonl` filenames; the analysis and replay commands do not require unpacking the historical traces.

## 2. Runtime and dependencies

The numerical and native executions used Python **3.12.14**. Native JavaScript lifecycle execution used Node.js **v24.22.1**. PDF generation uses `latexmk -pdf` and a working LaTeX distribution; the observed latexmk version was 4.83. Node and LaTeX are system prerequisites and are not installed by pip.

`requirements.txt` pins the directly used and explicitly observed Python dependencies. It is not a complete transitive dependency lock or a container-image digest. OR-Tools installs additional dependencies through its package metadata. SciPy 1.17.0 was present in the analysis environment but the supplied scheduling kernel does not require it.

Create an isolated environment in a disposable working copy:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python --version
node --version
latexmk --version
```

The original run loaded OR-Tools 9.14.6206 from an isolated temporary installation. Installing the pinned package in the environment above removes the need for that original temporary `PYTHONPATH`. No API keys, wallet funds, live ENS/RPC connection or model subscription are needed for these research reproductions.

## 3. Reuse the original calibration without recomputing the numerical study

This is the fastest way to reproduce the commercial analyses against exactly the delivered numerical calibration and its measured timings. Activate the environment, then create a fresh output root:

```bash
REPLAY_OUTPUT="$(mktemp -d /tmp/agi-alpha-evidence-replay.XXXXXX)"
python src/economics.py --output "$REPLAY_OUTPUT/economics" --repetitions 128
python src/native_integration.py --input "$REPLAY_OUTPUT/economics/native_input.json" --output "$REPLAY_OUTPUT/native" --self-test
python src/replay_expansion.py --output "$REPLAY_OUTPUT/expansion" --verify-only
python src/replay_expansion.py --output "$REPLAY_OUTPUT/expansion"
python src/compute_economics.py --output "$REPLAY_OUTPUT/compute-economics"
```

The primary economic controller checks its source hash against `config/economic_protocol.json`. The native adapter checks the eighteen-file source closure before importing it. With the bundled `vendor/runtime/`, a standalone copy does not need the rest of the upstream repository. Without that snapshot, the adapter falls back to the repository and still requires exactly the pinned bytes.

The quality-frontier economic supplement was frozen before a later primary-controller funding correction. **Use `replay_expansion.py` for that historical supplement.** It stages the original verified source and configuration from `evidence/expansion_source_snapshot/`, verifies all frozen input identities, and runs in a separate temporary tree. Calling the current `expansion_frontier.py` directly against its historical protocol correctly refuses the source mismatch. Neither the old evidence nor the guard should be altered to make that check pass.

`compute_economics.py` is the separate final stronger-Beta cost sensitivity. It uses the new twelve-case matched calibration and reports every quality tier and program-cost scenario. It refuses to overwrite an existing output pair. Its numbers are conditional expected collections/contributions per modeled booking, not observed customer revenue.

The `--repetitions 128` primary replay and the frozen 64-world supplement reproduce the delivered sampling budgets. A smaller repetition count is a different diagnostic, not the complete recorded experiment.

## 4. Recompute all numerical learning in a disposable copy

First copy the **whole study**, including the vendored native source and evidence-side postprocessing scripts. These commands keep the original tree untouched:

```bash
STUDY_SOURCE="$(pwd)"
REPLAY_PARENT="$(mktemp -d /tmp/agi-alpha-numerical-replay.XXXXXX)"
cp -a "$STUDY_SOURCE" "$REPLAY_PARENT/agi-alpha-next-advantage-v1"
cd "$REPLAY_PARENT/agi-alpha-next-advantage-v1"
mkdir -p replay-baseline
cp -a config replay-baseline/config
cp -a provenance replay-baseline/provenance
mv evidence/numerical/economic_calibration_primary.json replay-baseline/economic_calibration_primary.json
```

Create/activate the Python environment here as described above. If `.venv/` was copied from another absolute location, recreate it rather than relying on relocated interpreter entry points. The original delivered tree remains the authoritative evidence copy; the baseline directory preserves the configuration identities used before this recalculation.

Run the primary numerical experiment and the declared secondary analyses in this order:

```bash
python src/numerical.py
python evidence/numerical/quality_frontier_analysis.py
python evidence/numerical/cp_extension.py
python evidence/numerical/beta_expansion.py
python evidence/numerical/beta144_confirmation.py
```

These commands execute:

| Stage | Actual scope |
| --- | --- |
| Main numerical run | 8 productive-development cases; 24 Gym cases; 24 development cases; 80 fresh primary confirmation cases; six modes and two offerings; original CP-SAT challenge |
| Quality postprocessing | All predefined quality tiers; paired mode contrasts; complete development/confirmation calibration; preserved interrupted-attempt accounting |
| CP-SAT extension | Twelve existing primary cases, two warm starts and one declared larger deterministic budget |
| Generic-search expansion | Twelve existing primary cases, 144-candidate Beta versus the saved 48-candidate methods |
| Final stronger-Beta confirmation | 24 original development cases plus 12 new cases; Beta48, learned48 and Beta144; both offerings; no retraining |

The main CLI also accepts `--output PATH` and `--skip-cp-sat`. The latter omits the solver challenge and is not the complete delivered run. Several postprocessors intentionally locate input/output files beside themselves; this is why a complete disposable copy is the recommended route. The main script writes `config/numerical_protocol.json` even when `--output` is supplied.

Moving the copied `economic_calibration_primary.json` before the run is necessary: the quality postprocessor preserves that file once created. Leaving an earlier copy in place would retain earlier timing metadata during enrichment. Do not delete or move the original file in the delivered tree.

The interrupted original attempt is preserved as historical evidence and is not rerun. Repeating the same deterministic seeds reproduces the experiment; it does not create a newly independent holdout. A genuinely new confirmation campaign requires its own prospective protocol and fresh seeds.

## 5. Recalculate economics from the newly measured numerical run

Continue **only in the disposable copy**. Changed measured timings alter calibration hashes, so declare a new computational replay instead of pretending that the historical input identity is unchanged:

```bash
python src/economics.py --freeze
python src/economics.py --output replay-output/economics --repetitions 128
python src/native_integration.py --input replay-output/economics/native_input.json --output replay-output/native --self-test
mv config/compute_economics_protocol.json replay-baseline/compute_economics_protocol.json
python src/compute_economics.py --freeze
python src/compute_economics.py --output replay-output/compute-economics
```

The new freezes bind the current copied source and the new timing-bearing artifacts; they do not replace the original publication's evidence. The historical expansion supplement should still be replayed through step 3 from an untouched delivered tree, where its original calibration hash remains available. Do not waive a source/input guard to reuse it with new inputs.

The primary economic CLI accepts `--calibration PATH`, `--output PATH`, `--repetitions N` and `--freeze`. `--freeze` declares the configured controller and exits; it does not run the enterprise experiment. Native replay accepts `--input PATH`, required `--output PATH` and `--self-test`.

## 6. Tests and native controls

From the study root in an activated environment:

```bash
python tests/test_scheduling.py
python -m pytest -q tests --noconftest
```

The first command runs the nine numerical integrity tests. The second runs the study's own native/economic/frontier tests as well. `--noconftest` isolates the standalone research test suite from the upstream repository's application-wide test setup; it is not full-repository or release qualification. Exact executed outcomes are recorded in the final validation artifacts. Do not substitute the number of test files for a verified test count.

Native self-tests and lifecycle replay are included in the earlier `native_integration.py --self-test` command. They execute real signature, replay, ledger and scope checks using synthetic identities/RPC responses. A passing test does not provision live authority or make scheduling admission valid; the current protected capsule boundary must continue to refuse unsupported scheduling scope.

## 7. Rebuild figures, browser edition and PDF

Use a disposable copy because these commands generate artifacts at their standard locations. To rebuild the published presentation from the original frozen outputs:

```bash
python src/build_report.py
python web/build_web.py --strict
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error enterprise-next-advantage.tex
```

`latexmk` runs the required LaTeX/BibTeX passes. The result is `paper/enterprise-next-advantage.pdf`. The strict browser builder refuses missing final report sections and inconsistent scenario/policy metadata. PDF metadata, font/toolchain behavior and creation times can vary across environments; inspect rendering as well as successful compilation.

If a new replay was written under `replay-output/`, the report builder still reads its documented standard `evidence/` paths. Rebuilding from a different replay requires an explicitly prepared copy of those inputs and should be labeled as that replay, not silently substituted into the published evidence.

## 8. What should reproduce, and what should differ

With the pinned numerical environment and unchanged seeds/source, expect the same problem definitions, learned parameter values, policy-content identities, objective values, acceptance decisions and fixed-seed economic decisions. Floating-point/solver behavior can vary with a changed toolchain; investigate any material difference instead of updating expected numbers.

Wall-clock measurements are not deterministic. Native journal/signature fixtures create fresh keys and timestamps, so their binary identities differ while the recorded control outcomes and reconciled amounts should agree. Newly generated artifacts will not match the delivered package manifest; retain the delivered manifest with the original copy and record a distinct manifest for a new edition.

Confidence intervals in the package describe variation within the declared numerical samples or simulated worlds. Replaying the software does not validate its real-market assumptions, demonstrate customer demand, establish a live frontier-model baseline, prove a global optimum or qualify a public deployment.
