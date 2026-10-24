# Cost accounting and economic interpretation

This public reading surface accompanies the [complete source and evidence ZIP](AGI_ALPHA_Alpha_Beyond_Prediction_Complete.zip). Extract that archive before running any command. Paths marked **ZIP member** are inspectable files inside its `AGI_ALPHA_Alpha_Beyond_Prediction/` directory. The archive contains all 204 source/evidence payloads and its manifest; no external data download is needed for the synthetic study.

The study reports a **vector of observable costs** and marks unobserved costs explicitly. It does not produce a fully priced economic total. In particular, equal instrument units or a small solver-time difference do not establish equal total engineering cost, profitability, or commercial value. Frozen accounting definition — `protocol/PROTOCOL.md` (ZIP member)

## Units and measurement boundaries

| Quantity | Unit and measurement | Boundary |
|---|---|---|
| Shared capability construction | Code and fixed implementation are inspectable; attributable human effort and provider-side model compute are unknown. | No counterfactual engineering-budget equality was measured. Reusable capability construction is allowed for the conventional comparator too. |
| Per-mission construction | AST node evaluations, constructed rows, `setup_wall_s`. | This timing is a component of solve wall time; do not add it again to `total_wall_s`. Operator construction inside the evaluator and integration preparation have separate timing boundaries. |
| Measurement acquisition | `acquisitions` and integer `acquisition_units`. | These are synthetic resource units. They are not physical exposures, dollars, or numerical candidate evaluations. A discarded observation remains charged. |
| Model-based verification | `verification_acquisitions` and actual `verification_units`, separately reserved from fitting acquisition. | Normally four readouts; a residual pass is not a scientific-quality certificate. Verification observations do not update the fit. |
| Numerical execution | Candidate rows scored, feasible candidates, solver calls, objective calls, CPU seconds and wall seconds. | Count-likelihood fitting uses a bounded optimizer; unsuccessful statuses are retained. Counts and seconds must not be summed as one physical unit. |
| Recovery and local maintenance | Quarantine/recovery events, discarded observations, refits and fresh verification requirements in event traces. | Recorded operational repair is not evidence about long-term maintenance labor, depreciation, service staffing, or hardware failure rates. |
| Waiting and refusal | Recorded waiting steps, abstention reason, zero unperformed instrument observations. | Waiting still has small software/evaluator overhead. Real opportunity loss and the cost of delay are unknown. |
| Cross-family switching in campaign replay | Assumed tariffs of 0, 3 or 12 abstract resource units; charged only when a mission executes. | Sensitivity inputs, not measured switching time or a market price. Per-case execution does not infer a switching tariff. |
| Verification of this package | Independent-test, audit, demo and integration receipts; observed execution timing where recorded. | Automated checks are not human-review labor or proof of a maintained production service. |
| Human effort, provider model compute and monetary hardware/energy prices | **Unknown**. Fields are null or explicitly labeled unknown. | No paid invoice, human time sheet, provider token/cost ledger, or attributable financial accounting was available. Unknown is not zero. |

Full per-case vectors and events remain in confirmation records — `evidence/confirmation/records.json` (ZIP member). The checker — `evidence/confirmation/checker.json` (ZIP member) reconciles event charges and records 13,056 acquisition units plus 2,384 verification units across all eight methods. These totals describe the entire finite evaluation, not the resources needed to deliver a single useful result.

## Observed comparison at the agreed quality level

Across the 96 cases, both APERTURE and the conventional modular builder record:

- **54 qualified outputs**, requiring both normalized prediction error ≤0.12 and the reserved residual check.
- **2,064 acquisition units and 376 verification units**, with identical paired selected actions.
- **102,240 candidate scores, 2,066 solver calls, and eight recovery events**.

The sums of recorded solve CPU time are approximately **2.001 s** for APERTURE and **2.000 s** for modular in this single run. These nearly equal totals are descriptive measurements, not a controlled hardware-performance claim. Their complete end-to-end authoring, engineering, testing, and maintenance costs are unknown. Records — `evidence/confirmation/records.json` (ZIP member) · Interpretation review — `evidence/review/scientific_interpretation_review.md` (ZIP member)

The full primary collection took **16.972 s elapsed** in its recorded environment, with single-thread BLAS settings. That is broader than the per-method solver counters and should not be confused with their sum. The observed environment reports human effort, provider compute, and economic price as null. Environment receipt — `evidence/confirmation/environment.json` (ZIP member)

The later exact numerical reproduction took **16.381 s** including integrity checks, case regeneration, tests, comparison and record audit; the confirmation phase within it took **13.234 s**. This second elapsed time is not an additional independent sample or a controlled speed comparison. The reused installed runtime and immutable reference-data hard links are disclosed. Reproduction receipt — `evidence/reproduction/REPRODUCTION_RECEIPT.json` (ZIP member)

No quality advantage or instrument-unit saving over modular is available here to recover an unknown positive architecture premium. If an additional construction/maintenance cost is (B>0), repeated equal-quality, equal-resource outcomes alone do not pay back (B). This is a conditional accounting statement, not a theorem about all future assignments. A different representation could still earn its cost through a separately measured benefit; that benefit was not demonstrated in this comparison.

## Replays and crossover interpretation

The 288 campaign conditions combine four finite sequences, three methods, four decision strategies, two capacities, and three assumed switching tariffs. For an explicitly chosen abstract reward (R\in\{0,16,32,64\}), the replay reports

\[
\text{net score}=R\times\text{qualified outputs}-\text{used resource units}.
\]

Used units already include charged switching tariffs; do not subtract them twice. This score is a dimensionless sensitivity device under declared units, not willingness to pay, revenue, receipts, profit, or an investment return. Waiting can win when the assigned reward is low or work is infeasible; restricted specialization can avoid construction in unfamiliar families while also losing coverage. Changes in these assumptions can change the ranking. Replay source — `src/campaign.py` (ZIP member) · All conditions — `evidence/campaigns/campaigns.json` (ZIP member)

The scenarios include shared calibration failures, capacity loss, delayed authority, irreversible acquisition costs, and costly switching. Related stress labels across families do not have equal severity distributions. The label-only repair and first failed attempt are retained. There is no calibrated distribution of future demand, and convex reweighting of observed strata supplies no expected-value guarantee beyond those strata.

## Pilot, integration, and demo overhead

The NIST pilot records **54 and 64 actual residual-function calls** for the two starts; reporting only SciPy's smaller `nfev` values would omit finite-difference work. Per-fit time was about 3–4 ms. The instrumented script, including imports, input reading, fits and curve writes, took about 1.004 s wall / 2.142 s CPU; interpreter startup and final JSON serialization were excluded. Pilot accounting — `data/nist/README.md` (ZIP member)

The actual native dispatch integration recorded approximately **0.902 s wall / 0.846 s CPU** for input reads, source verification, observation precomputation, seven stages and serialization up to its receipt. Final JSON writing and journal compression are excluded. Preparing 420 closed synthetic values is computation, not 420 acquired measurements; the executed development solve separately charges 24 acquisition units and four verification units. The native stage ledger's seven calls are not a full scientific or economic cost. Integration receipt — `evidence/foundations/receipt.json` (ZIP member)

Each live demo receipt measures the bounded evaluator call including authority validation. Server startup, explicit authorization, HTTP serialization, UI rendering, and export are not metered. Static replay displays original timings without new numerical execution. Demo guide and boundary — `demo/README.md` (ZIP member)

## What commercial evidence would require

This package contains no realized receipts, paying customers, purchase commitments, operational adoption, or physical validation. Establishing commercial viability would require a separately authorized demand study, prospective quality targets with real users, evidence of willingness to pay, repeated delivery under operational conditions, measured support/recovery labor, and a priced cost ledger. A passed simulation, an unfunded work request, a token balance, or an AscensionMark bloom would not supply that evidence.

The **$15 quadrillion** phrase is excluded from every objective, price, reward, and value calculation. No currency or time horizon is instantiated for it here; it is motivating project language, not a forecast, valuation, accessible market, or existing wealth. No percentage of it is converted into revenue, token price, funding, or return. This paper's measured conclusions survive its removal. Source caveat — `integration/audit-source/AGI-Alpha-Agent-v0/docs/agent/INSIGHT_ATLAS.md` (ZIP member)
