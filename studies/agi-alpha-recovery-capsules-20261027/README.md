# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity
## Recovery Capsules: Making Stranded Analysis Usable

Vincent Boucher — President of MONTREAL.AI

This research edition delivers six analytical recovery packages, including four prospective confirmation jobs that pass all 133 code cells and 38 independently specified numerical/semantic checks on two clean runs. The central commercial model yields USD36,309.01 after additional setup, conditional on USD900 per accepted outcome, eight attempted orders monthly and 85% final acceptance. There are no customers, sales or actual collections; actual complete study cost is unknown.

The cases are MIT-licensed historical teaching code with a free updated edition. They are engineering analogues. The proposed paying market is customer-specific legacy analysis without an equivalent replacement. These cases do not estimate that market's demand or paid acceptance.

## Read the edition

- `publication/paper.pdf`: complete LaTeX research paper.
- `publication/browser-edition.html`: complete offline browser edition of the same manuscript, embedded figures and MathML.
- `publication/executive-brief.pdf`: two-page commercial executive brief.
- `publication/paper.tex`, `body.tex`, `references.bib`: compilable publication source.
- `publication/linkedin_draft.txt`: approval draft, not posted.
- `PUBLICATION_STATUS.json`: exact review-publication status, not a production-release claim.

## Reproduce

Use Python 3.12 and the exact installed versions listed in `requirements.txt` / `environment.json`. The original execution environment already had these dependencies. A new clean installation, an offline wheelhouse and other operating systems were not tested. Native provenance replay additionally uses the supplied Node installation and Pydantic; see `scripts/NATIVE_REUSE.md`.

From this directory:

```bash
python scripts/reproduce.py
```

This validates identities, executes the original failure baselines, runs every delivered notebook in a new process, applies independent checks, exercises adverse controls, regenerates the economics and verifies native provenance/plan components. Outputs go to `reproduction/`, including isolated native replay evidence; supplied original evidence remains under `evidence/`. The initial complete replay and the subsequent focused output-isolation correction are both recorded. The final complete replay is evidence/full-reproduction-final/report.json; superseded pre-correction evidence is explicitly retained in the plot-lifecycle-before-correction directory. The process uses local data and installed dependencies without model calls, customer accounts, credentials or runtime network access. New dependency installation, if needed, is a separate local setup action.

Economic computation alone uses the Python standard library:

```bash
python economics/run_economics.py
```

The published research recipes reconstruct the fixed repairs:

```bash
python scripts/build_capsules.py
python scripts/build_confirmation.py
```

Those are deterministic recipes for this executed study, not a general autonomous notebook-repair system. They do not demonstrate a new model, a learned policy or a customer-facing production service. Rebuilding identical inputs should preserve notebook content; run full reproduction and renew evidence bindings after any substantive modification.

To inspect one confirmation capsule:

```bash
python scripts/independent_run.py deliveries/03.02-Data-Indexing-and-Selection/recovered.ipynb --case 03.02-Data-Indexing-and-Selection --checks scripts/independent_checks.py --output indexing-acceptance.json
```

Execute only the audited supplied notebooks or separately authorized inputs. The study runner is not a universal security boundary for arbitrary uploaded code. Runtime networking is disallowed; the managed research environment provides an additional isolation boundary.

## Compile the paper

In `publication/`, run:

```bash
pdflatex -interaction=nonstopmode -halt-on-error paper.tex
bibtex paper
pdflatex -interaction=nonstopmode -halt-on-error paper.tex
pdflatex -interaction=nonstopmode -halt-on-error paper.tex
pdflatex -interaction=nonstopmode -halt-on-error executive-brief.tex
```

The paper uses standard TeX Live packages and supplied PDF figures. `scripts/make_figures.py` regenerates figures from frozen results. `scripts/build_browser.py` uses Pandoc 3.1.3 and beautifulsoup4 (see publication-requirements.txt) to build the full HTML edition from the same LaTeX body and bibliography. Optional responsive rendering also uses Playwright 1.54.0 and Chromium 139.0.7258.5; the finished HTML itself has no external runtime dependencies.

## Package contents and evidence

- `protocol.json` and development freeze: the offer, acceptance rules, case queue, budget and chronology.
- `inputs/`: code-only source extracts, source identities, data provenance and license notices.
- `deliveries/`: six complete recovered notebooks, change records, identity records and handoff instructions.
- `scripts/`: producer runner, independent numerical checker/runner, integrity audit, adverse controls and reproduction.
- `evidence/`: original failures, corrections, two independent confirmation reruns, economic review and native execution.
- `economics/`: frozen assumptions, executable scenarios, sixteen cash ledgers, 1,001-cell grid, sensitivities and preserved prior version.
- `upstream/`: 26 byte-exact AGI ALPHA files and original licenses; no replacement infrastructure.
- `figures/`, `publication/`: scientific figures and all publication outputs.

The current Iris CSV is a pinned same-source seaborn snapshot, not proven identical to a 2016 download. The code repairs preserve documented computational intent within the tested environment, not every historical floating-point output or scientific conclusion. All 84 hyperparameter settings and seven folds are retained; the bounded normalization adapter is not the complete scikit-learn estimator API.

## Economic boundaries

At the central case, operating/full-project break-even prices are USD390.73/USD441.26. Final acceptance must exceed 44.99% to repay modeled setup at central demand/cost. A joint downside loses USD28,943.02. A funded campaign with no sales loses USD26,800. Expected-case opening equity is USD6,760.92, rising to USD10,298.12 if the first cohort is entirely refunded and later months recover. Open-warranty customer funds are restricted, never unrestricted financing.

Documented API prices support a prospective deployment scenario. Actual billed tokens, model-call configuration and complete allocated study expense are not available. Native accounting retains unknown amounts as unknown; simulated earnings are not promoted into actual receipts. No live ENS, wallet, token transaction, MARK admission or production service is claimed.

## Rights and publication

Original notebook code: MIT, Copyright (c) 2016 Jacob VanderPlas; the complete notice is included. Original book prose and stored figures are excluded. Iris data attribution: Fisher (1936), UCI DOI 10.24432/C56C76, CC BY 4.0, with explicit seaborn snapshot provenance. Newly authored study source follows repository Apache-2.0 unless an original file retains another license. Unchanged upstream files retain their own notices.

This is an additive pinned research review edition under the repository's existing `PAPER_UPLOADS.md` route. It does not modify the runtime, catalog, homepage, workflows, release version or other owners' branches. Canonical merge/publication remains subject to the existing source qualification and publisher ownership.

## Repository formatting correction

The initial pinned content at f018e123da555f5cef7b36ef85ba24ed5e65fc14 passed the study and hosted smoke checks, but Ruff reported compound-statement formatting. The current scripts have exactly equivalent Python ASTs and pass the unchanged repository Ruff configuration. Original before-source bytes are retained as text evidence, including the historical failed scripts; separately labeled historical .py reading copies are formatting-only derivatives. The entire study was replayed, all 23 economic outputs and all 38 numerical checks remain identical, and the 16 native confirmation PNG hashes also match. See evidence/lint-formatting-correction/correction.json. The frozen numerical checker, notebook bytes, manuscript, PDFs, browser edition, assumptions and economic results are unchanged.
