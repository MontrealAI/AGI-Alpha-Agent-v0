# AGI ALPHA: The Advantage You Can Build

**Constructive Foresight for the Intelligence Transition — Writer 9**

**Finding:** the reusable numerical capability works, and frozen local timing forecasts have skill. The study does **not** establish a unique full-cost advantage for constructive foresight over an equally informed, equally capable alternative. This is a bounded scientific result, not a customer-adoption or investment claim.

## What is measured

Four fixed public sparse matrices, three right-hand-side counts, three methods and twelve held-out blocks produce **432/432 qualifying batches and 3,024 qualifying manufactured right-hand sides**. At 16 right-hand sides, certified reuse is about **7.0–13.6 times faster than repeated factorization**. Conventional cached LU already explains that benefit. Added certification has paired median time ratios of **1.01–1.44** relative to that strong baseline.

The preregistered primary local deadline gives **Brier 0.07205556 versus 0.25997074** for the pooled calibration-only constant, across **720 correlated outcomes**. The secondary all-deadline aggregate is 0.03146296 versus 0.24237301 across 2,160 outcomes. Ready-stage forecasts condition on factors **and manufactured RHS already available**; preparation remains in full-batch cost.

The finite timing experiment retains **32,256 policy rows in 4,608 paired simulated worlds**. Its locked comparator was selected on calibration only. The nominal constructive-foresight increment is **+0.025667 assumed mission credits per episode**, with a 95% paired seed-block interval **[−0.038950,+0.127277]**. Reversed signals produce **−0.062780 [−0.121571,−0.006446]**. A compiled conventional policy makes the same choices in all 4,608 worlds with lower mean controller cost in every regime. These are model credits, not currency, CPU totals, customer demand or revenue.

The native integration performs initial construction and actual refactorization after knowledge-only restore. Fresh numerical proof and a separate explicit public-fixture grant are required. Eight native refusal controls and six receiver refusals pass. The full process consumes **6.552 seconds wall / 6.427 seconds child CPU**; its substantial orchestration cost is retained.

## Start here

- `paper/paper.pdf`: canonical rendered paper when distributed in the completed archive.
- `paper/paper.tex`, `paper/references.bib`, `paper/figures/`: complete publication source.
- `protocol.json`, `decision_protocol.json`, `amendments/`: frozen design, information boundaries and corrections.
- `results/`: original observations, calibration, forecasts and derived summaries.
- `data/ATTRIBUTION.md`, `data/source_provenance.json`, `data/manifest.json`: exact public inputs and licensing.
- `evidence/`: audits, source pins, native receipts, controls, failure records and cost records.
- `COST_LEDGER.json` / `COST_LEDGER.md`: measured and unknown costs, without double counting.
- `SYSTEM_INTEGRATION.md`, `vendored/SOURCES.json`: exact published components and lifecycle boundaries.
- `publication/`: passive paper/source handoff, separate from deployment acceptance.
- `MANIFEST.json` in the complete archive: every payload's byte count and SHA-256.

No external beneficiary acceptance, payment, firm offer or willingness-to-pay evidence was obtained. Authoring inference, human review, maintenance and opportunity cost remain unknown. The $15 quadrillion project figure is an editable illustrative envelope, not verified wealth, TAM, a forecast or token valuation. Its twelve sector weights allocate an assumed total under a default twenty-year macro scenario. It is not used to compute this experiment's outcome.

## Environment

Observed Python: 3.12.14. The numerical and figure versions are pinned in `requirements.txt`. The native bridge also needs Node.js (the observed version appears in the integration records). Use an existing permitted environment or a disposable virtual environment. Installing packages can require network access; no paid infrastructure or credential is needed. The packaged matrix inputs make numerical execution offline.

```bash
python3 -m venv /tmp/writer9-venv
/tmp/writer9-venv/bin/python -m pip install -r requirements.txt
```

The canonical paper build needs XeLaTeX, latexmk, BibTeX, P052, Nimbus Sans and DejaVu Sans Mono. TeX Live and URW fonts provide these in the measured environment. It does not execute the scientific experiment:

```bash
bash build_paper.sh
```

The flattened top-level TeX download is a convenience entry point. Compile it with the supplied `figures/` directory beside it, or use `paper/paper.tex` from the complete archive. It is not an embedded-figure single-file source.

## Audit the retained study without rerunning it

Run these from this directory, writing new reports outside the original evidence paths:

```bash
python3 check_results.py --phase confirmation --output /tmp/writer9-numerical-audit.json
python3 check_decision.py \
  --observations results/decision-confirmation/decision_observations.csv.gz \
  --summary results/decision-confirmation/decision_summary.json \
  --training results/decision-calibration/decision_training.json \
  --freeze results/decision-calibration/decision_freeze.json \
  --primitives results/primitives.json \
  --invocation evidence/decision-confirmation-invocation.json \
  --output /tmp/writer9-decision-audit.json
```

The numerical checker independently recomputes 24 saved solution columns; other columns retain their original logged acceptance metrics. It does not claim to independently recompute all 3,024 full solution vectors. The decision checker independently rederives choices, probabilities, VOI, arithmetic and intervals from frozen tables. Exact first-qualified completion timestamps were not separately retained, so event auditing is bounded by the available times. Neither checker is independent institutional review.

The retained numerical negative controls, native refusal probes, development failures and later audit reports are labeled by evidence class and timing. A successful functional control is not an additional confirmatory sample.

## Run a fresh numerical replication

Original source hashes and observations are immutable research evidence. Do not overwrite `results/` or refresh the original forecast timestamps. Prepare a separate tree:

```bash
python3 reproduce.py /tmp/writer9-fresh-replication
cd /tmp/writer9-fresh-replication
python3 numerics.py development
python3 numerics.py calibration
python3 numerics.py freeze
python3 numerics.py confirmation
python3 analyze.py
```

The new freeze requires confirmation to start within its own declared window. All 180 forecasts must be issued before confirmation. Reproduction should preserve the four matrix identities, every failure and all planned cells. The original study uses a 300-second wall bound per numerical phase and a 1,800-CPU-second budget for declared experimental runs; an exhausted budget records unexecuted cells. Authoring and other tool activity are outside this incompletely metered experiment ledger.

The original development run finished all 36 numerical cells but failed while serializing metadata. Its raw rows and CPU lower bound are retained. The fixed frozen source used for calibration and confirmation avoids that metadata defect; a new development run can therefore finish normally without reproducing the original logging error.

## Run a fresh timing-model replication

Use the newly produced `results/primitives.json` in the isolated tree. Paths below are relative there:

```bash
python3 decision.py --phase calibrate --primitives results/primitives.json --output results/decision-calibration
python3 decision.py --phase freeze --primitives results/primitives.json \
  --training results/decision-calibration/decision_training.json --output results/decision-calibration
python3 decision.py --phase confirm --primitives results/primitives.json \
  --training results/decision-calibration/decision_training.json \
  --freeze results/decision-calibration/decision_freeze.json --output results/decision-confirmation
python3 analyze_decisions.py
```

Archive and reopen the new preconfirmation freeze before the final command if claiming a prospective replication. `run_logged.py` can bracket the child process externally and record source/input hashes before launch. Give it a new `--record` path and absolute input paths for complete input binding. Runtime measurements vary with hardware and scheduling; expected numerical results should meet the unchanged acceptance rule.

Six regimes are fixed in `decision_protocol.json`. The signal, adoption, competitive arrival, imitation, request count, expiry, cost rate and amortization are assumptions. The model replays measured wall-time primitives rather than executing a physical customer workflow. It never exposes future sampled service durations to a deployable policy. Admitted late work is paid and is not accepted. The perfect-future menu is an upper reference, not an eligible competitor.

## Run the bounded native lifecycle demonstration

From the original research tree, use a **new** output directory:

```bash
python3 demo_harness.py /tmp/writer9-native-replication
```

This runs the packaged unchanged published Alpha dispatcher, Jobs MissionPack operations and zero-cap Manager/Jobs receivers. It uses the **public RFC 8032 TEST 1 keypair**, with credential generators prohibited. Role labels share a public test identity and do not prove authentication or institutional independence. The fixture executes trusted installed local computation; the word “sandbox” in native APIs is not an OS-isolation claim.

Manager's USDC6 and Jobs' AGIALPHA18 routes are distinct, unsubmitted, unfunded local handoffs with no authority and no settlement connection. Fleet's custom numerical worker was not provisioned or executed. The five Ascension contracts were source-inspected; this mission needs no transaction. No local-EVM test or fresh mainnet-state verification is claimed.

## Source and publication boundary

The experiment pins Alpha `dfc79c4ae81ac612cbff9865a0af8389b6ff3de9`, Manager `c5958eae872458c2f3cac48fea0b4bbfadc6ac6c`, Jobs `9983478d42c32fe399f28dd9b0e0173f904b8a11`, and Fleet `45759fb096faf8988f58ae5ea71248d0f35a97c7`. The exact unchanged vendored closure has path, commit, blob identity, SHA-256 and license records. A later receiving-main commit does not retroactively change the experimental source.

Public coordination is [Alpha issue 4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850). The existing coordinator retains shared-index, merge and Pages ownership. An isolated source PR and a local page do not imply release or deployment. The final handoff records review and publication gates explicitly. No shared catalogue is changed without the receiving acknowledgment. Previous manuscripts and their negative results are preserved.

New research code is Apache-2.0 under the parent repository license. Vendored files retain their upstream licenses. Matrix attribution and the collection's CC-BY-4.0 statement are recorded separately; official-server byte identity remains unverified because the actual data came from pinned public research mirrors after official download failures.
