# Public source-tree packaging note

This draft source tree contains the runnable implementation, author paper, summaries and exact archive index. The raw ZIP shards are delivered separately; a public release is not claimed. The complete user package retains original raw paths. To restore this source tree from the separate evidence handoff, run `python3 publication/extract_evidence.py --archive-root PATH_TO_EVIDENCE`. That directory must contain `evidence/archives/` matching the included index. Do this before original-raw analysis or a fresh run intended to repeat the full development exposure scan. The first browser mission and source verification work without these archives. The historical original ZIP and user DOCX are excluded from this public tree; section 8 needs the separately identified historical archive. The research instructions below retain their original scope.

---

# Reproduce the Strategy Succession edition

## 1. Use the first mission immediately

Open `browser/index.html` in a current browser and select **Plan this mission**. It needs no account, wallet, key, package installation or internet access. The complete offline HTML is also delivered separately as `AGI_ALPHA_Strategy_Laboratory.html`.

The first result is a fresh computational schedule for the editable nine-job release. It is checked against the input dependencies and worker calendar. Export the JSON evidence or CSV plan. A missed target remains visible. The first valid plan is useful without assuming that constructing another strategy will repay its cost.

**Build the next** starts one finite six-mission sequence. The controller selects subsequent permitted missions and phases automatically. **Inspect construction chain** is a separate diagnostic that may retain a correct but uneconomic method; it is labeled accordingly. STOP requests a checkpoint; an explicit resume rechecks saved history. Closing the tab stops computation. A checkpoint is saved state, not an operating service.

## 2. Verify the package and prospective source identity

From the extracted `AGI_ALPHA_Strategy_Succession` directory:

```sh
sha256sum -c SHA256SUMS.txt
python3 scripts/freeze_study.py
```

The first command checks packaged payload bytes. The second checks the frozen scientific sources, checker, configuration and registered analysis. It refuses modifications; do not regenerate a source manifest to present changed code as an old experiment. Presentation files and recorded results have separate hashes.

## 3. Pinned research environment

The executed environment is Node **24.22.1**, CPython **3.12.14**, NumPy **2.4.6** and SciPy **1.17.0**. Python standard-library code suffices for the separate checker. The native reference additionally uses NumPy and SciPy's bundled HiGHS. No model provider is called.

Create an isolated environment if these are not already present:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
node --version
python --version
```

`python3.12` must resolve to the pinned patch version for an exact environment match. Installing dependencies on another machine has its own network and administrative requirements; no virtual environment or installer cache is required by the browser. Hardware, operating system and load affect wall times. Primitive reference work and non-timing outputs have their own source identity; exact physical timing reproduction is not expected.

## 4. Run a bounded local stream

Use a new output directory:

```sh
node companion/run.mjs --out my-selective-stream --python python3
```

For the labeled diagnostic:

```sh
node companion/run.mjs --diagnostic --out my-construction-lab --python python3
```

This is one explicit process start followed by automatic phase selection. The process must remain alive to keep computing. It does not initialize or install the native AGI ALPHA operator, create role keys, submit contract work or start a daemon. The released workbench source is executed through its supported adapter seam.

To inspect interruption and recovery on the public demonstration inputs:

```sh
node companion/run.mjs --out my-recovery-run --python python3 --stop-after 1
node companion/run.mjs --out my-recovery-run --python python3 --resume
```

The second command restores accepted receipts and rechecks them. Exhausted budgets, expired authority or a wall deadline require a new explicitly bounded run; resume does not renew them. Raw outcomes, packs, checkpoints and high-water guards are preserved.

## 5. Rerun the frozen confirmatory procedure

The delivered original run is `results/confirmation-v1/`. Preserve it. A new output path identifies your reproduction:

```sh
node companion/experiment.mjs --confirm --out results/reproduction-01 --python python3
```

The launcher verifies both source manifests before materializing inputs. It creates the 12 paired 72-mission streams once; runs eight arms at three prespecified work limits; executes the separate four-treatment constructive diagnostic; evaluates the fixed 36-task native-specialist subset in both modes; and runs the registered analysis. All downstream phases advance from this one command. It refuses an existing output directory. The 120-second per-stream wall bound, work caps and checker/native response ceilings remain active.

The run writes `RUN_START.json`, `INPUT_REGISTRY.json`, `WORLD_GENERATION.json`, exact inputs, per-trial compressed raw output and workbench packs, checkpoints, ledgers, `trials.jsonl`, native records, `SUMMARY.json`, `ARM_RESULTS.csv` and `RUN_COMPLETE.json`. Later budgets reuse the same task set as sensitivity analyses, not independent replications. The first mission is included in the 72-offered-mission endpoint.

The primary contrast is flywheel minus conventional saved workflow at 1,000,000 units per stream. Its paired percentile bootstrap uses 12 complete streams, 10,000 resamples and seed 20261024. Other methods, budgets, diagnostic interventions and native comparisons are descriptive. Stopped streams remain in the denominator. New source changes or additional tuning require a distinct protocol and fresh confirmation, not a replacement of these results.

## 6. Operating checks and finite load

Use new output paths:

```sh
node companion/fault-tests.mjs development/my-operating-tests
node operations/load_probe.mjs --out operations/my-load-probe --python python3
```

The operating suite intentionally interrupts subprocesses and supplies invalid or stale state within its own isolated outputs. It performs no external action. The load probe offers batches of 1, 4, 16 and 64 tasks with at most four checker processes, fixed independent seeds and finite wall/work ceilings. Its throughput and latency are one local observation per batch, not sustained-service or production scaling evidence.

## 7. Recheck the separately frozen challenge probe

The main acceptance checker is `review/check.py`. Its source and independence statement are preserved. The seeded-defect challenge/regression experiment has its own `PROBE_PROTOCOL.json`, `PROBE_FREEZE.json`, execution record and raw outcomes. It is development diagnostic evidence, never part of protected main confirmation. Read `review/README.md` for its exact entry points and argument conventions. Conventional regressions with the same counterexamples are an equally enabled comparison.

## 8. Replay the recovered historical Strategy Laboratory

The untouched original archive is `history/originals/SUCCESSOR_Omega_Strategy_Lab_v0.1.0.zip`, SHA-256 `c0df2ac39ddcb32de672db93d05df77b8d8f683966cb92469ab00bf2060284a1`. Extract it into a new location. Use its recorded **CPython 3.13.5** runtime, not the new study's Python3.12 environment:

```sh
python3.13 -m omega verify --workspace evidence/example --replay
```

Run that command from the original extracted project directory. The current fresh replay passed all six attempts and 27,648 confirmation cases with exact non-timing equality. `history/current-exact-replay/` records command, runtime identity, timestamps, elapsed/CPU time and raw log. The separate `history/audit_original.py` rechecks stored artifacts and statistics. These are different checks. Neither re-executes development search as a new historical experiment; the earlier pilot remains preserved and its source-reported policy replay is not relabeled as a current one.

## 9. Rebuild browser and paper

```sh
python3 browser/build_demo.py
bash paper/build.sh
```

The browser builder is standard-library only and bundles the static module closure with a SHA-256 manifest. Normal builds reuse versioned mission fixtures; they do not regenerate them. Recorded evidence is explicitly labeled and does not simulate a live result.

The paper uses XeLaTeX/BibTeX from TeX Live2023, Latin Modern fonts and Matplotlib3.10.8. Figure inputs are copied in `paper/plot-data.json`; SVG text remains editable. The build fixes document metadata time and identity. The delivered PDF was rebuilt from the packaged LaTeX, rendered page by page and inspected. See the final verification docket for exact hashes and any document-serving metadata distinction.

## 10. Extend honestly

A benchmark promotion is a particular frozen score-gate decision. A forecast-based local research admission is not observed outside adoption. Recovery of the full research investment additionally needs acquisition, failures, checking, maintenance and attributable labor valued against realized benefits. Unknown costs remain unknown. No numerical result in this package is revenue, a token-price forecast, production authority or proof of self-acceleration.
