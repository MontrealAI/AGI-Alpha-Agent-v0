# Evidence and reproduction index

This is the complete 26 October 2026 research companion for **AGI ALPHA Flywheel: The Legal Work Advantage**. All case documents are original, clearly labeled synthetic material. The released annotations are included for independent reproduction after predictions were sealed; production and reusable capabilities do not read them.

## What to inspect

| Question | Authoritative companion records |
| --- | --- |
| What work was offered, to whom, and under which boundary? | `protocol/scope.json`; `protocol/reconciliation-scope.json`; `research/legal-scope/scope-and-offering.md`; `research/legal-scope/final-boundary-notes.md` |
| What did the external research actually measure? | `research/legal-scope/evidence.json`; paper sections on motivation and methods. Student assistance and task-specific results do not establish autonomous profitable delivery. |
| What existing system was used? | `heritage/alpha-source-manifest.json`; `heritage/alpha/`; `research/coordination-snapshot.json`; `src/native_packaging.mjs`; `reconciliation/package.mjs` |
| What was frozen before primary cases? | `protocol/production-freeze.json`; `evaluation/source-freeze.json`; `protocol/independent-corpus-plan.json`; `protocol/corpus-freeze.json` |
| Were predictions sealed before annotations were released? | `protocol/prediction-seal.json`; `protocol/key-release.json`; second-prototype equivalents prefixed `reconciliation-` |
| Where are all first-prototype attempts? | `evidence/primary/`; `evidence/stress/`; development and failure directories. Each fresh case has B/C1/C/D/T original outputs, HTML packets and native Workbench records. |
| What passed, failed or escalated? | `evidence/production-summary.json`; `evidence/independent-audit.json`; `evaluation/scorer.py`; `evaluation/audit_predictions.py` |
| Where are the narrower fresh packets? | `evidence/reconciliation/RECON-01/` through `RECON-12/`, each with `characters/` and `lines/`; `evidence/reconciliation-independent-audit.json` |
| What did the narrower checker establish? | `evaluation/RECONCILIATION_CHECK_PROTOCOL.md`; `evaluation/reconciliation_check.py`; `evaluation/audit_reconciliation.py`. It verifies exact text conservation and source binding, not legal interpretation or useful localization. |
| What was retained, and what did it improve? | `src/references.py`; `src/amendments.py`; `evidence/capability-history.json`; `evaluation/independent-source-review.json` |
| What failed during construction? | `history/`; `evaluation/history/`; `evaluation/development/`; `economics/history/model-v1/`; `graph/history/`; development evidence. Preserve these records when reproducing. |
| What does sharing or a graph add? | `graph/README.md`; `graph/catalog.json`; `graph/source-provenance.json`; `graph/results/selection-panel.json`; `graph/results/controls.json` |
| What costs are known and unknown? | `evidence/cost-accounting.json`; `economics/production-input.json`; `economics/reconciliation-production-input.json`; `economics/findings.md`; `economics/secondary-findings.md` |
| Can the simulation be audited? | `economics/parameters.json`; `economics/legal-market.mjs`; `economics/results/primary-v2/`; `evidence/economics-independent-audit.json`; `evaluation/audit_economics.mjs` |
| What supports the narrower price thresholds? | `economics/secondary-unit.mjs`; `economics/results/reconciliation/`; `evidence/reconciliation-economics-independent-audit.json` |
| What were the publication checks? | `publication/` contains independent claim reviews, final integrity and presentation receipts, lint findings and draft qualification limits. |
| Where are the usable presentation artifacts? | `paper/AGI_ALPHA_Legal_Work_Advantage.pdf`; matching `.tex`; `paper/figures/`; `demo/AGI_ALPHA_Legal_Work_Demo.html` |

The `private-keys` directory name records custody during the experiment. Its final distributed contents are public synthetic factual annotations, not client information, credentials or cryptographic private keys.

## Run production without changing the original evidence

Use the extracted companion root as the working directory. The recorded runtime was Python 3.12 and Node 24.22.1. Production and the economics use standard libraries; figure creation additionally uses Matplotlib, and paper compilation requires XeLaTeX and the named fonts. There are no paid API calls, credentials, blockchain transactions or installation steps in these commands.

```bash
python src/run_production.py --cohort primary --output replay/primary
node src/native_packaging.mjs replay/primary/packaging-manifest.json replay/primary/native-records.json
python src/run_production.py --cohort stress --output replay/stress
node src/native_packaging.mjs replay/stress/packaging-manifest.json replay/stress/native-records.json
python reconciliation/reconcile.py replay/reconciliation
node reconciliation/package.mjs replay/reconciliation/packaging-manifest.json replay/reconciliation/native-records.json
```

Use a new directory for each campaign; the production runners refuse overwriting. The separate Python then Node sequence is deliberate. The attempted subprocess callback was blocked and remains in `history/failures/`; it was not bypassed. Portable Workbench execution retains `HOLD`, empty active authority, unfunded job descriptions and `NOT_CONNECTED` settlement. The signed-operator Harness, Fleet, live Jobs/Manager and authenticated agent admission were not provisioned or executed.

A replay checks reproducibility. It is not a new independent case, a new customer, a new acceptance observation or a fresh confirmation cohort. Times can vary between machines; original measured times remain in the sealed records.

## Audit the original frozen outputs

Create a new `replay` directory if it does not already exist. These commands read the original sealed outputs and write separate audit records:

```bash
mkdir -p replay
python evaluation/audit_predictions.py --output replay/primary-and-stress-audit.json
python evaluation/audit_reconciliation.py \
  --corpus protocol/reconciliation-corpus-freeze.json \
  --seal protocol/reconciliation-prediction-seal.json \
  --seal-sha256 6e048513e1b4773e0651bf22ed8aee1c407a16302d97757434681e76c15ed5d0 \
  --release protocol/reconciliation-key-release.json \
  --evidence evidence/reconciliation \
  --output replay/reconciliation-audit.json \
  --economic-input replay/reconciliation-production-input.json
```

The first supplementary audit defaults to B/C1/C/D. Add `--arms B C1 C D T` to check transfer outputs as well. Do not redirect either audit into the original frozen result paths. Output timestamps and scoring duration can differ while factual decisions remain the same.

## Reproduce the conditional economics

```bash
node economics/legal-market.test.mjs
node economics/legal-market.mjs economics/production-input.json replay/economics 24
node economics/secondary-unit.mjs economics/reconciliation-production-input.json replay/reconciliation-economics
```

The first command checks the corrected model's behavioral controls. The campaign uses nine declared scenarios, 24 paired worlds per scenario and five strategies, for 1,080 outcomes. Seed funding, reserve, collection delay, declining buyers, failures, professional review, acquisition, onboarding, support, maintenance and finite capability lifetime are explicit. The canonical accounting modules are unchanged. `economics/README.md` is a frozen earlier source document; its older example input `evidence/economics-input.json` is superseded by the exact path above. No frozen source was edited merely to improve documentation.

All 1,080 simulated outcomes were cash-negative and neither investment was funded in any of the 216 worlds. The simulation is calibrated to actual attempt counts, technical outcomes and local stage runtimes only. Demand, prices, task minutes, professional acceptance, commercial-tool effectiveness and actual full dollar costs remain unobserved. Buyer perceived quality remains an optimistic 0.95 conditional assumption; it is not the observed 2/24 technical reliability. Do not treat the distributions as empirical market confidence intervals.

The original invalid economic model is retained in `economics/history/model-v1/`: it could invoice a rejected technical packet after hypothetical correction. The separately frozen corrected model blocks that behavior. Its surviving descriptive-text and cent-rounding discrepancies are documented in `economics/results/primary-v2/reporting-errata.json`, the findings and paper; do not silently substitute invalid results or convert a hypothetical correction into accepted production.

## Graph and freshness replay

`graph/legal-graph.mjs measure` writes its fixed result path. To avoid replacing original evidence, copy the complete companion to a separate reproduction directory before running:

```bash
node graph/legal-graph.mjs measure
```

Do not rebuild the catalog while claiming to reproduce its frozen identity. The distributed two-asset catalog and dependency evidence are identical for registry and graph. Direct retention performs different root checks and is not a fair graph-performance winner. The 21 change/admission refusals use explicit research fixtures; they do not prove live ENS authentication, professional expertise, actual changed-law correctness or deployed contract compatibility. The historical attestation is insufficient after scope, dependency, playbook, epoch or lifecycle change.

## Rebuild the demonstration and paper

```bash
python demo/build_demo.py
python paper/build_figures.py
cd paper
xelatex -interaction=nonstopmode -halt-on-error AGI_ALPHA_Legal_Work_Advantage.tex
xelatex -interaction=nonstopmode -halt-on-error AGI_ALPHA_Legal_Work_Advantage.tex
```

The offline HTML embeds all 24 fresh reconciliation packets and the declared threshold grid. It has English and French explanations, keeps the actual English source text, and makes no network request. Its original QA checks structure, JavaScript syntax and evidence bindings; browser-rendered visual acceptance was unavailable and is not claimed. The 14-page PDF was rendered and visually inspected. Compilers can change PDF metadata and binary hashes; scientific source/results remain separately bound.

## Cost and conclusion discipline

CAD 0 collections does not mean CAD 0 cost, nor zero operating loss. Actual marginal, recurring, fully allocated and historical costs and actual available surplus remain unknown where metering or review evidence is absent. The cost ledger lists those gaps explicitly. Scenario construction cost is charged once, includes a failed-attempt allowance, and remains separate from unknown historical research cost. Token issuance or appreciation contributes nothing.

Professional review was retained rather than removed to create profitability. The supported disposition is **research-only / no commercial launch on this evidence**. A useful retained component, a technically complete comparison, a cheaper accepted legal deliverable and a self-financing sequence are different claims. This experiment supports the first two in bounded forms and establishes neither of the latter two.

## Integrity and rights

`MANIFEST.sha256.json` inside the complete ZIP binds every distributed member except that manifest itself. The ZIP's own hash belongs in the external delivery receipt to avoid circular hashing. `publication/build_companion.py` makes the archive deterministically from the selected source files. Generated caches, transient TeX intermediates and replay directories are not evidence and are excluded; recorded failed attempts, raw original packets, released keys and source histories are included.

Original code and synthetic text are Apache-2.0. Imported code retains the exact upstream license and provenance in `heritage/`, `economics/inherited-manifest.json` and `graph/source-provenance.json`. Cited third-party articles and official websites are not redistributed as the product. All human-professional and commercial acceptance fields remain unassessed. Draft publication and repository qualification status are separate from the immutable experimental record.
