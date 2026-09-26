# The Compounding Lab

[Open the experiment](../compounding/index.html). The question is concrete: **does a capability learned on Mandate A
improve work on a different Mandate B after its costs are counted?**

## A five-step experiment

1. Select continuity, regime change or archive ablation. Choose a future seed and cost assumptions, or supply your own series.
2. Freeze a forecasting policy learned from Mandate A. Inspect its training commitment, policy and full learning cost.
3. Execute B on four disclosed baseline/treatment arms. Inspect each prediction, actual held-out value and error.
4. Review current-stack and treatment evidence separately. Record elapsed review times, identity, rationale and decision.
5. Download the complete Evidence Docket ZIP or portable run JSON. Replay either with the native agent.

Changed inputs clear the frozen capability, results and reviews. Failed computations cannot be accepted by changing
a status field. A review is bound to the exact run digest. Imports replay before replacing the current workspace.
The last valid run survives reload and can execute offline after the gallery cache has installed.
Imported and recovered reviews keep their original timing provenance. A new browser review requires fresh timers
for both arms; it cannot relabel another review's reported durations as newly measured browser time.

## What the learner actually does

Mandate A provides 20–64 bounded integer observations. A walk-forward selector compares last value, mean, linear
least-squares trend and seasonal policies with periods 2–8. A seasonal candidate needs at least two cycles plus
one observation before it is considered. Each candidate's validation begins at `max(3, period)`; mean absolute
error determines selection, with a fixed policy order breaking ties. The capsule stores the selected policy,
training digest, validation scores, number of forecast calls, contract and rollback rule.

The selector receives **only A**. It neither receives B's observations nor calls an expected-answer function.
The policy type and period are frozen; application to each B calibration prefix adapts its level/scale using that
prefix alone. Every B suffix remains outside policy selection. Different policies have different training validation
windows, which is an explicitly bounded heuristic, not a state-of-the-art forecasting claim.

The four measured arms are:

| Arm | Policy | Prior information and charges |
| --- | --- | --- |
| B0 null | Repeat last value | B calibration only |
| B3 static | Linear least-squares trend | B calibration only |
| B5 current stack | The same walk-forward selector, on each B prefix | All B selection calls charged |
| B6 treatment | A's frozen policy, applied to each B prefix | All A selection calls charged in full, plus B prediction calls |

The default future prefixes have six observations, insufficient to select a five-period policy under the learner's
two-cycle rule. A has forty observations. This difference in prior information is the point of the transfer test;
it is not evidence that no stronger baseline could infer the period. B1 incumbent, B2 neighbor and B4 strongest
single agent are **unmeasured**. Both B5 and B6 predict the same eight held-out values per task using fixed local
arithmetic. No LLM, API, network tool, paid service or external evaluator is used.

Continuity creates new scale, level and phase variants of a disclosed periodic family. Regime change uses linear
future series, making the learned seasonal policy fail. Ablation removes the capsule, so B6 reproduces B5 exactly.
These are public synthetic examples, not secret held-outs, independent experiments or external economic outcomes.
Custom specifications permit different training and future data. Content and identifier duplicates are rejected;
this is a guard against obvious reuse, not a general semantic leakage detector. Imported provenance is self-reported.

## Accounting and gates

Predictions use integer milliunits, with ties rounded away from zero. The exact formulas are shared by two
implementations, Python and JavaScript. The dossier retains every prediction and error.

`raw gain = B5 total absolute error − B6 total absolute error`

`overhead = (B6 forecast calls − B5 forecast calls + full validator replay calls) × assumed call rate + coordination cost`

`adjusted advantage = raw gain − overhead − (B6 review time − B5 review time) × assumed human rate`

Call counts are measured invocations, not equal FLOP costs. Rates are explicit **modeled units, not money**.
All A selection calls are charged in the current trial; there is no hidden amortization. Creation executes the full
comparison twice, checking exact equality, and conservatively charges the entire validator pass to the trial.
The ledger counts all forecast calls in both passes, including the extra prepared-but-unused capsule in ablation.
Whole-run wall time covers both passes. Later UI preparation, exports and requested replays add work outside this
creation timing and modeled advantage; no end-to-end deployment efficiency claim is made.
Tokens and network tool calls are zero because this algorithm invokes neither. Energy and monetary compute costs
are unmeasured, not zero. Human timers measure elapsed time, not verified active attention; CLI inputs are labeled
operator-reported. Timings and identities are bound to the digest but are not independently attested.

The local claim requires a positive raw gain, positive cost-adjusted advantage, the declared maximum forecast-error
bound, enabled archive and an explicit accepted review. Reject and repair remain HOLD. Large modeled cost or human
review overhead can turn a raw win into HOLD. Forecast error is a bounded diagnostic, not a measure of financial,
social or deployment risk. The manuscript promotion gate remains HOLD until missing baselines, independent
validation, multi-agent scaling, α-WU calibration and delayed real-world outcomes are established.

ECI is **E2: executed locally**. Replaying in another runtime does not automatically create independent E3 evidence.
A local stress example is not a substitute for the paper's independent stress and external validation requirements.

## Native CLI and portable files

```bash
alpha-agent transfer-run --scenario seasonal --seed 37 --output run.json
alpha-agent transfer-verify run.json
alpha-agent transfer-review run.json --decision accept --reviewer "Operator" \
  --reason "Inspected predictions and costs; accept this bounded result" \
  --control-ms 12000 --treatment-ms 14000 --output reviewed.json
alpha-agent transfer-docket reviewed.json --output evidence-docket.zip
alpha-agent transfer-verify evidence-docket.zip
```

Use your actual review measurements; the example durations are illustrative. No `init`, identity secret or network
connection is needed for this offline experiment. Use `--spec spec.json` for custom inputs. Browser JSON imports
accept native reports unchanged. Browser-generated ZIPs pass the same native verifier as native exports.

The exact directory contract from manuscript pages 37–38 is:

```text
00_manifest.md                 07_replay_logs/
01_claims_matrix.md            08_cost_ledgers/
02_environment.md             09_safety_ledgers/
03_benchmark_tasks/            10_validator_reports/
04_baselines/                 11_alpha_wu_calibration/
05_agialpha_runs/              12_summary_tables/
06_proof_bundles/              checksums.json
```

Empty scientific obligations are explicit status records. The α-WU record is uncalibrated with a null value.
All raw results replay; changing a prediction, capsule, claim, review binding, file checksum or ZIP path is rejected.
ZIP verification uses fixed in-memory paths, entry/expansion limits and no filesystem extraction. JSON imports
reject duplicate keys, extra fields, non-integer/non-finite values, oversized documents and excessive nesting.
Hashes establish content integrity relative to a trusted copy, not signatures, reviewer identity or external truth.

## Relationship to existing demonstrations

Proof Bloom continues the claim → jobs → proof → review → Chronicle path, with ECI terminology corrected.
Its existing capability promotion and transitive revocation protocol stays compatible. The Compounding Lab is a
separate portable experiment for future-task advantage. It does not silently insert a forecasting capsule into
Bloom's registry or grant a permission to execute arbitrary code. See the [manuscript map](MANUSCRIPT_ALIGNMENT.md).
