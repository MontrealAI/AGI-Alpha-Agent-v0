> **Compact source-review draft.** This repository tree contains the frozen methods, shareable task inputs, original execution sources, raw aggregate receipts, economic models and editable publication sources. The complete companion also contains every repeated raw output and compiled PDF/ZIP assets; those binaries remain outside this source-only draft under the existing publication-owner process. Links and full saved-output audit commands below describe the complete companion. Use the isolated reproduction wrapper to create a new complete replication from this source tree. This draft is not a merged release or hosted website.

# AGI ALPHA FLYWHEEL — The Economics of Autonomous Work

**Research edition 1.0 · 25 October 2026**

Final paper: **20 pages**, two byte-identical clean builds, zero TeX warnings,
SHA-256 `8b9df6f5ef1887d6f972ccfbe26d61a5551962dea41ad7c6595d431dfacb2f51`.
The build record is [verification/CLEAN_BUILD.json](verification/CLEAN_BUILD.json);
separate page-inspection records cover all 20 pages.

This companion makes the employer's decision inspectable: obtain a complete useful
digital deliverable, know what was accepted and how long the measured process took,
see what human responsibility remains, and retain an executable capability for the
next job. The tested work is exact tabular reconciliation and descriptive exception
reporting. It does not represent an entire salaried role.

## Start here

| Deliverable | Location |
|---|---|
| Compiled paper | [paper/main.pdf](paper/main.pdf) |
| Complete editable LaTeX and bibliography | [paper/main.tex](paper/main.tex), [paper/references.bib](paper/references.bib), [paper/foundations.bib](paper/foundations.bib), [paper/historical.bib](paper/historical.bib) |
| Offline working browser companion | [browser/AGI_ALPHA_Work_Economics_Demo.html](browser/AGI_ALPHA_Work_Economics_Demo.html) |
| The first accepted public-source job | [raw/showcase/delivery.zip](raw/showcase/delivery.zip), [brief](raw/showcase/brief.json), [acceptance](raw/showcase/acceptance.json), [receipt](raw/showcase/receipt.json) |
| Retained executable successor | [raw/showcase/output/successor-tool.mjs](raw/showcase/output/successor-tool.mjs) |
| Recorded analysis | [raw/ANALYSIS.json](raw/ANALYSIS.json) |
| Actual resource and missing-cost ledger | [COST_LEDGER.json](COST_LEDGER.json) |
| Interventions, failures, and expected refusals | [INTERVENTION_LEDGER.json](INTERVENTION_LEDGER.json) |
| Frozen design and identity boundary | [protocol/STUDY_PROTOCOL.md](protocol/STUDY_PROTOCOL.md), [protocol/FREEZE.json](protocol/FREEZE.json), [protocol/FREEZE.sha256](protocol/FREEZE.sha256) |
| Independent-role saved-output review | [verification/independent_review.json](verification/independent_review.json) |

The first job reconciles 135 public tracked website-asset paths in each of two
repository snapshots and preserves 16 changed Git-blob identities. Its recorded
worker interval was about 0.276 seconds, including execution, independent-role
machine acceptance, hashes, and packaging. The source owner still determines whether
each change should be approved. The job does not inspect deployed website behavior.
The complete source-backed record is in the linked brief, receipt, and acceptance.

## What the measurements establish

| Question | Evidence and limit |
|---|---|
| Quality | 36/36 predeclared controlled jobs passed the frozen deterministic acceptance criteria. The selected public job and composed successor also passed their separate checks. Acceptance is independent-role software checking, not a blinded human/customer assessment. |
| Speed | Primary median process turnaround was about 0.301 seconds, including child execution, acceptance, packaging, worker receipt serialization, and process exit. Intake, research authoring, and employer attention are outside this interval. Worker-window and CPU counters exclude the final receipt serialization tail; outer process turnaround includes it. |
| Capacity | 108 operating attempts repeated 12 inputs in nine finite batches. Median accepted throughput was approximately 132, 212, and 332 deliveries/minute at 1, 2, and 4 local processes on the recorded host. These are local load observations, not a continuous-service guarantee or 108 fresh reliability cases. |
| Cost | Operational model-call count was zero on the deterministic route. Actual host invoices, authoring, setup, supervision, human review, maintenance, and investment allocation were unmetered. Complete actual cost remains **unknown**. |
| Attention | No human stopwatch observations were made. Configured review capacity is not observed review time. Remaining employer attention is an explicit economic assumption. |
| Reuse | The same byte-identified retained executable ran on fresh task paths and changed schemas. A successor aggregated evidence from 37 accepted parent outputs. Existing algorithms and adapters supplied the mechanisms; increasing improvement rate was not demonstrated. |

All values are traceable to [raw/ANALYSIS.json](raw/ANALYSIS.json) and the original
receipts. Controlled synthetic examples establish this bounded workflow; the four
domain presentations do not establish four independent general capabilities.

**The new empirical human comparison is NOT RUN.** The traditional baseline permits
competent workers to use ordinary spreadsheets, SQL, macros, scripts, and retained
templates. This edition uses published compensation and adjacent historical human
evidence with clearly labeled time, attention, reliability, and allocation
assumptions. Those sources do not supply observed completion times for these exact
jobs. See [economics/HUMAN_MARKET_BENCHMARK.md](economics/HUMAN_MARKET_BENCHMARK.md),
[protocol/HISTORICAL_HUMAN_EVIDENCE.md](protocol/HISTORICAL_HUMAN_EVIDENCE.md), and
[economics_post/measured_resource_economics.json](economics_post/measured_resource_economics.json).
The latter presentation was constructed after execution and is explicitly marked
postfreeze. Freed employee attention is capacity; realized cash savings require an
actual spending change. Wages, GDP, addressable expenditure, customer savings, and
provider revenue remain distinct. The $40 trillion thesis is an illustrative
scenario, not a measured market estimate from this portfolio.

## Frozen source and execution environment

The repository snapshot is
[`f836f06e8351e64db1da770e16e304b5feb01f28`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/f836f06e8351e64db1da770e16e304b5feb01f28).
The exercised execution modules match release v1.43.0, commit
`5499495911bf8822ac0aa8c9007f00789c1132b5`. The snapshot contains some later package
metadata, so it is not presented as an installed release wheel. The source inventory
and the four-repository/five-contract inspection boundaries are in
[protocol/SOURCE_AUDIT.md](protocol/SOURCE_AUDIT.md) and
[protocol/UPSTREAM_SOURCE_MANIFEST.json](protocol/UPSTREAM_SOURCE_MANIFEST.json).

The frozen protocol identity is:

```text
41b8b56a39993e29dc313faa8633e36abd910872ab43e9a5dbe1ab2edc589407
```

The closest reference environment is Linux x86_64, Python **3.12.14**, Node.js
**24.22.1**, Pydantic **2.13.5**, and cryptography **50.0.1**. The Python imports need
Pydantic and cryptography even though the measured route does not initialize a
Journal or signing identity. Reconciliation and controls use local ES modules;
there is no npm install step. Python's CSV, SQLite, statistics, and other standard
libraries provide the study evaluator and orchestration. The descriptive successor
uses the released pure `workbench.invoke`/`write_artifacts` route.

Optional figure builds use matplotlib **3.10.8** and NumPy **2.4.6**. Paper builds use
latexmk, pdfLaTeX, BibTeX, and the packages listed in
[reproduction/REFERENCE_ENVIRONMENT.json](reproduction/REFERENCE_ENVIRONMENT.json).
Browser QA used Python Playwright **1.64.1** with an existing Chromium headless shell;
the offline HTML itself needs only a modern browser. No script installs, upgrades,
or downloads dependencies. Other versions are not presumed equivalent.

## Audit the saved evidence without rerunning jobs

Run from the companion root:

```sh
python3 reproduction/audit_saved.py --freeze-only
python3 reproduction/audit_saved.py --hashes-only
python3 reproduction/audit_saved.py
```

The first command verifies the public freeze and every frozen file. The second also
checks output manifests, exact ZIP members, retained-tool identities, controls,
receipts, and successor lineage. The full command additionally recomputes expected
answers using the independent Python CSV/SQLite acceptance oracle. It does **not**
run the producing tool, model, controls, or load campaign and writes no files; its
JSON report goes to standard output. A nonzero exit preserves a visible finding.

The original `verification/audit_saved_results.py` is also supplied as provenance,
but its main function writes `verification/independent_review.json`; use the new
read-only command when preserving the supplied edition.

## Reproduce the measured sequence in a new directory

The wrapper refuses any existing destination and refuses a destination within or
containing the original companion. Choose a new sibling or external directory whose
parent already exists:

```sh
python3 reproduction/reproduce.py --destination ../work_economics_replication
```

To inspect a concrete copy and command plan without running any work:

```sh
python3 reproduction/reproduce.py --destination ../work_economics_plan --prepare-only
```

`--prepare-only` runs no task generator, useful job, control, scale trial, or analysis.
Use another new destination for execution; the prepared directory is not overwritten
or silently resumed. The wrapper copies and verifies the frozen source, protocols,
public inventories, and economic assumptions. Existing observations are left in the
original directory. `REPRODUCTION.json` records the new environment, source identity,
command plan, timings, exits, and any failure; detailed logs remain in the new
`reproduction-logs/` directory.

The actual execution sequence is:

```sh
python3 src/prepare_public_task.py
python3 src/generate_tasks.py --phase confirmation --out raw/tasks
python3 src/run_job.py --task raw/public-task --out raw/showcase
python3 src/run_campaign.py --mode primary --tasks raw/tasks --out raw/primary --parent raw/showcase/output/successor-tool.mjs
python3 src/successor_report.py
node src/controls.mjs --out raw/controls
python3 src/run_campaign.py --mode scale --tasks raw/tasks --out raw/scale --parent raw/showcase/output/successor-tool.mjs
python3 src/analyse.py
```

These direct commands belong **only inside the newly prepared execution tree**.
The generator's literal `confirmation` flag reproduces the original fixed-seed
portfolio (seed `2026102501`); a later rerun is a replication of those same inputs,
not another fresh independent held-out study. The public task is regenerated from
the frozen GitHub inventories, so no live network lookup changes its inputs.
There are 36 primary jobs, one selected public job, one composed successor, eight
controls, and 108 load attempts. Dependent stages stop visibly if a stage fails;
already written attempts and logs are retained. The original campaign runner counts
failed attempts and keeps missing CPU as null.

The common employer deadline is eight hours. The system worker's 30-second execution
cap and the outer 35-second guard are operating bounds; they are not a 30-second
human benchmark. These finite local processes require an active execution process.
The browser demo runs only while its page is active. Nothing in this companion
creates a daemon, cloud worker, or service that survives closing its execution
environment. The tested STOP/recovery/budget/rollback scope is documented in
[protocol/PROTOCOL_CONTROLS.md](protocol/PROTOCOL_CONTROLS.md).

## Use the actual retained tool on another eligible job

With existing Node.js, fresh authorized CSV files, and a new output directory:

```sh
node raw/showcase/output/successor-tool.mjs first.csv second.csv firstKey secondKey NEW-output-directory
```

The tool emits joined/unmatched/conflict CSVs, exact JSON, and comparison evidence.
Its internal methods are existing implementations; the study does not claim that
every component was newly invented. Exact string keys, duplicate Cartesian pairs,
shared-field scope, and original input bounds apply. Missing keys are refused.
Choosing authoritative source values and authorizing any update remain with the
responsible person. To obtain the study's extended grouped-action package and its
independent machine checks, use the complete `run_job.py` workflow and task brief.

## Rebuild the recorded paper and browser companion

The build wrapper copies the original recorded edition into a new tree, regenerates
the four editable SVG/PDF/PNG figures and economic rows, rebuilds table macros,
compiles the paper, and bundles the offline browser:

```sh
python3 reproduction/rebuild_publication.py --destination ../work_economics_publication_build
```

Use `--prepare-only` for a source copy without running builds, or `--browser-only` to
skip figures and TeX. It performs no new experiment. From the new build tree, the
underlying commands are `python3 figures/make_figures.py`, then
`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` from its `paper/`
directory, and `python3 browser/build_demo.py` from the new companion root. The
wrapper preserves the existing `table-data.tex` macro structure while refreshing
the three row sets; directly injecting row files inside `tabularx` failed during
development and that failure remains in the ledger.

Paper prose and some signature captions describe the original recorded observations;
they are not automatically rewritten for a new replication's timing. Rebuilding the
recorded edition can change PDF/HTML bytes because of tool versions or generated
timestamps. Check its new hashes, render **every** PDF page with `pdftoppm`, inspect
layout and references, and run `python3 browser/qa_demo.py` in that new tree before
publication. The provided visual/QA records apply to the delivered edition only.

The supplied `verification/verify_clean_build.py` performs two fresh temporary
latexmk builds, compares PDF bytes, renders every page, and validates the PNGs. It
also writes build logs, the canonical PDF, page images, and its verification report
under its current companion root, so run it **in the new publication-build tree**
when preserving this edition. It needs PyMuPDF (`fitz`) and Pillow in addition to
TeX. Its rendered-image verification does not replace visual inspection. The
publication-development ledger preserves the earlier truncated-figure failure that
motivated buffered, validated atomic figure output.

## Cost, interventions, failure preservation, and publication

`COST_LEDGER.json` enumerates every available unique receipt plus development,
control, and shared construction categories. Nested stage observations are not
summed a second time. Study resource totals keep primary cases, public showcase,
successor composition, and repeated load work distinct. All missing invoices,
authoring/setup/review/maintenance allocations and complete costs remain null.
The injected timeout's mock interval is not relabeled as 35 seconds of actual work.

`INTERVENTION_LEDGER.json` preserves the development generator failure, five
prefreeze review corrections, deliberate corruption/timeout probes, eight control
cases and expected refusals, browser build/test-harness failures, saved-output
auditor correction, and publication build failures. The measured batch-intervention
field is narrower than total project labor. Whole-session intervention count and
human attention were not continuously instrumented and remain unknown.

To reconstruct these ledgers from the supplied records without rerunning work:

```sh
python3 reproduction/build_ledgers.py --check
python3 reproduction/build_ledgers.py
```

The first command prints counts only; the second writes the two top-level derived
ledgers. Development attempts remain in `development/`, browser construction records
in `browser/BUILD_ATTEMPTS.jsonl`, and original verification/build logs in their
respective directories. Previous editions and negative studies are preserved by the
additive publication approach.

Coordination is tracked in
[repository issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850).
Prepared, reviewed, merged, and publicly verified states are distinct. This local
companion and its reproduction/build scripts do not publish a repository, website,
participant dataset, or deployed contract. Contract/source inspection, unsigned
drafts, simulations, and executed financial transactions are not interchangeable;
the measured route made no live settlement and required no wallet or provider key.
